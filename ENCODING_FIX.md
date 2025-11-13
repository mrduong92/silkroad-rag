# Fix lỗi Unicode Encoding với filename tiếng Việt

## Vấn đề

Lỗi: `'ascii' codec can't encode character '\u0110' in position X: ordinal not in range(128)`

**Nguyên nhân:**
- Terminal/shell đang dùng ASCII encoding thay vì UTF-8
- Python cố gắng print filename tiếng Việt nhưng output encoding không hỗ trợ

## Giải pháp đã áp dụng

### 1. Cập nhật `upload_document.py`

Đã thêm code tự động fix encoding:

```python
# Fix encoding for Vietnamese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

### 2. Safe print cho filename tiếng Việt

Thêm try-except để handle encoding errors:

```python
try:
    print(f"  - {pdf.name} ({file_size:.2f} MB)")
except UnicodeEncodeError:
    print(f"  - {pdf.name.encode('utf-8', errors='replace').decode('utf-8')} ({file_size:.2f} MB)")
```

### 3. Tạo wrapper scripts

**run_upload.sh** và **run_app.sh** để set environment variables.

## Cách chạy (3 phương án)

### ✅ Phương án 1: Dùng wrapper script (Khuyến nghị)

```bash
# Upload documents
./run_upload.sh

# Start chatbot
./run_app.sh
```

### ✅ Phương án 2: Set environment variables

```bash
# Set UTF-8 encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

# Chạy scripts
python3 upload_document.py
python3 app.py
```

### ✅ Phương án 3: Inline environment

```bash
# Upload
PYTHONIOENCODING=utf-8 python3 upload_document.py

# Run app
PYTHONIOENCODING=utf-8 python3 app.py
```

## Kiểm tra encoding hiện tại

Chạy script này để check:

```bash
python3 check_locale.py
```

Kết quả mong muốn:
```
sys.stdout.encoding: UTF-8 (hoặc utf-8)
locale.getpreferredencoding(): UTF-8
LANG: en_US.UTF-8
```

## Nếu vẫn gặp lỗi

### Option 1: Đổi tên file PDF sang tiếng Anh

```bash
cd documents/
mv "TT 17-2024-TT-BTC (14.3.2024)-Hướng dẫn KS..." "circular-17-2024.pdf"
```

### Option 2: Set locale system-wide (macOS)

Thêm vào `~/.bash_profile` hoặc `~/.zshrc`:

```bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8
```

Sau đó reload:
```bash
source ~/.bash_profile  # hoặc source ~/.zshrc
```

### Option 3: Chạy Python với explicit encoding

```bash
python3 -X utf8 upload_document.py
```

## Test nhanh

```bash
# Test 1: Check Python encoding
python3 -c "import sys; print(f'stdout: {sys.stdout.encoding}')"

# Test 2: Test Vietnamese print
python3 -c "print('Đây là test tiếng Việt')"

# Test 3: Run upload with verbose encoding info
PYTHONIOENCODING=utf-8 python3 upload_document.py
```

## Note quan trọng

**Gemini API không có vấn đề với tiếng Việt!**

- ✅ Gemini API hỗ trợ UTF-8 hoàn toàn
- ✅ Có thể upload file tên tiếng Việt
- ✅ Có thể search và query tiếng Việt
- ❌ Lỗi chỉ xảy ra khi Python **print** filename ra terminal

Sau khi fix encoding, mọi thứ sẽ hoạt động bình thường!

## Summary

**Lỗi đã được fix tại:**
- `upload_document.py`: dòng 15-19 (auto UTF-8 fix)
- `upload_document.py`: dòng 40-44, 164-168 (safe print)

**Cách chạy:**
```bash
./run_upload.sh          # Thay vì: python3 upload_document.py
./run_app.sh             # Thay vì: python3 app.py
```

Hoặc:
```bash
PYTHONIOENCODING=utf-8 python3 upload_document.py
PYTHONIOENCODING=utf-8 python3 app.py
```

---

**Nếu vẫn gặp vấn đề, chạy:**
```bash
python3 check_locale.py
```

Và gửi kết quả cho tôi!
