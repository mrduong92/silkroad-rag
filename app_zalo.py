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

# Message deduplication - store processed message IDs
processed_messages = set()
MAX_PROCESSED_MESSAGES = 1000  # Limit memory usage

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

    # ==================== DETAILED LOGGING FOR BUG INVESTIGATION ====================
    logger.info(f"[BUG1] === SEND_MESSAGE_TO_USER CALLED ===")
    logger.info(f"[BUG1] user_id: {user_id} (type: {type(user_id)})")
    logger.info(f"[BUG1] message type: {type(message)}")
    logger.info(f"[BUG1] message length RECEIVED: {len(message)} chars")
    logger.info(f"[BUG1] message length RECEIVED (bytes): {len(message.encode('utf-8'))} bytes")
    logger.info(f"[BUG1] message first 200 chars: {message[:200]}")
    logger.info(f"[BUG1] message last 100 chars: {message[-100:]}")
    # ==================== END DETAILED LOGGING ====================

    # Convert user_id to string if it's not already
    user_id_str = str(user_id)

    headers = {
        "Content-Type": "application/json",
        "access_token": get_access_token()
    }

    # Create payload
    payload = {
        "recipient": {"user_id": user_id_str},
        "message": {"text": message}
    }

    # ==================== PAYLOAD VALIDATION LOGGING ====================
    payload_json = json.dumps(payload, ensure_ascii=False)
    logger.info(f"[BUG1] Payload JSON length: {len(payload_json)} chars")
    logger.info(f"[BUG1] Payload JSON length (bytes): {len(payload_json.encode('utf-8'))} bytes")
    logger.info(f"[BUG1] Message in payload length: {len(payload['message']['text'])} chars")
    logger.info(f"[BUG1] Message in payload matches original: {payload['message']['text'] == message}")
    logger.info(f"[BUG1] Payload first 300 chars: {payload_json[:300]}")
    logger.info(f"[BUG1] Payload last 200 chars: {payload_json[-200:]}")
    logger.info(f"[BUG1] Access token length: {len(headers['access_token'])}")
    # ==================== END PAYLOAD VALIDATION ====================

    try:
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"Sent message to user {user_id_str}: {response.status_code}")
        logger.info(f"[DEBUG] Zalo API Response: {response.text}")

        # Check if response has error
        try:
            response_data = response.json()
            if response_data.get('error') != 0:
                logger.error(f"Zalo API Error: {response_data}")
                logger.error(f"[DEBUG] Failed payload was: {json.dumps(payload, ensure_ascii=False)}")
        except:
            pass

        return response.status_code, response.text
    except Exception as e:
        logger.error(f"Error sending message to user {user_id_str}: {e}", exc_info=True)
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
            logger.info(f"[BUG3] Chat history length: {len(chat_history)}, using recent: {len(recent_history)}")
            for msg in recent_history:
                context_messages.append(f"{msg['role'].capitalize()}: {msg['content']}")
            logger.info(f"[BUG3] Context messages: {len(context_messages)}")

        # Build the prompt with context
        system_prompt = """Bạn là trợ lý AI chuyên nghiệp, trả lời câu hỏi dựa trên tài liệu kỹ thuật.

⚠️ QUY TẮC BẮT BUỘC:
1. Trả lời NGẮN GỌN, đi thẳng vào trọng tâm - KHÔNG giải thích dài dòng
2. CHỈ trả lời ĐÚNG câu hỏi - KHÔNG thêm thông tin thừa
3. Ưu tiên LIỆT KÊ (bullet points) thay vì đoạn văn dài
4. Tối đa 2-3 câu hoặc 3-5 bullet points
5. Dùng ngôn ngữ của câu hỏi (Việt → Việt, English → English)
6. Nếu không có thông tin: nói ngắn gọn "Không tìm thấy thông tin trong tài liệu"

📝 ĐỊNH DẠNG TRẢ LỜI MẪU:
- Câu hỏi: "What materials are allowed?"
  ✅ TỐT: "Materials allowed: A, B, C per standard XYZ."
  ❌ TỆ: "According to the document, there are several materials that are allowed for use. First, material A is permitted because... Second, material B can be used when..."

- Câu hỏi: "Tiêu chuẩn nào áp dụng?"
  ✅ TỐT: "Tiêu chuẩn: CAN/ULC S702, ASTM E331."
  ❌ TỆ: "Theo tài liệu, có một số tiêu chuẩn được áp dụng. Đầu tiên là tiêu chuẩn CAN/ULC S702 được sử dụng để..."

---

You are a professional AI assistant answering questions based on technical documents.

⚠️ MANDATORY RULES:
1. Answer CONCISELY, get straight to the point - NO lengthy explanations
2. ONLY answer the question asked - NO extra information
3. Prefer BULLET POINTS over long paragraphs
4. Maximum 2-3 sentences OR 3-5 bullet points
5. Match question language (Vietnamese → Vietnamese, English → English)
6. If no info found: briefly state "Information not found in documents"

📝 ANSWER FORMAT EXAMPLES:
- Question: "What materials are allowed?"
  ✅ GOOD: "Materials allowed: A, B, C per standard XYZ."
  ❌ BAD: "According to the document, there are several materials..."

- Question: "Tiêu chuẩn nào áp dụng?"
  ✅ GOOD: "Tiêu chuẩn: CAN/ULC S702, ASTM E331."
  ❌ BAD: "Theo tài liệu, có một số tiêu chuẩn..."
"""

        # Combine context and current question
        if context_messages:
            full_prompt = f"{system_prompt}\n\nCuộc hội thoại trước:\n" + "\n".join(context_messages) + f"\n\nCâu hỏi mới: {user_question}"
        else:
            full_prompt = f"{system_prompt}\n\nCâu hỏi: {user_question}"

        logger.info(f"[BUG3] === QUERY CONFIG ===")
        logger.info(f"[BUG3] Model: {Config.MODEL_NAME}")
        logger.info(f"[BUG3] Temperature: {Config.TEMPERATURE}")
        logger.info(f"[BUG3] Max output tokens: {Config.MAX_OUTPUT_TOKENS}")
        logger.info(f"[BUG3] User question: {user_question}")
        logger.info(f"[BUG3] Full prompt length: {len(full_prompt)} chars")
        logger.info(f"[BUG3] Full prompt first 300 chars: {full_prompt[:300]}")

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
        logger.info(f"[DEBUG] Gemini response candidates: {len(response.candidates) if response.candidates else 0}")

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]

            logger.info(f"[DEBUG] Candidate content parts: {len(candidate.content.parts) if candidate.content and candidate.content.parts else 0}")

            # Check if we have valid content
            if not candidate.content or not candidate.content.parts:
                logger.error("[DEBUG] No content parts in candidate response")
                logger.error(f"[DEBUG] Candidate: {candidate}")
                return {
                    'answer': 'Xin lỗi, tôi không thể tạo câu trả lời. Vui lòng thử lại hoặc đặt câu hỏi khác.',
                    'error': 'No content parts in response',
                    'success': False
                }

            answer_text = candidate.content.parts[0].text

            # ==================== ANSWER GENERATION LOGGING ====================
            logger.info(f"[BUG1] === ANSWER GENERATED BY GEMINI ===")
            logger.info(f"[BUG1] Answer type: {type(answer_text)}")
            logger.info(f"[BUG1] Answer length: {len(answer_text)} chars")
            logger.info(f"[BUG1] Answer length (bytes): {len(answer_text.encode('utf-8'))} bytes")
            logger.info(f"[BUG1] Answer first 200 chars: {answer_text[:200]}")
            logger.info(f"[BUG1] Answer last 100 chars: {answer_text[-100:]}")
            logger.info(f"[BUG1] Answer FULL CONTENT: {answer_text}")
            # ==================== END ANSWER LOGGING ====================

            # Keep old debug log for backwards compatibility
            logger.info(f"[DEBUG] Generated answer length: {len(answer_text)} chars")
            logger.info(f"[DEBUG] Answer preview: {answer_text[:100]}...")

            # Extract grounding metadata (citations)
            citations = []
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                logger.info(f"[BUG3] Grounding metadata found: {grounding}")
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    logger.info(f"[BUG3] Number of grounding chunks: {len(grounding.grounding_chunks)}")
                    for idx, chunk in enumerate(grounding.grounding_chunks):
                        logger.info(f"[BUG3] Chunk {idx}: {chunk}")
                        if hasattr(chunk, 'web') and chunk.web:
                            citations.append({
                                'title': chunk.web.title if hasattr(chunk.web, 'title') else 'Unknown',
                                'uri': chunk.web.uri if hasattr(chunk.web, 'uri') else ''
                            })
                else:
                    logger.info(f"[BUG3] No grounding chunks found")
            else:
                logger.info(f"[BUG3] No grounding metadata found")

            return {
                'answer': answer_text,
                'citations': citations,
                'success': True
            }
        else:
            logger.error("[DEBUG] No candidates in Gemini response")
            logger.error(f"[DEBUG] Full response: {response}")
            return {
                'answer': 'Xin lỗi, tôi không thể tìm thấy thông tin liên quan trong tài liệu. Vui lòng thử đặt câu hỏi khác.',
                'error': 'No candidates in Gemini response',
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
        logger.info(f"[BUG2] === HANDLE_USER_QUESTION STARTED ===")
        logger.info(f"[BUG2] user_id: {user_id}")
        logger.info(f"[BUG2] question: {question}")
        logger.info(f"Processing question from user {user_id}: {question}")

        # Use user_id as session_id for conversation history
        session_id = user_id

        # Add user message to history
        logger.info(f"[BUG2] Adding user message to history")
        add_to_history(session_id, 'user', question)

        # Query Gemini FileSearch
        logger.info(f"[BUG2] Calling query_gemini_filesearch")
        gemini_start = datetime.now()
        result = query_gemini_filesearch(question, session_id)
        gemini_elapsed = (datetime.now() - gemini_start).total_seconds()
        logger.info(f"[BUG2] query_gemini_filesearch completed in {gemini_elapsed:.2f}s")

        # Extract answer
        if result.get('success'):
            answer = result.get('answer', 'Xin lỗi, không tìm thấy thông tin.')
            logger.info(f"[BUG2] Successfully got answer from Gemini (length: {len(answer)} chars)")

            # Add bot response to history
            add_to_history(session_id, 'assistant', answer)

            logger.info(f"Answer for user {user_id}: {answer[:100]}...")
        else:
            answer = "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn. / Sorry, there was an error processing your question."
            logger.error(f"[BUG2] Failed to get answer from Gemini")
            logger.error(f"Error processing question: {result.get('error')}")

        # Send answer back to user
        logger.info(f"[BUG2] Calling send_message_to_user")
        send_start = datetime.now()
        send_message_to_user(user_id, answer)
        send_elapsed = (datetime.now() - send_start).total_seconds()
        logger.info(f"[BUG2] send_message_to_user completed in {send_elapsed:.2f}s")
        logger.info(f"[BUG2] === HANDLE_USER_QUESTION COMPLETED ===")

    except Exception as e:
        logger.error(f"[BUG2] === EXCEPTION IN HANDLE_USER_QUESTION ===")
        logger.error(f"[BUG2] Exception type: {type(e).__name__}")
        logger.error(f"[BUG2] Exception message: {str(e)}")
        logger.error(f"Error handling question: {e}", exc_info=True)

        # Send error message to user
        error_message = "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau. / Sorry, the system is experiencing issues. Please try again later."
        try:
            send_message_to_user(user_id, error_message)
            logger.info(f"[BUG2] Error message sent to user {user_id}")
        except Exception as send_error:
            logger.error(f"[BUG2] Failed to send error message: {send_error}", exc_info=True)


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
    logger.info(f"[DEBUG] ===== WEBHOOK RECEIVED =====")
    logger.info(f"[DEBUG] Full webhook data: {json.dumps(data, ensure_ascii=False, indent=2)}")

    # Handle user text message
    if data.get("event_name") == "user_send_text":
        # Get message ID for deduplication
        msg_id = data.get("message", {}).get("msg_id")

        # Deduplicate: Skip if already processed
        if msg_id and msg_id in processed_messages:
            logger.warning(f"[BUG2][DEDUP] Message {msg_id} already processed, skipping")
            logger.warning(f"[BUG2][DEDUP] Total processed messages: {len(processed_messages)}")
            logger.warning(f"[BUG2][DEDUP] Recent 10 msg_ids: {list(processed_messages)[-10:]}")
            return jsonify({"status": "success", "message": "Duplicate message ignored"}), 200

        sender_data = data.get("sender", {})
        sender_id = sender_data.get("id")

        # IMPORTANT: Use user_id_by_app for sending messages (not sender.id)
        user_id_by_app = data.get("user_id_by_app")

        logger.info(f"[DEBUG] Event: user_send_text")
        logger.info(f"[DEBUG] msg_id: {msg_id}")
        logger.info(f"[DEBUG] Sender data: {sender_data}")
        logger.info(f"[DEBUG] sender.id: {sender_id} (type: {type(sender_id)})")
        logger.info(f"[DEBUG] user_id_by_app: {user_id_by_app} (type: {type(user_id_by_app)})")

        # Use user_id_by_app if available, fallback to sender.id
        user_id = user_id_by_app if user_id_by_app else sender_id

        if not user_id:
            logger.error("User ID not found in webhook data")
            logger.error(f"[DEBUG] sender dict was: {sender_data}")
            logger.error(f"[DEBUG] user_id_by_app was: {user_id_by_app}")
            return jsonify({"error": "User ID not found"}), 400

        logger.info(f"[DEBUG] Using user_id for reply: {user_id}")

        # Get user's message
        user_message = data.get("message", {}).get("text", "")
        logger.info(f"[DEBUG] User message: {user_message}")

        if not user_message:
            logger.warning(f"Empty message from user {user_id}")
            return jsonify({"status": "success", "message": "Empty message ignored"}), 200

        # Add to processed messages for deduplication
        if msg_id:
            logger.info(f"[BUG2][DEDUP] Adding msg_id {msg_id} to processed set")
            processed_messages.add(msg_id)
            # Limit memory: remove oldest if too many
            if len(processed_messages) > MAX_PROCESSED_MESSAGES:
                removed_id = processed_messages.pop()
                logger.warning(f"[BUG2][DEDUP] Removed msg_id {removed_id} due to size limit")
            logger.info(f"[BUG2][DEDUP] Added msg_id {msg_id} to processed set (total: {len(processed_messages)})")

        # Process the question with Gemini RAG chatbot
        logger.info(f"[BUG2][TIMING] Starting handle_user_question for user {user_id}")
        start_time = datetime.now()

        handle_user_question(user_id, user_message)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[BUG2][TIMING] Completed handle_user_question in {elapsed:.2f}s")

        if elapsed > 10:
            logger.warning(f"[BUG2][TIMING] SLOW RESPONSE: Took {elapsed:.2f}s to process question")

        return jsonify({"status": "success", "message": "Question processed"}), 200

    # Handle follow event (optional - send welcome message)
    elif data.get("event_name") == "follow":
        follower_data = data.get("follower", {})
        follower_id = follower_data.get("id")

        # Use user_id_by_app if available
        user_id_by_app = data.get("user_id_by_app")
        user_id = user_id_by_app if user_id_by_app else follower_id

        logger.info(f"[DEBUG] Event: follow")
        logger.info(f"[DEBUG] Follower data: {follower_data}")
        logger.info(f"[DEBUG] follower.id: {follower_id} (type: {type(follower_id)})")
        logger.info(f"[DEBUG] user_id_by_app: {user_id_by_app} (type: {type(user_id_by_app)})")
        logger.info(f"[DEBUG] Using user_id for welcome: {user_id}")

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
    logger.info(f"[DEBUG] Unhandled event: {data.get('event_name')}")
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
