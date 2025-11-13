# Kiến trúc hệ thống - System Architecture

## Tổng quan / Overview

Silkroad RAG Chatbot sử dụng kiến trúc RAG (Retrieval-Augmented Generation) với Gemini FileSearch API.

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│       Frontend (HTML/CSS/JS)        │
│  - Chat Interface                   │
│  - Message Display                  │
│  - User Input                       │
└────────────────┬────────────────────┘
                 │ HTTP/JSON
                 ▼
┌─────────────────────────────────────┐
│       Flask Backend                 │
│  - /api/chat endpoint               │
│  - Session management               │
│  - Chat history                     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│     Gemini API Client               │
│  - Query formatting                 │
│  - FileSearch tool config           │
│  - Response parsing                 │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│   Gemini FileSearch Service         │
│  ┌───────────────────────────────┐  │
│  │  FileSearch Store             │  │
│  │  - Indexed PDF documents      │  │
│  │  - Embeddings                 │  │
│  │  - Semantic search index      │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Gemini LLM                   │  │
│  │  - gemini-2.0-flash-exp       │  │
│  │  - Answer generation          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Luồng hoạt động / Workflow

### 1. Upload & Indexing Phase (Chỉ chạy 1 lần)

```
PDF Document
    │
    ▼
[upload_document.py]
    │
    ├─► Create FileSearch Store
    │
    ├─► Upload PDF to Gemini
    │
    ├─► Chunking (800 tokens/chunk)
    │
    ├─► Generate Embeddings
    │
    └─► Store in FileSearch Index
```

**Chi tiết:**

1. **Upload PDF**: File được upload lên Gemini Files API
2. **Chunking**: Tài liệu được chia thành các chunks (~800 tokens mỗi chunk, overlap 100 tokens)
3. **Embedding**: Mỗi chunk được convert thành embedding vector (1024 dimensions)
4. **Indexing**: Embeddings được lưu vào FileSearch Store với semantic index
5. **Store ID**: ID của store được lưu vào `.env` để sử dụng sau

### 2. Query Phase (Mỗi khi user hỏi)

```
User Question
    │
    ▼
[Frontend] Send to /api/chat
    │
    ▼
[Flask Backend]
    │
    ├─► Get session history
    │
    ├─► Build context prompt
    │
    └─► Query Gemini API
            │
            ▼
[Gemini FileSearch]
    │
    ├─► Convert query to embedding
    │
    ├─► Semantic search in FileSearch Store
    │       │
    │       ├─► Find top K relevant chunks (typically K=3-5)
    │       │
    │       └─► Compute similarity scores
    │
    ├─► Retrieve relevant document chunks
    │
    └─► Pass to LLM with context
            │
            ▼
[Gemini LLM]
    │
    ├─► Generate answer based on:
    │       - User question
    │       - Retrieved chunks
    │       - Chat history
    │       - System prompt
    │
    └─► Return answer + grounding metadata
            │
            ▼
[Flask Backend]
    │
    ├─► Extract answer text
    │
    ├─► Extract citations
    │
    ├─► Save to chat history
    │
    └─► Send JSON response
            │
            ▼
[Frontend]
    │
    └─► Display answer + citations
```

## Components chi tiết

### 1. Frontend (templates/index.html + static/)

**Nhiệm vụ:**
- Hiển thị giao diện chat
- Gửi câu hỏi qua API
- Nhận và hiển thị câu trả lời
- Quản lý UX (typing indicator, scroll, etc.)

**Technologies:**
- Vanilla JavaScript (no frameworks)
- Responsive CSS
- Fetch API cho HTTP requests

### 2. Flask Backend (app.py)

**Endpoints:**

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Serve HTML page |
| `/api/chat` | POST | Xử lý câu hỏi user |
| `/api/history` | GET | Lấy lịch sử chat |
| `/api/clear` | POST | Xóa lịch sử |
| `/api/health` | GET | Health check |

**Features:**
- Session management (UUID-based)
- In-memory chat history (per session)
- Context building từ lịch sử
- Error handling

### 3. Gemini FileSearch Integration

**FileSearch Tool Configuration:**

```python
config=types.GenerateContentConfig(
    tools=[
        types.Tool(
            file_search=types.FileSearchTool(
                file_search_store_names=[store_id]
            )
        )
    ],
    temperature=0.2,
    response_modalities=["TEXT"],
)
```

**Cách hoạt động:**

1. **Semantic Search**: Gemini tự động:
   - Convert câu hỏi thành embedding
   - Tìm kiếm trong FileSearch Store
   - Retrieve top relevant chunks

2. **Grounding**: LLM generate câu trả lời dựa trên:
   - Retrieved chunks (RAG context)
   - System prompt
   - Chat history

3. **Citations**: Gemini trả về grounding metadata:
   - Document sources
   - Chunk references
   - Confidence scores

## Semantic Search Pipeline

```
User Query: "Silkroad là gì?"
    │
    ▼
Query Embedding
[0.123, -0.456, 0.789, ...]  (1024 dimensions)
    │
    ▼
Vector Similarity Search
    │
    ├─► Chunk 1: "Silkroad là một nền tảng..." (similarity: 0.92)
    ├─► Chunk 2: "Định nghĩa Silkroad..." (similarity: 0.88)
    └─► Chunk 3: "Tính năng của Silkroad..." (similarity: 0.85)
    │
    ▼
Top 3 chunks retrieved
    │
    ▼
LLM Context
"""
System: Bạn là trợ lý AI...
Context:
- Chunk 1: Silkroad là một nền tảng...
- Chunk 2: Định nghĩa Silkroad...
- Chunk 3: Tính năng của Silkroad...

User: Silkroad là gì?
"""
    │
    ▼
LLM generates answer
"Silkroad là một nền tảng..."
```

