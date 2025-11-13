# Changelog - Silkroad RAG Chatbot

## [Fixed] - 2025-11-12

### Bug Fixes

#### 1. AttributeError: 'Client' object has no attribute 'file_search_stores'
**Lỗi:** Package version quá cũ (1.0.0) không hỗ trợ FileSearch

**Fix:**
- Updated `requirements.txt`: `google-genai>=1.49.0`
- Fixed API syntax trong `upload_document.py` và `app.py`

**Files changed:**
- `requirements.txt`
- `upload_document.py` (lines 35-53)
- `app.py` (lines 108-123)

#### 2. SyntaxError: invalid syntax with FileSearch tool
**Lỗi:** Cú pháp FileSearch tool configuration sai

**Fix:**
```python
# Trước (SAI):
tools=[
    file_search=(
        file_search_store_names=[store_id]
    )
]

# Sau (ĐÚNG):
tools=[
    types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[store_id]
        )
    )
]
```

**File changed:** `app.py` (lines 114-118)

#### 3. UnicodeEncodeError: 'ascii' codec can't encode Vietnamese characters
**Lỗi:** Terminal encoding không hỗ trợ tiếng Việt

**Fix:**
- Added UTF-8 encoding fix ở đầu script
- Safe print với try-except cho filename tiếng Việt
- Tạo wrapper scripts (`run_upload.sh`, `run_app.sh`)

**Files changed:**
- `upload_document.py` (lines 15-19, 40-44, 164-168)
- Created: `run_upload.sh`
- Created: `run_app.sh`
- Created: `ENCODING_FIX.md`

#### 4. AttributeError: 'str' object has no attribute 'name' in operations.get()
**Lỗi:** Gọi `client.operations.get()` sai cách

**Fix:**
```python
# Trước (SAI):
while not operation.done:
    operation = client.operations.get(operation.name)

# Sau (ĐÚNG):
operation_name = operation.name
while not operation.done:
    operation = client.operations.get(name=operation_name)
```

**File changed:** `upload_document.py` (lines 57-64)

### New Features

#### 1. Setup Diagnostic Tool
**File:** `test_setup.py`

Kiểm tra:
- Python version
- Package installation
- .env configuration
- Documents folder
- Gemini API connection

#### 2. Locale Check Tool
**File:** `check_locale.py`

Kiểm tra encoding settings của hệ thống.

#### 3. Documentation
**Files created:**
- `FIX_GUIDE.md` - Chi tiết về các bug fixes
- `ENCODING_FIX.md` - Hướng dẫn fix Unicode encoding
- `CHANGELOG.md` - Lịch sử thay đổi

### Code Improvements

#### 1. Error Handling
- Added detailed error messages
- Added traceback printing
- Safe encoding fallbacks

#### 2. UTF-8 Encoding Declaration
Added `# -*- coding: utf-8 -*-` to all Python files:
- `app.py`
- `config.py`
- `upload_document.py`

#### 3. Progress Tracking
- Added progress dots during upload
- File size display
- Store listing with details

## Version History

### v1.1.0 (Current)
- ✅ FileSearch working with latest Gemini API
- ✅ Full Vietnamese support
- ✅ Proper error handling
- ✅ UTF-8 encoding fixes
- ✅ Diagnostic tools

### v1.0.0 (Initial)
- Basic Flask chatbot
- Gemini FileSearch integration
- PDF upload functionality
- Chat interface

## Known Issues

None currently!

## Upcoming Features

- [ ] Multiple file upload via web interface
- [ ] User authentication
- [ ] Chat history persistence (database)
- [ ] Export chat to PDF/Markdown
- [ ] Streaming responses
- [ ] Multi-language UI toggle

## Migration Guide

### From v1.0.0 to v1.1.0

1. Update packages:
```bash
pip install -r requirements.txt --upgrade
```

2. Run with wrapper scripts:
```bash
./run_upload.sh  # Instead of: python3 upload_document.py
./run_app.sh     # Instead of: python3 app.py
```

Or set environment:
```bash
export PYTHONIOENCODING=utf-8
python3 upload_document.py
```

## Support

Nếu gặp vấn đề:
1. Chạy `python3 test_setup.py` để chẩn đoán
2. Đọc `FIX_GUIDE.md` cho troubleshooting
3. Check `ENCODING_FIX.md` nếu gặp lỗi Unicode

---

**Last Updated:** 2025-11-12
