# -*- coding: utf-8 -*-
"""
Flask Backend for Silkroad RAG Chatbot
Main application with Gemini FileSearch integration
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

def query_gemini_filesearch(user_question, session_id):
    """
    Query Gemini with FileSearch tool
    Returns the response and grounding metadata
    """
    if not gemini_client:
        return {
            'error': 'Gemini client not initialized. Please check your API key.'
        }

    try:
        # Build conversation history context
        chat_history = get_chat_history(session_id)
        context_messages = []

        # Add recent history for context (last 3 exchanges)
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        for msg in recent_history:
            context_messages.append(f"{msg['role'].capitalize()}: {msg['content']}")

        # Build the prompt with context
        system_prompt = """Bạn là trợ lý AI thông minh, chuyên trả lời câu hỏi dựa trên tài liệu được cung cấp.

Quy tắc:
1. Trả lời CHÍNH XÁC dựa trên nội dung trong tài liệu
2. Nếu câu hỏi bằng tiếng Việt, trả lời bằng tiếng Việt
3. Nếu câu hỏi bằng tiếng Anh, trả lời bằng tiếng Anh
4. Nếu không tìm thấy thông tin trong tài liệu, hãy nói rõ ràng
5. Trích dẫn nguồn từ tài liệu khi có thể
6. Trả lời ngắn gọn, súc tích và rõ ràng

You are an intelligent AI assistant specializing in answering questions based on provided documents.

Rules:
1. Answer ACCURATELY based on document content
2. If question is in Vietnamese, answer in Vietnamese
3. If question is in English, answer in English
4. If information is not found in documents, state clearly
5. Cite sources from documents when possible
6. Keep answers concise, clear and to the point
"""

        # Combine context and current question
        if context_messages:
            full_prompt = f"{system_prompt}\n\nCuộc hội thoại trước:\n" + "\n".join(context_messages) + f"\n\nCâu hỏi mới: {user_question}"
        else:
            full_prompt = f"{system_prompt}\n\nCâu hỏi: {user_question}"

        # Query with FileSearch tool
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
    """
    Chat endpoint
    Expects JSON: { "message": "user question" }
    Returns JSON: { "answer": "bot response", "citations": [...] }
    """
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
        'file_search_store': Config.FILE_SEARCH_STORE_ID is not None
    })

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Silkroad RAG Chatbot - Starting Server")
    print("=" * 60)

    if not gemini_client:
        print("\n⚠ Warning: Gemini client not initialized!")
        print("  Please check your .env configuration\n")

    print(f"Server running at: http://localhost:5000")
    print(f"API endpoints:")
    print(f"  POST /api/chat      - Send a message")
    print(f"  GET  /api/history   - Get chat history")
    print(f"  POST /api/clear     - Clear chat history")
    print(f"  GET  /api/health    - Health check")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