## Data Flow

### Request Flow

```
1. User Input
   ↓
2. Frontend validates & sends
   POST /api/chat {"message": "..."}
   ↓
3. Flask receives request
   ↓
4. Get/Create session_id
   ↓
5. Load chat history
   ↓
6. Build context prompt
   system_prompt + history + user_question
   ↓
7. Call Gemini API
   gemini_client.models.generate_content(...)
   ↓
8. Gemini FileSearch:
   - Semantic search
   - Retrieve chunks
   - Generate answer
   ↓
9. Parse response
   - Extract answer text
   - Extract citations
   ↓
10. Save to history
    ↓
11. Return JSON
    {"answer": "...", "citations": [...]}
    ↓
12. Frontend displays
```

### Session Management

```python
# In-memory structure
chat_sessions = {
    'session-uuid-1': {
        'messages': [
            {'role': 'user', 'content': '...', 'timestamp': '...'},
            {'role': 'assistant', 'content': '...', 'timestamp': '...'},
        ],
        'created_at': '2024-01-01T10:00:00'
    }
}
```

## Scalability Considerations

### Current Implementation (MVP)
- In-memory session storage
- Single server
- Good for: 10-100 concurrent users

### Recommended Improvements

**1. Session Storage:**
```
In-Memory → Redis
- Distributed sessions
- Persistent across restarts
- Support multiple servers
```

**2. Database:**
```
In-Memory → PostgreSQL/MongoDB
- Store chat history permanently
- User accounts
- Analytics
```

**3. Caching:**
```
Add Redis caching for:
- Frequently asked questions
- Gemini API responses
- Reduce API calls & latency
```

**4. Load Balancing:**
```
nginx → [Flask Server 1]
      → [Flask Server 2]
      → [Flask Server 3]
```

**5. Async Processing:**
```
Flask → FastAPI + async
- Better concurrent handling
- WebSocket support for streaming
```

## Performance Optimization

### Current Performance
- Query latency: ~2-5 seconds (depends on Gemini API)
- Throughput: ~15 requests/minute (API rate limit)

### Optimization Tips

**1. Reduce latency:**
- Use `gemini-2.0-flash-exp` (faster) vs `gemini-2.5-pro`
- Implement response streaming
- Cache common queries

**2. Handle rate limits:**
```python
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(min=1, max=10))
def query_gemini_with_retry(...):
    # Automatic retry with exponential backoff
    pass
```

**3. Optimize chunking:**
```python
# Experiment with chunk size
chunk_size=800      # Smaller = more precise, more chunks
chunk_size=1200     # Larger = more context, fewer chunks

# Adjust overlap
chunk_overlap=100   # Less overlap = faster indexing
chunk_overlap=200   # More overlap = better retrieval
```

## Security Considerations

### Current Implementation
- Flask secret key (basic session security)
- CORS enabled (development)
- No authentication

### Recommended Improvements

**1. Authentication:**
```python
from flask_login import LoginManager, login_required

@app.route('/api/chat')
@login_required
def chat():
    pass
```

**2. Rate Limiting:**
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/chat')
@limiter.limit("10 per minute")
def chat():
    pass
```

**3. Input Sanitization:**
```python
import bleach

user_message = bleach.clean(user_message)
```

**4. API Key Protection:**
- Use environment variables (✓ already done)
- Never expose in client-side code (✓ already done)
- Rotate keys regularly

**5. HTTPS:**
- Use SSL/TLS in production
- Configure Flask with proper security headers

## Monitoring & Logging

### Recommended Additions

**1. Logging:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log queries
logger.info(f"User query: {user_message}")
logger.info(f"Response time: {response_time}ms")
```

**2. Metrics:**
- Query count
- Response times
- Error rates
- Popular questions

**3. Alerts:**
- API quota exceeded
- High error rates
- Slow responses

## Cost Estimation

### Gemini API Pricing (Free Tier)

| Resource | Free Tier | Cost After Limit |
|----------|-----------|------------------|
| Storage | 1 GB | Free |
| Indexing | 1M tokens/day | $0.15/1M tokens |
| Queries | 1,500/day | Context tokens pricing |

### Example Usage Cost

**Scenario:** 100 users, 10 questions/user/day

- Total queries: 1,000/day (within free tier ✓)
- Average response: 500 tokens
- Total tokens: 500K/day (within free tier ✓)

**Cost: $0/month** (within free tier)

For production scale, estimate ~$10-50/month for 10K queries/day.

## Conclusion

Hệ thống sử dụng kiến trúc RAG đơn giản nhưng hiệu quả:

✅ **Ưu điểm:**
- Dễ setup và maintain
- Chi phí thấp (miễn phí cho MVP)
- Chính xác cao (semantic search)
- Hỗ trợ đa ngôn ngữ tự động

⚠️ **Limitations:**
- Single server (for now)
- In-memory storage
- API rate limits
- No authentication

🚀 **Next Steps:**
- Deploy to production
- Add user authentication
- Implement caching
- Monitor và optimize
