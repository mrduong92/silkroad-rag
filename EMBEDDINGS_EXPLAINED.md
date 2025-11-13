# Embeddings trong Gemini FileSearch - Giải thích chi tiết

## 🗄️ Embeddings được lưu ở đâu?

### Trả lời ngắn gọn:
**Embeddings được lưu trên Google Cloud infrastructure**, được quản lý bởi Gemini API. Bạn **KHÔNG thể tải về raw vectors**, nhưng có thể sử dụng chúng thông qua API.

### Chi tiết:

```
Your API Key
    ↓
FileSearch Store ID: fileSearchStores/kbnn-je4ipcju1cdi
    ↓
[Google Cloud Infrastructure]
    ├── Original PDF (9.97 MB)
    ├── Extracted text chunks (~500-1000 chunks)
    ├── Embedding vectors (1024-dim × number of chunks)
    └── Vector search index (ANN index)
```

## 📊 Kiến trúc lưu trữ

### 1. Upload & Processing Pipeline

```
PDF Document (9.97 MB)
    ↓
[Gemini FileSearch Service]
    ↓
┌───────────────────────────────┐
│  TEXT EXTRACTION              │
│  - Parse PDF                  │
│  - Extract text content       │
│  - Preserve structure         │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│  CHUNKING                     │
│  - Split into ~800 token chunks│
│  - 100 token overlap          │
│  - Preserve context           │
│  Result: ~500-1000 chunks     │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│  EMBEDDING GENERATION         │
│  Each chunk → 1024-dim vector │
│  Model: text-embedding-004    │
│  [0.023, -0.145, ..., 0.234] │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│  VECTOR INDEX                 │
│  - Build ANN index            │
│  - Enable fast search         │
│  - Store on Google Cloud      │
└───────────────────────────────┘
```

### 2. Storage Structure

```
FileSearch Store (kbnn)
├── Metadata
│   ├── Store ID: fileSearchStores/kbnn-je4ipcju1cdi
│   ├── Display Name: "kbnn"
│   ├── Created: 2024-11-12
│   └── API Key: (your key)
│
├── Documents
│   └── TT 17-2024-TT-BTC.pdf
│       ├── Original file (9.97 MB)
│       ├── MIME type: application/pdf
│       └── Upload timestamp
│
├── Chunks (Not directly accessible)
│   ├── Chunk 0: "Thông tư 17/2024/TT-BTC..."
│   ├── Chunk 1: "Về việc hướng dẫn..."
│   ├── Chunk 2: "Điều 1. Phạm vi điều chỉnh..."
│   └── ... (~500-1000 chunks total)
│
└── Embeddings (Not directly accessible)
    ├── Vector 0: [0.023, -0.145, 0.089, ..., 0.234]
    ├── Vector 1: [0.156, -0.023, 0.145, ..., 0.089]
    ├── Vector 2: [-0.089, 0.234, -0.156, ..., 0.023]
    └── ... (1024 dimensions × ~500-1000 vectors)
```

## 🔍 Có thể xem được gì?

### ✅ CÓ THỂ XEM:

1. **FileSearch Stores**
   ```python
   stores = list(client.file_search_stores.list())
   for store in stores:
       print(f"Name: {store.display_name}")
       print(f"ID: {store.name}")
   ```

2. **Store Metadata**
   - Store ID
   - Display name
   - Creation time
   - Update time

3. **Query Results**
   - Retrieved chunks (text content)
   - Citations/sources
   - Similarity scores (implicit)

4. **Grounding Metadata**
   ```python
   response.candidates[0].grounding_metadata.grounding_chunks
   # → List of chunks that were used to generate answer
   ```

### ❌ KHÔNG THỂ XEM:

1. **Raw embedding vectors** (không có API)
2. **Individual chunks** trước khi query
3. **Vector index structure** (nội bộ)
4. **Similarity scores** trực tiếp
5. **Chunking boundaries** chi tiết

## 🔧 Cách kiểm tra Store của bạn

### Chạy inspection tool:

```bash
python3 inspect_store.py
```

Output mẫu:
```
================================================================================
FileSearch Store Inspector
================================================================================

Found 2 FileSearch store(s):

────────────────────────────────────────────────────────────────────────────────
Store #1
────────────────────────────────────────────────────────────────────────────────
Name: Silkroad Documents Store
ID: fileSearchStores/silkroad-documents-store-9plqmmz7du9h
Created: 2024-11-12T10:30:00Z

Files in this store:
  (FileSearch stores embeddings internally - individual files not directly listable)
  Files are chunked and embedded automatically by Gemini

────────────────────────────────────────────────────────────────────────────────
Store #2
────────────────────────────────────────────────────────────────────────────────
Name: kbnn
ID: fileSearchStores/kbnn-je4ipcju1cdi
Created: 2024-11-12T11:15:00Z

Files in this store:
  (FileSearch stores embeddings internally - individual files not directly listable)
  Files are chunked and embedded automatically by Gemini
```

## 🧮 Embedding Vector Details

### Kích thước và cấu trúc:

```python
# Mỗi chunk text được convert thành:
embedding_vector = [
    0.0234,   # Dimension 0
    -0.1456,  # Dimension 1
    0.0892,   # Dimension 2
    # ... 1021 dimensions more
    0.2341    # Dimension 1023
]

# Vector properties:
- Type: float32
- Dimensions: 1024
- Range: [-1.0, 1.0] typically
- Normalized: Yes (unit vector)
```

### Ước tính dung lượng:

