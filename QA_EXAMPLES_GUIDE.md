# Sử dụng Q&A Examples để cải thiện Chatbot

## 🎯 Mục tiêu

Chatbot **học từ các Q&A mẫu** trong file `sample_questions.xlsx` để:
1. ✅ Trả lời với **format nhất quán** như examples
2. ✅ **Độ dài phù hợp** (học từ examples)
3. ✅ **Style tương tự** (ngắn gọn nếu examples ngắn gọn)
4. ✅ **Tránh thông tin thừa** (examples không có → bot cũng không thêm)

## 🔧 Cách hoạt động: Few-Shot Learning

```
User Question: "Khả năng chống nước của vật liệu X?"
    ↓
[Bước 1] Tìm 3 câu hỏi TƯƠNG TỰ nhất từ sample_questions.xlsx
    ↓
Example 1: Q: "Khả năng chống cháy của vật liệu Y?"
           A: "Vật liệu Y có khả năng chống cháy cấp A1."
           Similarity: 85%

Example 2: Q: "Khả năng chống ẩm của vật liệu Z?"
           A: "Vật liệu Z chống ẩm tốt ở độ ẩm < 80%."
           Similarity: 78%

Example 3: Q: "Đặc tính chống nước của ABC?"
           A: "ABC có chỉ số chống nước IPX7."
           Similarity: 72%
    ↓
[Bước 2] Thêm examples vào prompt như few-shot learning
    ↓
[Bước 3] LLM học từ examples và trả lời theo style tương tự
    ↓
Answer: "Vật liệu X có khả năng chống nước cấp IP68."
        (Ngắn gọn, format giống examples, không thông tin thừa)
```

## 📋 Setup Guide

### **Bước 1: Chuẩn bị file Excel**

File `sample_questions.xlsx` cần có **2 cột**:

| Câu hỏi (Question) | Câu trả lời (Answer) |
|--------------------|----------------------|
| Tên các vật liệu chống nước? | Các vật liệu chống nước bao gồm: A, B, C. |
| Khả năng chống cháy của vật liệu X? | Vật liệu X có khả năng chống cháy cấp A1. |
| Đặc điểm của loại Y? | Loại Y có đặc điểm chính: độ bền cao, trọng lượng nhẹ. |

**Lưu ý:**
- Tên cột có thể là: "Question", "Câu hỏi", "Q", "Query"
- Tên cột answer: "Answer", "Câu trả lời", "A", "Response"
- Script sẽ tự động detect hoặc hỏi bạn chọn

### **Bước 2: Install dependencies**

```bash
pip install pandas openpyxl
```

### **Bước 3: Đặt file vào project**

```bash
# Đặt file sample_questions.xlsx vào thư mục gốc hoặc documents/
cp /path/to/sample_questions.xlsx .
```

### **Bước 4: Load Q&A examples**

```bash
python3 load_qa_examples.py
```

**Output:**
```
================================================================================
Q&A Examples Loader
================================================================================

Found 1 Excel file(s):
  1. sample_questions.xlsx

✓ Using: sample_questions.xlsx
✓ Loaded Excel file: sample_questions.xlsx
  Columns: ['Câu hỏi', 'Câu trả lời']
  Rows: 20

✓ Using columns:
  Question: Câu hỏi
  Answer: Câu trả lời

✓ Extracted 20 Q&A pairs

Preview of Q&A Examples (showing 5 of 20)
================================================================================

1. Q: Tên các vật liệu chống nước?
   A: Các vật liệu chống nước bao gồm: A, B, C.

2. Q: Khả năng chống cháy của vật liệu X?
   A: Vật liệu X có khả năng chống cháy cấp A1.

...

✓ Saved to qa_examples.json

✓ Loaded 20 Q&A pairs
✓ Saved to qa_examples.json
```

File `qa_examples.json` sẽ được tạo ra.

### **Bước 5: Chạy chatbot với examples**

