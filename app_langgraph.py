# -*- coding: utf-8 -*-
"""
Flask Backend with LangGraph Workflow
Multi-step reasoning for focused answers
"""
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import uuid
from datetime import datetime
from config import Config

# LangGraph imports
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
CORS(app)

# Initialize clients
try:
    Config.validate()
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)

    # LangChain Gemini client for LangGraph
    llm = ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=Config.TEMPERATURE
    )

    print("✓ Gemini client initialized successfully")
except Exception as e:
    print(f"✗ Error initializing Gemini client: {str(e)}")
    gemini_client = None
    llm = None

# In-memory storage for chat sessions
chat_sessions = {}

def get_or_create_session_id():
    """Get or create a unique session ID for the user"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def get_chat_history(session_id):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            'messages': [],
            'created_at': datetime.now().isoformat()
        }
    return chat_sessions[session_id]['messages']

def add_to_history(session_id, role, content):
    """Add a message to chat history"""
    history = get_chat_history(session_id)
    history.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    })

    if len(history) > Config.MAX_HISTORY_LENGTH * 2:
        chat_sessions[session_id]['messages'] = history[-(Config.MAX_HISTORY_LENGTH * 2):]

# Define State for LangGraph
class RAGState(TypedDict):
    question: str
    query_analysis: dict
    retrieved_context: str
    answer: str
    citations: List[dict]
    should_refine: bool

# Node 1: Analyze Query
def analyze_query_node(state: RAGState) -> RAGState:
    """Analyze user query to understand intent and requirements"""
    question = state["question"]

    analysis_prompt = f"""Phân tích câu hỏi và trả về JSON:

Câu hỏi: "{question}"

Phân tích chi tiết:
1. **intent**: Loại câu hỏi (list_names, describe_property, explain_concept, compare, general)
2. **scope**: Phạm vi (single_object, multiple_objects)
3. **focus**: Khía cạnh chính (name_only, specific_property, multiple_properties, all_info)
4. **expected_length**: Độ dài mong đợi (short: 1-2 câu, medium: 2-4 câu, long: 4-6 câu)
5. **should_include**: Nên bao gồm (names, descriptions, examples, comparisons)
6. **should_exclude**: Nên loại trừ (other_properties, unrelated_info, extra_details)

Trả về JSON:
{{
    "intent": "...",
    "scope": "...",
    "focus": "...",
    "expected_length": "...",
    "should_include": [...],
    "should_exclude": [...],
    "enhanced_query": "câu hỏi được làm rõ"
}}

CHỈ trả về JSON."""

    try:
        response = llm.invoke([HumanMessage(content=analysis_prompt)])
        import json
        result_text = response.content

        # Extract JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(result_text)
        state["query_analysis"] = analysis

    except Exception as e:
        print(f"Query analysis failed: {e}")
        state["query_analysis"] = {
            "intent": "general",
            "scope": "multiple_objects",
            "focus": "all_info",
            "expected_length": "medium",
            "should_include": ["all"],
            "should_exclude": [],
            "enhanced_query": question
        }

    return state

# Node 2: Retrieve from FileSearch
def retrieve_context_node(state: RAGState) -> RAGState:
    """Retrieve relevant context from FileSearch"""
    query_analysis = state["query_analysis"]
    enhanced_query = query_analysis.get("enhanced_query", state["question"])

    try:
        # Query FileSearch
        response = gemini_client.models.generate_content(
            model=Config.MODEL_NAME,
            contents=enhanced_query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[Config.FILE_SEARCH_STORE_ID]
                        )
                    )
                ],
                temperature=0.0,  # Deterministic retrieval
            )
        )

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            context = candidate.content.parts[0].text if candidate.content.parts else ""
            state["retrieved_context"] = context

            # Extract citations
            citations = []
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            citations.append({
                                'title': chunk.web.title if hasattr(chunk.web, 'title') else 'Unknown',
                                'uri': chunk.web.uri if hasattr(chunk.web, 'uri') else ''
                            })
            state["citations"] = citations

    except Exception as e:
        print(f"Retrieval failed: {e}")
        state["retrieved_context"] = ""
        state["citations"] = []

    return state

# Node 3: Generate Focused Answer
def generate_answer_node(state: RAGState) -> RAGState:
    """Generate focused answer based on analysis and retrieved context"""
    question = state["question"]
    analysis = state["query_analysis"]
    context = state["retrieved_context"]

    # Build dynamic prompt based on analysis
    intent = analysis.get("intent", "general")
    expected_length = analysis.get("expected_length", "medium")
    should_include = analysis.get("should_include", [])
    should_exclude = analysis.get("should_exclude", [])

    generation_prompt = f"""Dựa trên thông tin sau, trả lời câu hỏi:

THÔNG TIN TỪ TÀI LIỆU:
{context}

CÂU HỎI:
{question}

PHÂN TÍCH CÂU HỎI:
- Loại: {intent}
- Độ dài mong đợi: {expected_length}
- Nên bao gồm: {', '.join(should_include)}
- Không nên bao gồm: {', '.join(should_exclude)}

