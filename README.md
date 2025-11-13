# Silkroad RAG Chatbot

Chatbot thông minh sử dụng Google Gemini API với FileSearch để trả lời câu hỏi dựa trên tài liệu PDF. Hỗ trợ tiếng Việt và tiếng Anh.

Intelligent chatbot using Google Gemini API with FileSearch to answer questions based on PDF documents. Supports Vietnamese and English.

## Tính năng / Features

- ✅ Hỏi đáp dựa trên tài liệu PDF (RAG - Retrieval Augmented Generation)
- ✅ Hỗ trợ đa ngôn ngữ (tiếng Việt & tiếng Anh)
- ✅ Semantic search thông minh
- ✅ Trích dẫn nguồn từ tài liệu
- ✅ Lưu lịch sử chat
- ✅ Giao diện đẹp và responsive
- ✅ Dễ dàng tích hợp và mở rộng

## Công nghệ / Technology Stack

- **Backend**: Flask (Python)
- **AI/ML**: Google Gemini API với FileSearch
- **Frontend**: HTML, CSS, JavaScript
- **Database**: In-memory (có thể mở rộng sang Redis/PostgreSQL)

## Cấu trúc dự án / Project Structure

```
silkroad-rag/
├── app.py                  # Flask application chính
├── config.py               # Configuration
├── upload_document.py      # Script upload PDF vào FileSearch Store
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (tạo từ .env.example)
├── .env.example           # Template cho environment variables
├── documents/             # Thư mục chứa tài liệu PDF
├── templates/
│   └── index.html         # Frontend HTML
├── static/
│   ├── css/
│   │   └── style.css      # Styling
│   └── js/
│       └── chat.js        # Chat functionality
└── README.md              # Documentation
```

## Yêu cầu / Requirements

- Python 3.8+
- Google Gemini API Key (miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey))
- Tài liệu PDF cần index

## Cài đặt / Installation

### 1. Clone hoặc tạo project

```bash
cd silkroad-rag
```

### 2. Tạo môi trường ảo Python

```bash
python -m venv venv

# Trên macOS/Linux:
source venv/bin/activate

# Trên Windows:
venv\Scripts\activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình môi trường

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env` và thêm Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
FILE_SEARCH_STORE_ID=
FLASK_ENV=development
FLASK_DEBUG=True
```

**Lấy API Key:**
1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập với Google account
3. Click "Create API Key"
4. Copy và paste vào `.env`

### 5. Upload tài liệu PDF

**Bước 1:** Đặt file PDF vào thư mục `documents/`

```bash
# Tải file PDF từ Google Drive về máy
# Sau đó copy vào thư mục documents/
cp ~/Downloads/your-document.pdf documents/
```

**Bước 2:** Chạy script upload

```bash
python upload_document.py
```

Script sẽ:
- Tạo FileSearch Store trên Gemini
- Upload và index tài liệu PDF
- Tự động cập nhật `FILE_SEARCH_STORE_ID` vào `.env`

**Lưu ý:** Chỉ cần chạy script này **một lần** khi setup ban đầu, hoặc khi muốn thêm tài liệu mới.

### 6. Chạy ứng dụng

```bash
python app.py
```

Chatbot sẽ chạy tại: http://localhost:5000

## Sử dụng / Usage

### Chat với Bot

1. Mở trình duyệt và truy cập http://localhost:5000
2. Nhập câu hỏi bằng tiếng Việt hoặc tiếng Anh
3. Bot sẽ trả lời dựa trên nội dung tài liệu
4. Xem citations (trích dẫn nguồn) nếu có

### Ví dụ câu hỏi

**Tiếng Việt:**
- "Silkroad là gì?"
- "Tóm tắt nội dung chính của tài liệu"
- "Giải thích về [khái niệm] trong tài liệu"

**Tiếng Anh:**
- "What is Silkroad?"
- "Summarize the main content"
- "Explain [concept] from the document"

### API Endpoints

Ứng dụng cung cấp REST API:

#### POST /api/chat
Gửi câu hỏi và nhận câu trả lời

**Request:**
```json
{
  "message": "What is Silkroad?"
}
```

**Response:**
```json
{
  "answer": "Silkroad is...",
  "citations": [
    {
      "title": "Document Title",
      "uri": "file://..."
    }
  ],
  "success": true
}
```

#### GET /api/history
Lấy lịch sử chat của session

**Response:**
```json
{
  "history": [
    {
      "role": "user",
      "content": "What is Silkroad?",
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  "success": true
}
```

#### POST /api/clear
Xóa lịch sử chat

#### GET /api/health
Health check endpoint

## Tùy chỉnh / Customization

### Thay đổi Model

Trong `config.py`, bạn có thể thay đổi model:

```python
MODEL_NAME = 'gemini-2.0-flash-exp'  # Nhanh, miễn phí
# hoặc
MODEL_NAME = 'gemini-2.5-pro'        # Chất lượng cao hơn
```

### Điều chỉnh độ chính xác

Trong `config.py`:

```python
TEMPERATURE = 0.2  # 0.0 = deterministic, 1.0 = creative
```

### Chunking Configuration

Trong `upload_document.py`, điều chỉnh cách chia nhỏ tài liệu:

```python
chunking_config=types.ChunkingConfig(
    chunk_size=800,      # Số tokens mỗi chunk
    chunk_overlap=100    # Overlap giữa các chunks
)
```

## Xử lý lỗi / Troubleshooting

### Lỗi: "GEMINI_API_KEY is not set"
- Kiểm tra file `.env` có chứa API key
- Chạy `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GEMINI_API_KEY'))"`

### Lỗi: "FILE_SEARCH_STORE_ID is not set"
- Chạy `python upload_document.py` để tạo store và upload tài liệu

### Bot trả lời không chính xác
- Kiểm tra tài liệu PDF đã được upload đúng
- Thử giảm `TEMPERATURE` trong `config.py`
- Thử model `gemini-2.5-pro` để có kết quả tốt hơn

### Lỗi kết nối
- Kiểm tra internet connection
- Verify API key còn hiệu lực
- Kiểm tra quota của Gemini API

## Giới hạn / Limitations

### Free Tier (Gemini API)
- Tối đa 1GB storage cho FileSearch
- 1,500 requests/day
- Rate limit: 15 RPM (requests per minute)

### File Size
- Mỗi PDF tối đa 100MB
- Khuyến nghị giữ store dưới 20GB cho performance tốt

## Mở rộng / Future Enhancements

- [ ] Hỗ trợ nhiều tài liệu PDF
- [ ] Upload PDF qua web interface
- [ ] Database persistent (PostgreSQL/MongoDB)
- [ ] User authentication
- [ ] Export chat history
- [ ] Multi-turn conversation context
- [ ] Deploy lên cloud (Heroku/Railway/Vercel)

## Deploy lên Production

### Sử dụng Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker (Optional)

Tạo `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build và chạy:

```bash
docker build -t silkroad-rag .
docker run -p 5000:5000 --env-file .env silkroad-rag
```

## Bảo mật / Security

⚠️ **Quan trọng:**

- **KHÔNG** commit file `.env` vào Git
- **KHÔNG** share API key công khai
- Sử dụng HTTPS khi deploy production
- Implement rate limiting cho API endpoints
- Sanitize user inputs

## Giấy phép / License

MIT License - Tự do sử dụng cho mục đích cá nhân và thương mại.

## Liên hệ / Contact

Nếu có vấn đề hoặc câu hỏi, vui lòng tạo issue hoặc liên hệ.

---

**Built with ❤️ using Google Gemini API**