```bash
python3 app_with_examples.py
```

**Output:**
```
============================================================
Silkroad RAG Chatbot - WITH Q&A EXAMPLES
============================================================

✓ Gemini client initialized successfully
✓ Loaded 20 Q&A examples
  Chatbot will learn from these examples

Server running at: http://localhost:5004
Features:
  - Few-shot learning from Q&A examples
  - Similarity-based example selection
  - Answer format learning
============================================================
```

### **Bước 6: Test chatbot**

Mở http://localhost:5004 và hỏi:

**Test 1:**
```
Q: Khả năng chống nước của vật liệu ABC?

Bot sẽ:
1. Tìm 3 câu hỏi tương tự trong examples
2. Học format từ examples
3. Trả lời theo style tương tự
```

---

## 🎨 Ví dụ thực tế

### **Example Set trong xlsx:**

| Câu hỏi | Câu trả lời |
|---------|-------------|
| Tên các vật liệu chống nước? | Các vật liệu chống nước: A, B, C. |
| Khả năng chống cháy của X? | X có khả năng chống cháy cấp A1. |
| Đặc điểm của Y? | Y có độ bền cao và trọng lượng nhẹ. |

### **User hỏi:**
```
Q: Tên các vật liệu chống ẩm?
```

### **Bot sẽ làm:**
```
1. Tìm example tương tự nhất:
   → "Tên các vật liệu chống nước?" (similarity 85%)

2. Học format:
   → Answer format: "Các vật liệu [tính năng]: A, B, C."
   → Style: Ngắn gọn, chỉ liệt kê tên
   → Không có mô tả chi tiết

3. Trả lời theo format đã học:
   → "Các vật liệu chống ẩm: P, Q, R."
```

### **So sánh:**

| Approach | Answer |
|----------|--------|
| **Không có examples** | "Các vật liệu chống ẩm bao gồm P, Q, R. Vật liệu P có đặc điểm... Vật liệu Q được sử dụng trong..." (200 từ, nhiều thông tin thừa) |
| **Với examples** | "Các vật liệu chống ẩm: P, Q, R." (12 từ, format giống example) |

---

## 🔄 Cập nhật examples

### **Thêm/sửa Q&A trong Excel:**

1. Mở `sample_questions.xlsx`
2. Thêm/sửa câu hỏi và câu trả lời
3. Lưu file

### **Reload examples:**

```bash
# Cách 1: Chạy lại load script
python3 load_qa_examples.py

# Cách 2: API endpoint (khi app đang chạy)
curl -X POST http://localhost:5004/api/reload-examples
```

---

## 📊 API Endpoints mới

### **GET /api/examples**

Lấy danh sách Q&A examples:

```bash
curl http://localhost:5004/api/examples
```

**Response:**
```json
{
  "examples": [
    {
      "id": 1,
      "question": "Tên các vật liệu chống nước?",
      "answer": "Các vật liệu chống nước: A, B, C."
    },
    ...
  ],
  "total": 20,
  "success": true
}
```

### **POST /api/reload-examples**

Reload examples từ file:

```bash
curl -X POST http://localhost:5004/api/reload-examples
```

### **POST /api/chat** (Enhanced)

Response giờ bao gồm `similar_examples`:

```json
{
  "answer": "Vật liệu X có khả năng chống nước cấp IP68.",
  "citations": [...],
  "similar_examples": [
    {
      "question": "Khả năng chống cháy của vật liệu Y?",
      "answer": "Vật liệu Y có khả năng chống cháy...",
      "similarity": "85%"
    }
  ],
  "success": true
}
```

---

## 🎯 Best Practices

### **1. Viết examples tốt:**

✅ **TỐT:**
```
Q: Tên các vật liệu chống nước?
A: Các vật liệu chống nước: A, B, C.

(Ngắn gọn, rõ ràng, format nhất quán)
```

