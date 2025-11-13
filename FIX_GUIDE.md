# Hướng dẫn Fix lỗi AttributeError

## Vấn đề

Lỗi `AttributeError: 'Client' object has no attribute 'file_search_stores'` xảy ra do:
- Package `google-genai` version cũ (1.0.0) không hỗ trợ FileSearch
- FileSearch chỉ có từ version **1.49.0** trở lên

## Giải pháp đã fix

Tôi đã cập nhật các file sau:

### 1. requirements.txt
- Changed: `google-genai==1.0.0` → `google-genai>=1.49.0`

### 2. upload_document.py
- Updated API syntax cho FileSearch
- Sử dụng `upload_to_file_search_store()` method
- Thêm error handling và progress tracking

### 3. app.py
- Fixed FileSearch tool configuration syntax
- Simplified tool definition

### 4. config.py
- Updated model name: `gemini-2.5-flash`

## Các bước fix (cho user)

### Bước 1: Cập nhật package

```bash
# Uninstall version cũ
pip uninstall google-genai -y

# Install version mới nhất
pip install google-genai>=1.49.0

# Hoặc install tất cả dependencies mới
pip install -r requirements.txt --upgrade
```

### Bước 2: Verify installation

```bash
# Kiểm tra version đã cài
pip show google-genai
```

Kết quả phải hiển thị version >= 1.49.0:
```
Name: google-genai
Version: 1.49.0 (hoặc cao hơn)
```

### Bước 3: Chạy lại upload script

```bash
python upload_document.py
```

Script sẽ:
1. Initialize Gemini client với API key từ `.env`
2. Tạo hoặc chọn FileSearch store
3. Upload PDF files từ thư mục `documents/`
4. Index tài liệu (có thể mất vài phút)
5. Lưu Store ID vào `.env`

### Bước 4: Kiểm tra .env file

Sau khi upload thành công, file `.env` sẽ có:

```env
GEMINI_API_KEY=your_api_key_here
FILE_SEARCH_STORE_ID=fileSearchStores/xxxxx
```

### Bước 5: Chạy chatbot

```bash
python app.py
```

Mở trình duyệt: http://localhost:5000

## Troubleshooting

### Lỗi: "ImportError: cannot import name 'types'"

**Fix:**
```bash
pip install google-genai --upgrade --force-reinstall
```

### Lỗi: "API key not valid"

**Fix:**
1. Kiểm tra API key tại: https://aistudio.google.com/app/apikey
2. Verify key trong file `.env`
3. Thử tạo API key mới

### Lỗi: "Operation timed out"

**Fix:**
- File PDF quá lớn (>100MB)
- Mạng không ổn định
- Thử upload file nhỏ hơn hoặc check internet

### Lỗi: "Model not found: gemini-2.5-flash"

**Fix:**
Nếu model chưa available ở region của bạn, dùng model khác trong `config.py`:

```python
MODEL_NAME = 'gemini-2.0-flash-exp'  # Alternative
# or
MODEL_NAME = 'gemini-1.5-flash'      # Fallback
```

## Kiểm tra hoạt động

### Test 1: Check API connection

```bash
python -c "
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
print('✓ Client initialized successfully')
stores = list(client.file_search_stores.list())
print(f'✓ Found {len(stores)} FileSearch stores')
"
```

### Test 2: List existing stores

```bash
python -c "
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
for store in client.file_search_stores.list():
    print(f'Store: {store.display_name}')
    print(f'ID: {store.name}')
"
```

### Test 3: Query test

Sau khi chạy `app.py`, test qua API:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test question"}'
```

## Thay đổi chính trong code

### upload_document.py (trước)

```python
# Cũ - KHÔNG HOẠT ĐỘNG
upload_response = client.files.upload(path=file_path)
import_operation = client.file_search_stores.import_file(...)
```

### upload_document.py (sau)

```python
# Mới - HOẠT ĐỘNG
operation = client.file_search_stores.upload_to_file_search_store(
    file=str(file_path),
    file_search_store_name=file_search_store.name,
    config={'display_name': file_name}
)
while not operation.done:
    time.sleep(2)
    operation = client.operations.get(operation.name)
```

### app.py (trước)

```python
# Cũ - Cú pháp phức tạp
tools=[
    types.Tool(
        file_search=types.FileSearchTool(
            file_search_store_names=[store_id]
        )
    )
]
```

### app.py (sau)

```python
# Mới - Cú pháp đơn giản
tools=[
    file_search=(
        file_search_store_names=[store_id]
    )
]
```

## Summary

Lỗi đã được fix bằng cách:
1. ✅ Update `google-genai` từ 1.0.0 → >=1.49.0
2. ✅ Fix API syntax trong `upload_document.py`
3. ✅ Simplify tool config trong `app.py`
4. ✅ Update model name trong `config.py`

Bây giờ bạn có thể chạy lại:
```bash
pip install -r requirements.txt --upgrade
python upload_document.py
python app.py
```

---

**Nếu vẫn gặp vấn đề, vui lòng cung cấp:**
1. Output của `pip show google-genai`
2. Full error message
3. Output của `python upload_document.py`
