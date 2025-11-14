# -*- coding: utf-8 -*-
"""
Silkroad RAG Chatbot with Zalo OA Integration
Combines Gemini FileSearch with Zalo Official Account webhook
"""
from flask import Flask, render_template, request, render_template, jsonify, session
from flask_cors import CORS
from google import genai
from google.genai import types
import os
import uuid
import json
import logging
import requests
from datetime import datetime
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini client
try:
    Config.validate()
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
    logger.info("✓ Gemini client initialized successfully")
except Exception as e:
    logger.error(f"✗ Error initializing Gemini client: {str(e)}")
    gemini_client = None

# In-memory storage for chat sessions
chat_sessions = {}

# Zalo Configuration
TOKEN_FILE = "tokens.json"

# ============================================================================
# ZALO API FUNCTIONS (Reused from silkroad-api)
# ============================================================================

def get_access_token():
    """
    Get Zalo access token from tokens.json

    Returns:
        Access token string or None if not found
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data["access_token"]
    except (FileNotFoundError, KeyError) as e:
        logger.error(f"Access token error: {e}")
        return None


def send_message_to_user(user_id, message):
    """
    Send a text message to a Zalo user

    Args:
        user_id: Zalo user ID
        message: Message text to send

    Returns:
        Tuple of (status_code, response_text)
    """
    url = "https://openapi.zalo.me/v3.0/oa/message/cs"
    headers = {
        "Content-Type": "application/json",
        "access_token": get_access_token()
    }
    payload = {
        "recipient": {"user_id": user_id},
        "message": {"text": message}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"Sent message to user {user_id}: {response.status_code}")
        logger.info(f"Zalo API Response: {response.text}")

        # Check if response has error
        try:
            response_data = response.json()
            if response_data.get('error') or response_data.get('error_code'):
                logger.error(f"Zalo API Error: {response_data}")
        except:
            pass

        return response.status_code, response.text
    except Exception as e:
        logger.error(f"Error sending message to user {user_id}: {e}", exc_info=True)
        return 500, str(e)


# ============================================================================
# GEMINI RAG FUNCTIONS
# ============================================================================

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


def query_gemini_filesearch(user_question, session_id=None):
    """
    Query Gemini with FileSearch tool
    Returns the response and grounding metadata
    """
    if not gemini_client:
        return {
            'error': 'Gemini client not initialized. Please check your API key.'
        }

    try:
        # Build conversation history context if session_id provided
        context_messages = []
        if session_id:
            chat_history = get_chat_history(session_id)
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
                'success': True
            }
        else:
            return {
                'error': 'No response generated from Gemini',
                'success': False
            }

    except Exception as e:
        logger.error(f"Error querying Gemini: {str(e)}", exc_info=True)
        return {
            'error': f'Error querying Gemini: {str(e)}',
            'success': False
        }


# ============================================================================
# ZALO WEBHOOK HANDLER
# ============================================================================

def handle_user_question(user_id, question):
    """
    Handle user question using Gemini FileSearch chatbot

    Args:
        user_id: Zalo user ID (used as session_id)
        question: User's question text

    Returns:
        None (sends response via Zalo)
    """
    try:
        logger.info(f"Processing question from user {user_id}: {question}")

        # Use user_id as session_id for conversation history
        session_id = user_id

        # Add user message to history
        add_to_history(session_id, 'user', question)

        # Query Gemini FileSearch
        result = query_gemini_filesearch(question, session_id)

        # Extract answer
        if result.get('success'):
            answer = result.get('answer', 'Xin lỗi, không tìm thấy thông tin.')

            # Add bot response to history
            add_to_history(session_id, 'assistant', answer)

            logger.info(f"Answer for user {user_id}: {answer[:100]}...")
        else:
            answer = "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. / Sorry, there was an error processing your question."
            logger.error(f"Error processing question: {result.get('error')}")

        # Send answer back to user
        send_message_to_user(user_id, answer)

    except Exception as e:
        logger.error(f"Error handling question: {e}", exc_info=True)

        # Send error message to user
        error_message = "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau. / Sorry, the system is experiencing issues. Please try again later."
        send_message_to_user(user_id, error_message)


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Render the main chatbot interface"""
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def zalo_webhook():
    """
    Webhook endpoint for receiving Zalo OA events

    Handles:
    - user_send_text: User sends a message (question) to the chatbot
    - follow: New user follows the OA
    """
    # return jsonify({"status": "success", "message": "Webhook received"}), 200 # useful for testing
    data = request.json
    logger.info(f"Received webhook data: {data}")

    # Handle user text message
    if data.get("event_name") == "user_send_text":
        user_id = data.get("sender", {}).get("id")
        if not user_id:
            logger.error("User ID not found in webhook data")
            return jsonify({"error": "User ID not found"}), 400

        # Get user's message
        user_message = data.get("message", {}).get("text", "")
        if not user_message:
            logger.warning(f"Empty message from user {user_id}")
            return jsonify({"status": "success", "message": "Empty message ignored"}), 200

        # Process the question with Gemini RAG chatbot
        handle_user_question(user_id, user_message)

        return jsonify({"status": "success", "message": "Question processed"}), 200

    # Handle follow event (optional - send welcome message)
    elif data.get("event_name") == "follow":
        user_id = data.get("follower", {}).get("id")
        if user_id:
            welcome_message = (
                "Xin chào! Tôi là trợ lý ảo của Silkroad Hà Nội. "
                "Bạn có thể hỏi tôi bất kỳ câu hỏi nào liên quan đến tài liệu kỹ thuật.\n\n"
                "Hello! I am the virtual assistant of Silkroad Hanoi. "
                "You can ask me any questions related to technical documentation."
            )
            send_message_to_user(user_id, welcome_message)
        return jsonify({"status": "success", "message": "Welcome message sent"}), 200

    # Other events - just acknowledge
    return jsonify({"status": "success", "message": "Webhook received"}), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint for web interface
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
        logger.error(f"Server error: {str(e)}", exc_info=True)
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
    try:
        # Check if tokens.json exists
        tokens_exist = os.path.exists(TOKEN_FILE)

        return jsonify({
            'status': 'healthy',
            'gemini_initialized': gemini_client is not None,
            'file_search_store': Config.FILE_SEARCH_STORE_ID is not None,
            'tokens_file_exists': tokens_exist
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route("/zalo_verifierRjBd3fx3LLb6nVvnpCv8IZt_v1FHYZL5D38.html")
def verify_domain():
    return render_template("zalo_verifierRjBd3fx3LLb6nVvnpCv8IZt_v1FHYZL5D38.html")


@app.route('/api/test-send', methods=['POST'])
def test_send_message():
    """
    Test endpoint to send a message to a specific user

    Request body:
    {
        "user_id": "123456789",
        "message": "Test message"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message', 'Test message from Silkroad RAG Chatbot')

        if not user_id:
            return jsonify({
                'error': 'user_id is required',
                'success': False
            }), 400

        status_code, response_text = send_message_to_user(user_id, message)

        return jsonify({
            'status_code': status_code,
            'response': response_text,
            'success': status_code == 200
        }), 200

    except Exception as e:
        logger.error(f"Error in test send: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Silkroad RAG Chatbot - Zalo OA Integration")
    print("=" * 60)

    if not gemini_client:
        print("\n⚠ Warning: Gemini client not initialized!")
        print("  Please check your .env configuration\n")

    print(f"Server running at: http://localhost:5001")
    print(f"Endpoints:")
    print(f"  POST /webhook       - Zalo OA webhook")
    print(f"  POST /api/chat      - Web chat interface")
    print(f"  GET  /api/history   - Get chat history")
    print(f"  POST /api/clear     - Clear chat history")
    print(f"  GET  /api/health    - Health check")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5001,
        debug=Config.DEBUG
    )
