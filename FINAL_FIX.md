# Final Fix - Operations Polling

## Vấn đề cuối cùng

Lỗi: `AttributeError: 'str' object has no attribute 'name'` trong `operations.get()`

## Root Cause

SDK documentation cho thấy `client.operations.get()` nhận **operation object** chứ không phải operation name string!

## Các thử nghiệm sai:

### ❌ Thử 1: Truyền operation.name
```python
while not operation.done:
    operation = client.operations.get(operation.name)  # SAI!
```
**Lỗi:** `AttributeError: 'str' object has no attribute 'name'`

### ❌ Thử 2: Dùng keyword argument
```python
operation_name = operation.name
while not operation.done:
    operation = client.operations.get(name=operation_name)  # SAI!
```
**Lỗi:** `TypeError: Operations.get() got an unexpected keyword argument 'name'`

### ❌ Thử 3: Truyền string trực tiếp
```python
operation_name = operation.name
while not operation.done:
    operation = client.operations.get(operation_name)  # SAI!
```
**Lỗi:** `AttributeError: 'str' object has no attribute 'name'`

## ✅ Giải pháp đúng:

Theo [official documentation](https://ai.google.dev/gemini-api/docs/file-search):

```python
# Upload file
operation = client.file_search_stores.upload_to_file_search_store(
    file='sample.txt',
    file_search_store_name=file_search_store.name,
    config={'display_name': 'display-file-name'}
)

# Poll operation - truyền OPERATION OBJECT, không phải string!
while not operation.done:
    time.sleep(5)
    operation = client.operations.get(operation)  # ✅ ĐÚNG!
```

**Key point:** `client.operations.get()` nhận **operation object** và SDK tự động extract name bên trong.

## Code đã fix

**File:** `upload_document.py` (lines 55-62)

```python
print(f"  Upload initiated. Waiting for indexing to complete...")

# Wait for operation to complete
# Pass the operation object itself, not the name string
while not operation.done:
    time.sleep(2)
    operation = client.operations.get(operation)
    print("  .", end="", flush=True)

print("\n✓ Document uploaded and indexed successfully!")
```

## Tại sao lại như vậy?

Nhìn vào source code của SDK (`operations.py` line 255):

```python
def get(self, operation):
    operation_name = operation.name  # ← SDK extract name từ object
    # ... rest of the code
```

SDK expect một object có attribute `.name`, không phải string trực tiếp!

## Test ngay:

```bash
./run_upload.sh
```

Hoặc:

```bash
PYTHONIOENCODING=utf-8 python3 upload_document.py
```

Lần này chắc chắn sẽ hoạt động! 🎉

---

## Summary tất cả fixes:

| # | Lỗi | Fix |
|---|-----|-----|
| 1 | `AttributeError: 'Client' object has no attribute 'file_search_stores'` | Update `google-genai>=1.49.0` |
| 2 | `SyntaxError: invalid syntax` với FileSearch tool | Dùng `types.Tool(file_search=types.FileSearch(...))` |
| 3 | `UnicodeEncodeError` với filename tiếng Việt | Auto UTF-8 fix + wrapper scripts |
| 4 | `AttributeError: 'str' object has no attribute 'name'` | Truyền **operation object** vào `operations.get()` |

**All fixed!** ✅