❌ **TRÁNH:**
```
Q: Cho tôi biết về các vật liệu có khả năng chống nước?
A: Vâng, có nhiều loại vật liệu chống nước khác nhau. Đầu tiên là A, đây là loại...

(Dài dòng, không consistent)
```

### **2. Số lượng examples:**

- **Tối thiểu:** 10-15 examples
- **Khuyến nghị:** 20-50 examples
- **Tối đa:** Không giới hạn (nhưng > 100 có thể slow)

### **3. Coverage:**

Đảm bảo examples cover các loại câu hỏi:
- ✅ Câu hỏi về **tên/danh sách**
- ✅ Câu hỏi về **đặc điểm cụ thể**
- ✅ Câu hỏi về **so sánh**
- ✅ Câu hỏi về **giải thích**

### **4. Consistency:**

Tất cả examples nên có:
- ✅ Cùng style (formal/informal)
- ✅ Cùng độ dài tương đối
- ✅ Cùng format (bullet points, prose, etc.)

---

## 🧪 Testing

### **Test similarity search:**

```bash
python3 load_qa_examples.py
```

Khi được hỏi, nhập câu hỏi test:
```
Enter a test question: Khả năng chống nước của ABC?

Top 3 similar questions:
1. Similarity: 85%
   Q: Khả năng chống cháy của XYZ?
   A: XYZ có khả năng chống cháy...
```

### **Test chatbot:**

```bash
# Start server
python3 app_with_examples.py

# Test via API
curl -X POST http://localhost:5004/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test question"}'
```

---

## 🔧 Troubleshooting

### **Lỗi: "No .xlsx files found"**

```bash
# Kiểm tra file có trong thư mục không
ls -la *.xlsx
ls -la documents/*.xlsx

# Nếu không có, copy file vào
cp /path/to/sample_questions.xlsx .
```

### **Lỗi: "pandas not installed"**

```bash
pip install pandas openpyxl
```

### **Lỗi: "Cannot auto-detect Q&A columns"**

Script sẽ hỏi bạn chọn cột:
```
Please specify column names:
  Question column name [Column1]: Câu hỏi
  Answer column name [Column2]: Câu trả lời
```

### **Examples không load:**

```bash
# Kiểm tra qa_examples.json có được tạo không
ls -la qa_examples.json

# Nếu có, check nội dung
cat qa_examples.json | head -20

# Reload trong app
curl -X POST http://localhost:5004/api/reload-examples
```

---

## 📈 Kết quả mong đợi

### **Before (không có examples):**

- Answer length: 150-250 từ
- Format: Không nhất quán
- Extra info: 50% cases
- Style: Varies

### **After (với examples):**

- Answer length: 20-50 từ (học từ examples)
- Format: Nhất quán với examples
- Extra info: < 10% cases
- Style: Consistent với examples

---

## 🚀 Next Steps

1. ✅ **Tạo file sample_questions.xlsx** với 20-30 Q&A mẫu
2. ✅ **Run:** `python3 load_qa_examples.py`
3. ✅ **Start:** `python3 app_with_examples.py`
4. ✅ **Test** với real questions
5. ✅ **Iterate:** Thêm/sửa examples dựa trên feedback
6. ✅ **Monitor:** Xem examples nào được dùng nhiều nhất

---

## 💡 Advanced: Hybrid Approach

Kết hợp **Few-Shot Learning** + **FileSearch Store**:

```bash
# 1. Upload xlsx vào FileSearch (để bot biết examples)
python3 upload_document.py
# → Chọn file sample_questions.xlsx

# 2. Dùng app_with_examples.py (để few-shot learning)
python3 app_with_examples.py
```

**Lợi ích:**
- FileSearch: Bot có thể retrieve examples trực tiếp
- Few-Shot: Bot học format từ similar examples
- Best of both worlds!

---

**Ready to test!** 🎯

Upload file `sample_questions.xlsx` của bạn và chạy `python3 load_qa_examples.py` để bắt đầu!
