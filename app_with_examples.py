# -*- coding: utf-8 -*-
"""
Flask Backend with Few-Shot Learning from Q&A Examples
Chatbot học từ file sample_questions.xlsx
"""
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import uuid
import json
from datetime import datetime
from config import Config
from pathlib import Path

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

# Load Q&A examples
QA_EXAMPLES = []

def load_qa_examples():
    """Load Q&A examples from JSON file"""
    global QA_EXAMPLES

    json_file = Path('qa_examples.json')

    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                QA_EXAMPLES = json.load(f)
            print(f"✓ Loaded {len(QA_EXAMPLES)} Q&A examples from qa_examples.json")
            return True
        except Exception as e:
            print(f"✗ Error loading Q&A examples: {str(e)}")
            return False
    else:
        print("⚠ Warning: qa_examples.json not found")
        print("  Run: python3 load_qa_examples.py first")
        return False

# Load examples on startup
load_qa_examples()

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

def find_similar_examples(user_question, top_k=3):
    """
    Find most similar Q&A examples using simple string matching
    Returns top K most similar examples for few-shot prompting
    """
    if not QA_EXAMPLES:
        return []

    from difflib import SequenceMatcher

    def similarity(q1, q2):
        return SequenceMatcher(None, q1.lower(), q2.lower()).ratio()

    # Calculate similarity scores
    scored_examples = []
    for example in QA_EXAMPLES:
        score = similarity(user_question, example['question'])
        scored_examples.append({
            **example,
            'similarity': score
        })

    # Sort by similarity and return top K
    scored_examples.sort(key=lambda x: x['similarity'], reverse=True)

    return scored_examples[:top_k]

def build_few_shot_prompt(user_question, similar_examples):
    """
    Build prompt with few-shot examples
    Examples teach the model the desired answer format and style
    """

    base_prompt = """Bạn là trợ lý AI chuyên nghiệp, trả lời câu hỏi dựa trên TÀI LIỆU được cung cấp.

⚠️ QUY TẮC BẮT BUỘC:
1. BẮT BUỘC SỬ DỤNG FileSearch Tool để tìm thông tin từ tài liệu
2. Trả lời PHẢI DỰA VÀO nội dung từ tài liệu, KHÔNG PHẢI từ các ví dụ
3. Các ví dụ bên dưới CHỈ để học FORMAT/STYLE trả lời, KHÔNG DÙNG NỘI DUNG của chúng
4. Ngôn ngữ: Vietnamese → Vietnamese, English → English

---

VÍ DỤ FORMAT TRẢ LỜI (CHỈ HỌC FORMAT, KHÔNG COPY NỘI DUNG):

"""

    # Add few-shot examples
    if similar_examples:
        for i, example in enumerate(similar_examples, 1):
            base_prompt += f"""
VÍ DỤ {i} - CHỈ ĐỂ HỌC FORMAT (KHÔNG DÙNG NỘI DUNG NÀY):

Câu hỏi: {example['question']}

Câu trả lời: {example['answer']}

---
"""

    base_prompt += """

🎯 HƯỚNG DẪN QUAN TRỌNG:

VỀ NỘI DUNG:
✅ SỬ DỤNG FileSearch để tìm thông tin từ TÀI LIỆU
✅ Trả lời dựa 100% vào nội dung TÌM ĐƯỢC từ tài liệu
❌ TUYỆT ĐỐI KHÔNG copy/paraphrase nội dung từ các ví dụ trên
❌ KHÔNG dùng thông tin từ ví dụ, kể cả khi câu hỏi giống nhau

VỀ FORMAT:
✅ HỌC độ dài câu trả lời từ ví dụ (ngắn gọn/chi tiết)
✅ HỌC cách tổ chức (bullet points/prose/liệt kê)
✅ HỌC style (formal/concise/structured)

---

You are a professional AI assistant answering questions based on PROVIDED DOCUMENTS.

⚠️ MANDATORY RULES:
1. MUST USE FileSearch Tool to retrieve information from documents
2. Answer MUST BE BASED ON document content, NOT from examples
3. Examples below are ONLY for learning FORMAT/STYLE, DO NOT use their content
4. Language: Vietnamese → Vietnamese, English → English

🎯 CRITICAL INSTRUCTIONS:

FOR CONTENT:
✅ USE FileSearch to find information from DOCUMENTS
✅ Answer based 100% on content FOUND in documents
❌ ABSOLUTELY DO NOT copy/paraphrase content from examples above
❌ DO NOT use information from examples, even if question is similar

FOR FORMAT:
✅ LEARN answer length from examples (concise/detailed)
✅ LEARN organization style (bullet points/prose/lists)
✅ LEARN tone (formal/concise/structured)

"""

    return base_prompt