YÊU CẦU:
1. Trả lời CHÍNH XÁC câu hỏi, dựa VÀO THÔNG TIN TRÊN
2. Chỉ trả lời những gì được hỏi
3. Độ dài: {expected_length}
4. Bao gồm: {', '.join(should_include)}
5. KHÔNG bao gồm: {', '.join(should_exclude)}
6. Ngôn ngữ: {'Tiếng Việt' if any(ord(c) > 127 for c in question) else 'English'}

Trả lời:"""

    try:
        response = llm.invoke([HumanMessage(content=generation_prompt)])
        state["answer"] = response.content

    except Exception as e:
        print(f"Answer generation failed: {e}")
        state["answer"] = "Xin lỗi, không thể tạo câu trả lời."

    return state

# Node 4: Validate and Refine
def validate_answer_node(state: RAGState) -> RAGState:
    """Validate if answer meets requirements, refine if needed"""
    question = state["question"]
    answer = state["answer"]
    analysis = state["query_analysis"]

    validation_prompt = f"""Đánh giá câu trả lời:

CÂU HỎI: {question}
CÂU TRẢ LỜI: {answer}
YÊU CẦU: {analysis}

Kiểm tra:
1. Có trả lời đúng câu hỏi không?
2. Có thông tin thừa không?
3. Độ dài có phù hợp không?
4. Có đề cập thông tin không được yêu cầu không?

Trả về JSON:
{{
    "is_valid": true/false,
    "issues": ["vấn đề 1", "vấn đề 2"],
    "refined_answer": "câu trả lời đã cải thiện (nếu cần)"
}}

CHỈ trả về JSON."""

    try:
        response = llm.invoke([HumanMessage(content=validation_prompt)])
        import json
        result_text = response.content

        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        validation = json.loads(result_text)

        if not validation.get("is_valid", True) and validation.get("refined_answer"):
            state["answer"] = validation["refined_answer"]
            state["should_refine"] = False
        else:
            state["should_refine"] = False

    except Exception as e:
        print(f"Validation failed: {e}")
        state["should_refine"] = False

    return state

# Define routing logic
def should_refine_router(state: RAGState) -> str:
    """Decide if answer needs refinement"""
    if state.get("should_refine", False):
        return "refine"
    else:
        return "end"

# Build LangGraph workflow
def create_rag_workflow():
    """Create the RAG workflow graph"""
    workflow = StateGraph(RAGState)

    # Add nodes
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("validate_answer", validate_answer_node)

    # Add edges
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_answer")
    workflow.add_edge("generate_answer", "validate_answer")
    workflow.add_edge("validate_answer", END)

    # Compile
    return workflow.compile()

# Create workflow
rag_workflow = create_rag_workflow() if llm and gemini_client else None

def query_with_langgraph(user_question, session_id):
    """Query using LangGraph workflow"""
    if not rag_workflow:
        return {
            'error': 'LangGraph workflow not initialized',
            'success': False
        }

    try:
        # Run workflow
        initial_state = {
            "question": user_question,
            "query_analysis": {},
            "retrieved_context": "",
            "answer": "",
            "citations": [],
            "should_refine": False
        }

        result = rag_workflow.invoke(initial_state)

        return {
            'answer': result["answer"],
            'citations': result.get("citations", []),
            'query_analysis': result.get("query_analysis", {}),
            'success': True
        }

    except Exception as e:
        return {
            'error': f'LangGraph workflow error: {str(e)}',
            'success': False
        }

@app.route('/')
def index():
    """Render the main chatbot interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint using LangGraph"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({
                'error': 'Message is required',
                'success': False
            }), 400

        session_id = get_or_create_session_id()
        add_to_history(session_id, 'user', user_message)

        # Use LangGraph workflow
        result = query_with_langgraph(user_message, session_id)

        if result.get('success'):
            add_to_history(session_id, 'assistant', result['answer'])

            return jsonify({
                'answer': result['answer'],
                'citations': result.get('citations', []),
                'query_analysis': result.get('query_analysis', {}),
                'workflow': 'langgraph',
                'success': True
            })
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}',
            'success': False
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history"""
    try:
        session_id = get_or_create_session_id()
        history = get_chat_history(session_id)

        return jsonify({
            'history': history,
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': f'Error retrieving history: {str(e)}',
            'success': False
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear chat history"""
    try:
        session_id = get_or_create_session_id()
        if session_id in chat_sessions:
            chat_sessions[session_id]['messages'] = []

        return jsonify({
            'message': 'History cleared',
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': f'Error clearing history: {str(e)}',
            'success': False
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'workflow': 'langgraph',
        'gemini_initialized': gemini_client is not None,
        'langgraph_initialized': rag_workflow is not None
    })

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Silkroad RAG Chatbot - LANGGRAPH VERSION")
    print("=" * 60)

    if not rag_workflow:
        print("\n⚠ Warning: LangGraph workflow not initialized!")
        print("  Install: pip install -r requirements_langgraph.txt\n")

    print(f"Server running at: http://localhost:5003")
    print(f"Workflow:")
    print(f"  1. Analyze Query → 2. Retrieve Context")
    print(f"  3. Generate Answer → 4. Validate & Refine")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5003,
        debug=Config.DEBUG
    )