```
File PDF của bạn: 9.97 MB

Ước tính processing:
├── Text extraction: ~5 MB (text only)
├── Chunks: ~800-1000 chunks
├── Embeddings: 1024 dims × 4 bytes × 1000 chunks = ~4 MB
└── Index overhead: ~2-3 MB

Total storage: ~15-20 MB (cho 1 file 10 MB)

Free tier limit: 1 GB (đủ cho ~50-70 files tương tự)
```

## 🔎 Semantic Search hoạt động như thế nào?

### Query Flow:

```
1. User Query: "Thông tư 17 có hiệu lực khi nào?"
   ↓
2. Query Embedding
   Text → Embedding Model → Query Vector [1024 dims]
   ↓
3. Vector Search
   Compare query vector với tất cả chunk vectors
   Method: Cosine Similarity

   cosine_similarity = dot(A, B) / (norm(A) × norm(B))

   Example:
   - Chunk #42: similarity = 0.92 ✓ (top match!)
   - Chunk #43: similarity = 0.88 ✓
   - Chunk #15: similarity = 0.85 ✓
   - Chunk #89: similarity = 0.45 (not relevant)
   ↓
4. Retrieve Top K Chunks (K = 3-5)
   Chunk #42: "Thông tư này có hiệu lực từ ngày 01/05/2024..."
   Chunk #43: "Thay thế Thông tư 62/2020/TT-BTC..."
   Chunk #15: "Quy định về thời gian áp dụng..."
   ↓
5. LLM Generation
   Input: Query + Retrieved chunks + System prompt
   Output: "Thông tư 17/2024/TT-BTC có hiệu lực từ ngày 01/05/2024
           và thay thế Thông tư 62/2020/TT-BTC."
```

### Visualization:

```
Vector Space (3D projection for illustration):

                    Query Vector
                         ↓
                         •
                        /|\
                       / | \
                      /  |  \
            0.92 →   •   |   •  ← 0.45 (low similarity)
                    /    |    \
          Chunk #42     •      Chunk #89
         (relevant)     |     (not relevant)
                        |
                        • ← Chunk #15 (0.85)
```

## 💾 Data Persistence

### Lưu trữ lâu dài:

```
✓ Embeddings persist indefinitely (không tự động xóa)
✓ Survive across API sessions
✓ No need to re-upload unless:
  - File content changes
  - Want different chunking parameters
  - Accidentally deleted store
  - Moving to new account/API key
```

### Xóa embeddings:

```python
# Delete entire store (xóa tất cả embeddings và files)
client.file_search_stores.delete(
    name='fileSearchStores/kbnn-je4ipcju1cdi',
    force=True  # Force delete even if not empty
)
```

⚠️ **Lưu ý:** Xóa store = xóa vĩnh viễn tất cả embeddings!

## 💰 Chi phí lưu trữ

### Free Tier:
```
✓ Storage: 1 GB free
✓ Indexing: Free (during free tier)
✓ Query: Free (trong rate limits)

Your current usage:
- 1 PDF (9.97 MB)
- Embeddings (~10-15 MB)
- Total: ~20-25 MB
- Remaining: ~975 MB (97.5% free!)
```

### Paid Tier (nếu cần):
```
Tier 1: 10 GB - $0/month (just pay for usage)
Tier 2: 100 GB - Contact sales
Tier 3: 1 TB - Contact sales

Usage charges:
- Indexing: $0.15 per 1M tokens
- Queries: Standard context token pricing
```

## 🔒 Security & Privacy

### Data Protection:

```
✓ Your embeddings are PRIVATE to your API key
✓ Other users CANNOT access your FileSearch stores
✓ Data encrypted at rest
✓ Data encrypted in transit (HTTPS/TLS)
✓ Google's standard cloud security applies
✓ Compliance: GDPR, SOC2, ISO 27001
```

### Access Control:

```
Your API Key (AIza...)
    ↓ (only accessible by)
Your FileSearch Stores
    ↓ (contains)
Your Embeddings & Files
```

## 🛠️ Practical Examples

### Example 1: View your stores

```python
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# List all stores
for store in client.file_search_stores.list():
    print(f"Store: {store.display_name}")
    print(f"ID: {store.name}")
    print()
```

### Example 2: Query and see retrieved chunks

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Thông tư 17 có hiệu lực khi nào?",
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=['fileSearchStores/kbnn-je4ipcju1cdi']
                )
            )
        ]
    )
)

# See grounding metadata (which chunks were used)
grounding = response.candidates[0].grounding_metadata
print("Chunks used:")
for chunk in grounding.grounding_chunks:
    print(f"- {chunk}")
```

## 📚 Further Reading

- [Gemini FileSearch Docs](https://ai.google.dev/gemini-api/docs/file-search)
- [Vector Embeddings Explained](https://www.pinecone.io/learn/vector-embeddings/)
- [Semantic Search](https://en.wikipedia.org/wiki/Semantic_search)
- [RAG Architecture](https://www.pinecone.io/learn/retrieval-augmented-generation/)

## 🎯 Summary

**TL;DR:**

1. ❌ Không thể xem raw embedding vectors
2. ✅ Embeddings stored securely on Google Cloud
3. ✅ Access via semantic search API
4. ✅ Private to your API key
5. ✅ 1 GB free storage (plenty!)
6. ✅ Persists indefinitely until deleted
7. ✅ Use `inspect_store.py` to view store metadata

**Để inspect stores của bạn:**
```bash
python3 inspect_store.py
```
