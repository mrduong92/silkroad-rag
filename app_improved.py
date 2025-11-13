# -*- coding: utf-8 -*-
"""
Flask Backend for Silkroad RAG Chatbot - IMPROVED VERSION
With advanced prompting (no hardcoded keywords)
"""
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import uuid
from datetime import datetime
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
CORS(app)

# Initialize Gemini client
try:
    Config.validate()
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
    print("✓ Gemini client initialized successfully")
except Exception as e:
    print(f"✗ Error initializing Gemini client: {str(e)}")
    gemini_client = None

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

    # Keep only last N messages
    if len(history) > Config.MAX_HISTORY_LENGTH * 2:
        chat_sessions[session_id]['messages'] = history[-(Config.MAX_HISTORY_LENGTH * 2):]

def analyze_query_intent(user_question):
    """
    Use LLM to analyze query intent and extract key aspects
    This is a lightweight pre-processing step without hardcoded keywords
    """
    if not gemini_client:
        return {"enhanced_query": user_question, "intent": "general"}

    try:
        analysis_prompt = f"""Phân tích câu hỏi sau và trả về JSON:

Câu hỏi: "{user_question}"

Phân tích:
1. Intent: Câu hỏi muốn hỏi về gì? (list_names, describe_property, explain_concept, compare, other)
2. Scope: Hỏi về một đối tượng cụ thể hay nhiều đối tượng?
3. Focus: Khía cạnh nào đang được hỏi? (name, property, characteristic, example, all)

Trả về JSON format:
{{
    "intent": "list_names/describe_property/explain_concept/compare/other",
    "scope": "single/multiple",
    "focus": "name/property/characteristic/example/all",
    "enhanced_query": "câu hỏi được làm rõ hơn"
}}

Chỉ trả về JSON, không giải thích thêm."""

        response = gemini_client.models.generate_content(
            model=Config.MODEL_NAME,
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,  # Deterministic analysis
                max_output_tokens=200,
            )
        )

        # Parse JSON response
        import json
        result_text = response.candidates[0].content.parts[0].text
        # Extract JSON from markdown code block if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(result_text)
        return analysis

    except Exception as e:
        print(f"Query analysis failed: {e}")
        return {"enhanced_query": user_question, "intent": "general", "scope": "multiple", "focus": "all"}

def build_dynamic_prompt(user_question, query_analysis):
    """
    Build system prompt dynamically based on query analysis
    No hardcoded keywords!
    """

    intent = query_analysis.get("intent", "general")
    scope = query_analysis.get("scope", "multiple")
    focus = query_analysis.get("focus", "all")

    # Base prompt
    base_prompt = """Bạn là trợ lý AI chuyên nghiệp, trả lời câu hỏi dựa trên tài liệu.

QUY TẮC CƠ BẢN:
1. Trả lời CHÍNH XÁC dựa trên nội dung tài liệu
2. Sử dụng ngôn ngữ của câu hỏi (Việt → Việt, English → English)
3. Nếu không có thông tin trong tài liệu, nói rõ ràng
4. Trích dẫn nguồn khi có thể
"""

    # Dynamic instructions based on intent
    if intent == "list_names":
        specific_instruction = """
HƯỚNG DẪN CỤ THỂ (cho câu hỏi liệt kê):
- CHỈ liệt kê tên/danh sách được yêu cầu
- KHÔNG mô tả chi tiết từng mục
- Format: Bullet points hoặc danh sách ngắn gọn
- Độ dài: 1-2 câu

VÍ DỤ:
Q: Các loại X được đề cập?
A: Các loại X bao gồm: A, B, C, D.
"""

    elif intent == "describe_property":
        if focus == "name":
            specific_instruction = """
HƯỚNG DẪN CỤ THỂ (cho câu hỏi về tên):
- CHỈ trả lời tên/danh sách
- KHÔNG thêm mô tả hoặc đặc điểm
- Độ dài: 1-2 câu
"""
        else:
            specific_instruction = """
HƯỚNG DẪN CỤ THỂ (cho câu hỏi về thuộc tính):
- CHỈ mô tả thuộc tính/đặc điểm được hỏi
- KHÔNG đề cập đến các thuộc tính khác
- Nếu hỏi về MỘT thuộc tính cụ thể, CHỈ trả lời thuộc tính đó
- Độ dài: 2-3 câu

VÍ DỤ:
Q: Khả năng X của đối tượng Y?
A: Đối tượng Y có khả năng X là [thông tin từ tài liệu]. (KHÔNG đề cập khả năng Z, W, etc.)
"""

    elif intent == "explain_concept":
        specific_instruction = """
HƯỚNG DẪN CỤ THỂ (cho câu hỏi giải thích):
- Giải thích khái niệm được hỏi
- Có thể bao gồm ví dụ nếu có trong tài liệu
- Độ dài: 3-4 câu
- Tập trung vào khái niệm chính, không lan man
"""

    elif intent == "compare":
        specific_instruction = """
HƯỚNG DẪN CỤ THỂ (cho câu hỏi so sánh):
- So sánh các đối tượng được yêu cầu
- CHỈ so sánh về khía cạnh được hỏi (nếu có)
- Format: Bảng hoặc danh sách so sánh
- Độ dài: 3-5 câu
"""

    else:  # general
        specific_instruction = """
HƯỚNG DẪN CỤ THỂ (câu hỏi chung):
- Trả lời trực tiếp câu hỏi
- Ngắn gọn, súc tích (2-4 câu)
- Tập trung vào thông tin chính
- KHÔNG thêm thông tin không được hỏi
"""

    # Scope instruction
    if scope == "single":
        scope_instruction = "\n⚠ LƯU Ý: Câu hỏi chỉ hỏi về MỘT đối tượng cụ thể. CHỈ trả lời về đối tượng đó, KHÔNG liệt kê các đối tượng khác."
    else:
        scope_instruction = ""

    # Combine all
    final_prompt = f"""{base_prompt}

{specific_instruction}
{scope_instruction}

QUAN TRỌNG:
- Mỗi câu hỏi là ĐỘC LẬP
- KHÔNG gộp nhiều thông tin không liên quan
- KHÔNG thêm thông tin "bonus" dù có trong tài liệu
- Độ dài tối đa: 100 từ

---

You are a professional AI assistant answering questions based on documents.

BASIC RULES:
1. Answer ACCURATELY based on document content
2. Use question's language (Vietnamese → Vietnamese, English → English)
3. If no info in documents, state clearly
4. Cite sources when possible

IMPORTANT:
- Each question is INDEPENDENT
- Do NOT merge unrelated information
- Do NOT add "bonus" info even if in document
- Max length: 100 words
"""

    return final_prompt

