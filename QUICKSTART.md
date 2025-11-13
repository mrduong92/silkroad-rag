# Hướng dẫn nhanh - Quick Start

## Setup trong 5 phút

### 1. Cài đặt dependencies

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. Lấy Gemini API Key

1. Truy cập: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy API key

### 3. Tạo file .env

```bash
cp .env.example .env
```

Chỉnh sửa `.env`:
```env
GEMINI_API_KEY=paste_your_api_key_here
```

### 4. Thêm tài liệu PDF

```bash
# Tải file PDF từ Google Drive:
# https://drive.google.com/file/d/10-GqTQQOHnchKoMGXYEkVOJjzbdqBvpn/view
# Đặt vào thư mục documents/

# Hoặc dùng curl (nếu file public):
# curl -L "your-pdf-link" -o documents/document.pdf
```

### 5. Upload tài liệu

```bash
python upload_document.py
```

Chọn option 1 (Create new store), nhấn Enter để dùng tên mặc định.

### 6. Chạy chatbot

```bash
python app.py
```

Mở trình duyệt: http://localhost:5000

## Xong! Giờ bạn có thể chat với bot.

---

## Câu hỏi thường gặp

**Q: Tôi gặp lỗi "GEMINI_API_KEY is not set"?**

A: Kiểm tra file `.env` có chứa API key và đang ở cùng thư mục với `app.py`

**Q: Bot không trả lời chính xác?**

A:
- Kiểm tra PDF đã upload thành công chưa
- Thử hỏi câu hỏi cụ thể hơn
- Giảm `TEMPERATURE` trong `config.py`

**Q: Làm sao thêm nhiều tài liệu?**

A: Đặt nhiều PDF vào `documents/` rồi chạy lại `python upload_document.py`, chọn option 2 để dùng store hiện tại.

**Q: API có miễn phí không?**

A: Có! Gemini API có free tier:
- 1GB storage
- 1,500 requests/ngày
- Đủ cho dự án nhỏ

---

**Cần hỗ trợ?** Đọc README.md để biết chi tiết.
