# Zalo OA Integration Guide

## Overview

This guide explains how to integrate the Silkroad RAG chatbot with Zalo Official Account (OA) to enable users to ask questions via Zalo Messenger.

## Architecture

```
User sends message on Zalo OA
        ↓
Zalo Webhook → /webhook endpoint
        ↓
Gemini FileSearch RAG Engine
        ↓
send_message_to_user() → Answer sent back to Zalo
```

## Prerequisites

1. **Zalo Official Account** - You must have a verified Zalo OA
2. **Zalo App** - Registered on Zalo Developers Portal
3. **Gemini API** - Configured and working (see main README.md)
4. **Public URL** - For webhook (use ngrok for local testing)

---

## Step 1: Setup Zalo App & Get Credentials

### 1.1 Create/Access Your Zalo App

1. Go to [Zalo Developers](https://developers.zalo.me/)
2. Log in with your Zalo account
3. Navigate to your app or create a new one
4. Note down:
   - **APP_ID**: Your application ID
   - **SECRET_KEY**: Your application secret key

### 1.2 Get OAuth Tokens

1. In Zalo Developers Console, go to **OAuth Settings**
2. Generate **access_token** and **refresh_token** for your OA
3. Note down your **OA ID** (Official Account ID)

---

## Step 2: Configure Environment Variables

Edit `.env` file:

```bash
# Gemini Configuration (already set)
GEMINI_API_KEY=your_gemini_api_key
FILE_SEARCH_STORE_ID=your_file_search_store_id

# Zalo OA Configuration
APP_ID=your_zalo_app_id
SECRET_KEY=your_zalo_secret_key
```

---

## Step 3: Setup Tokens

### 3.1 Create tokens.json

Copy the example file:

```bash
cp tokens.json.example tokens.json
```

### 3.2 Edit tokens.json

Replace with your actual tokens:

```json
{
  "access_token": "your_actual_access_token",
  "refresh_token": "your_actual_refresh_token",
  "expires_in": "90000"
}
```

**Note:** This app supports a single Zalo OA only. No need for OA ID as key.

### 3.3 Add tokens.json to .gitignore

```bash
echo "tokens.json" >> .gitignore
```

**Never commit tokens.json to git!**

---

## Step 4: Test Token Refresh

Zalo access tokens expire after ~25 hours. Test the refresh mechanism:

```bash
python3 refresh_zalo_token.py
```

**Expected output:**
```
✅ Token refreshed successfully
✅ Token updated successfully.
```

**Setup a cron job to auto-refresh:**

```bash
# Run every 12 hours
0 */12 * * * cd /path/to/silkroad-rag && python3 refresh_zalo_token.py >> refresh.log 2>&1
```

---

## Step 5: Run the App

Start the Zalo-integrated chatbot:

```bash
python3 app_zalo.py
```

**Expected output:**
```
============================================================
Silkroad RAG Chatbot - Zalo OA Integration
============================================================

✓ Gemini client initialized successfully

Server running at: http://localhost:5001
Endpoints:
  POST /webhook       - Zalo OA webhook
  POST /api/chat      - Web chat interface
  GET  /api/history   - Get chat history
  POST /api/clear     - Clear chat history
  GET  /api/health    - Health check
============================================================
```

---

## Step 6: Setup Webhook (Local Testing with ngrok)

### 6.1 Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

### 6.2 Start ngrok tunnel

```bash
ngrok http 5001
```

**Output:**
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5001
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 6.3 Configure Webhook in Zalo Developers

1. Go to [Zalo Developers Console](https://developers.zalo.me/)
2. Select your app
3. Go to **Webhook Settings**
4. Set webhook URL: `https://abc123.ngrok.io/webhook`
5. Subscribe to events:
   - ✅ `user_send_text` (required)
   - ✅ `follow` (optional - for welcome messages)
6. Save settings

---

## Step 7: Test End-to-End

### 7.1 Test via Zalo App

1. Open Zalo app on your phone
2. Search for your Official Account
3. Follow the OA (if not already)
4. Send a test message:
   ```
   In the Toronto area, what types of insulation are standard?
   ```
5. Bot should reply with answer from documents

### 7.2 Monitor Logs

Watch the Flask logs:

```bash
# You should see:
Received webhook data: {'event_name': 'user_send_text', ...}
Processing question from user 123456789: In the Toronto area...
Answer for user 123456789: In the Toronto area, the following...
Sent message to user 123456789: 200
```

### 7.3 Test Health Endpoint

```bash
curl http://localhost:5001/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "gemini_initialized": true,
  "file_search_store": true,
  "tokens_file_exists": true
}
```

---

## Troubleshooting

### Issue: "Missing oa_id in webhook data"

**Solution:** Check Zalo webhook configuration. Make sure the webhook URL is correct.

### Issue: "Access token error for OA"

**Solution:**
1. Check `tokens.json` exists and has correct format
2. Verify OA ID matches exactly
3. Run `python3 refresh_zalo_token.py` to refresh tokens

### Issue: "Error sending message to user"

**Solution:**
1. Check access token is valid
2. Verify user has not blocked the OA
3. Check Zalo API rate limits

### Issue: Webhook not receiving messages

**Solution:**
1. Verify ngrok is running and forwarding to port 5001
2. Check webhook URL in Zalo console matches ngrok URL
3. Make sure `user_send_text` event is subscribed
4. Check Flask app is running without errors

### Issue: "Gemini client not initialized"

**Solution:**
1. Check `.env` has valid `GEMINI_API_KEY`
2. Check `FILE_SEARCH_STORE_ID` is set
3. Run health check to verify

---

## Production Deployment

### Option 1: Deploy on VPS/Cloud

1. Deploy app on a server with public IP
2. Use a domain name (e.g., `chatbot.silkroad.vn`)
3. Setup HTTPS with Let's Encrypt/SSL certificate
4. Configure webhook URL: `https://chatbot.silkroad.vn/webhook`
5. Setup systemd service for auto-restart
6. Setup cron job for token refresh

### Option 2: Deploy on Heroku/Railway/Render

1. Add `Procfile`:
   ```
   web: gunicorn app_zalo:app
   ```
2. Add `requirements.txt`:
   ```
   flask
   flask-cors
   google-genai
   requests
   python-dotenv
   gunicorn
   ```
3. Set environment variables in platform settings
4. Deploy and get public URL
5. Configure Zalo webhook with deployed URL

---

## API Endpoints

### POST /webhook
Receives Zalo OA events

**Events handled:**
- `user_send_text`: User sends message → Bot responds with answer
- `follow`: User follows OA → Bot sends welcome message

### POST /api/chat
Web chat interface (for testing without Zalo)

**Request:**
```json
{
  "message": "Your question here"
}
```

**Response:**
```json
{
  "answer": "Bot's answer",
  "citations": [],
  "success": true
}
```

### GET /api/health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "gemini_initialized": true,
  "file_search_store": true,
  "tokens_file_exists": true
}
```

---

## Features

✅ **Conversation History**: Bot remembers last 6 messages per user
✅ **Bilingual Support**: Auto-detects Vietnamese/English and responds accordingly
✅ **Document Grounding**: Answers based on uploaded technical documents
✅ **Welcome Message**: Auto-sends when user follows OA
✅ **Error Handling**: Graceful error messages to users
✅ **Token Auto-Refresh**: Keep access tokens fresh

---

## Next Steps

1. **Add more documents**: Use `upload_document.py` to add more PDFs
2. **Improve prompts**: Edit system prompt in `app_zalo.py` for better answers
3. **Add analytics**: Track user questions and popular topics
4. **Add buttons/templates**: Enhance UX with Zalo message templates
5. **Setup monitoring**: Use logging/monitoring service for production

---

## Security Notes

⚠️ **Never commit these files:**
- `tokens.json` - Contains access tokens
- `.env` - Contains API keys and secrets

✅ **Always:**
- Use HTTPS in production
- Rotate tokens regularly
- Monitor webhook for suspicious activity
- Rate limit API calls
- Validate webhook requests

---

## Support

For issues or questions:
- Check logs in Flask console
- Test health endpoint: `/api/health`
- Verify Gemini FileSearch is working via `/api/chat`
- Check Zalo Developers Console for webhook delivery status

---

**Ready to go! 🚀**

Your Zalo OA chatbot is now integrated with Gemini RAG engine.