def query_gemini_filesearch(user_question, session_id):
    """
    Query Gemini with FileSearch tool using dynamic prompting
    """
    if not gemini_client:
        return {
            'error': 'Gemini client not initialized. Please check your API key.'
        }

    try:
        # Step 1: Analyze query intent (lightweight, no hardcoded keywords)
        query_analysis = analyze_query_intent(user_question)

        # Step 2: Build dynamic prompt based on analysis
        system_prompt = build_dynamic_prompt(user_question, query_analysis)

        # Step 3: Build conversation history context
        chat_history = get_chat_history(session_id)
        context_messages = []

        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        for msg in recent_history:
            context_messages.append(f"{msg['role'].capitalize()}: {msg['content']}")

        # Step 4: Combine everything
        enhanced_query = query_analysis.get("enhanced_query", user_question)

        if context_messages:
            full_prompt = f"{system_prompt}\n\nCuộc hội thoại trước:\n" + "\n".join(context_messages) + f"\n\nCâu hỏi mới: {enhanced_query}"
        else:
            full_prompt = f"{system_prompt}\n\nCâu hỏi: {enhanced_query}"

        # Step 5: Query with FileSearch tool
        response = gemini_client.models.generate_content(
            model=Config.MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[Config.FILE_SEARCH_STORE_ID]
                        )
                    )
                ],
                temperature=Config.TEMPERATURE,
                max_output_tokens=Config.MAX_OUTPUT_TOKENS,
                response_modalities=["TEXT"],
            )
        )

        # Extract response text
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            answer_text = candidate.content.parts[0].text if candidate.content.parts else "No response generated"

            # Extract grounding metadata (citations)
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

            return {
                'answer': answer_text,
                'citations': citations,
                'query_analysis': query_analysis,  # Return analysis for debugging
                'success': True
            }
        else:
            return {
                'error': 'No response generated from Gemini',
                'success': False
            }

    except Exception as e:
        return {
            'error': f'Error querying Gemini: {str(e)}',
            'success': False
        }

@app.route('/')
def index():
    """Render the main chatbot interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({
                'error': 'Message is required',
                'success': False
            }), 400

        # Get or create session
        session_id = get_or_create_session_id()

        # Add user message to history
        add_to_history(session_id, 'user', user_message)

        # Query Gemini FileSearch
        result = query_gemini_filesearch(user_message, session_id)

        if result.get('success'):
            # Add bot response to history
            add_to_history(session_id, 'assistant', result['answer'])

            return jsonify({
                'answer': result['answer'],
                'citations': result.get('citations', []),
                'query_analysis': result.get('query_analysis', {}),  # For debugging
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
    """Get chat history for current session"""
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
    """Clear chat history for current session"""
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
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'gemini_initialized': gemini_client is not None,
        'file_search_store': Config.FILE_SEARCH_STORE_ID is not None,
        'version': 'improved'
    })

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Silkroad RAG Chatbot - IMPROVED VERSION")
    print("=" * 60)

    if not gemini_client:
        print("\n⚠ Warning: Gemini client not initialized!")
        print("  Please check your .env configuration\n")

    print(f"Server running at: http://localhost:5002")
    print(f"Features:")
    print(f"  - Dynamic prompt engineering (no hardcoded keywords)")
    print(f"  - Query intent analysis")
    print(f"  - Adaptive response formatting")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5002,
        debug=Config.DEBUG
    )