def query_gemini_with_examples(user_question, session_id):
    """
    Query Gemini with few-shot learning from Q&A examples
    """
    if not gemini_client:
        return {
            'error': 'Gemini client not initialized. Please check your API key.'
        }

    try:
        # Step 1: Find similar Q&A examples
        similar_examples = find_similar_examples(user_question, top_k=3)

        # Step 2: Build few-shot prompt
        system_prompt = build_few_shot_prompt(user_question, similar_examples)

        # Step 3: Build conversation history context
        chat_history = get_chat_history(session_id)
        context_messages = []

        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        for msg in recent_history:
            context_messages.append(f"{msg['role'].capitalize()}: {msg['content']}")

        # Step 4: Combine everything
        if context_messages:
            full_prompt = f"{system_prompt}\n\nCuộc hội thoại trước:\n" + "\n".join(context_messages) + f"\n\nCâu hỏi mới: {user_question}"
        else:
            full_prompt = f"{system_prompt}\n\nCâu hỏi: {user_question}"

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
                'similar_examples': [
                    {
                        'question': ex['question'],
                        'answer': ex['answer'][:100] + '...' if len(ex['answer']) > 100 else ex['answer'],
                        'similarity': f"{ex.get('similarity', 0):.0%}"
                    }
                    for ex in similar_examples
                ],
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
    """Chat endpoint with few-shot learning"""
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

        # Query Gemini with examples
        result = query_gemini_with_examples(user_message, session_id)

        if result.get('success'):
            # Add bot response to history
            add_to_history(session_id, 'assistant', result['answer'])

            return jsonify({
                'answer': result['answer'],
                'citations': result.get('citations', []),
                'similar_examples': result.get('similar_examples', []),
                'success': True
            })
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}',
            'success': False
        }), 500

@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get all Q&A examples"""
    try:
        return jsonify({
            'examples': QA_EXAMPLES[:20],  # Return first 20
            'total': len(QA_EXAMPLES),
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': f'Error retrieving examples: {str(e)}',
            'success': False
        }), 500

@app.route('/api/reload-examples', methods=['POST'])
def reload_examples():
    """Reload Q&A examples from file"""
    try:
        success = load_qa_examples()
        return jsonify({
            'message': f'Reloaded {len(QA_EXAMPLES)} examples',
            'success': success
        })
    except Exception as e:
        return jsonify({
            'error': f'Error reloading examples: {str(e)}',
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
        'qa_examples_loaded': len(QA_EXAMPLES) > 0,
        'num_examples': len(QA_EXAMPLES),
        'version': 'with_examples'
    })

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Silkroad RAG Chatbot - WITH Q&A EXAMPLES")
    print("=" * 60)

    if not gemini_client:
        print("\n⚠ Warning: Gemini client not initialized!")
        print("  Please check your .env configuration\n")

    if not QA_EXAMPLES:
        print("\n⚠ Warning: No Q&A examples loaded!")
        print("  Run: python3 load_qa_examples.py")
        print("  to load examples from sample_questions.xlsx\n")
    else:
        print(f"\n✓ Loaded {len(QA_EXAMPLES)} Q&A examples")
        print("  Chatbot will learn from these examples\n")

    print(f"Server running at: http://localhost:5004")
    print(f"Features:")
    print(f"  - Few-shot learning from Q&A examples")
    print(f"  - Similarity-based example selection")
    print(f"  - Answer format learning")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5004,
        debug=Config.DEBUG
    )
