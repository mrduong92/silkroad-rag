# -*- coding: utf-8 -*-
"""
Script to inspect FileSearch store and list uploaded files
"""
import os
import sys
import io
from google import genai
from dotenv import load_dotenv

# Fix encoding for Vietnamese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

def format_bytes(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def inspect_file_search_stores(client):
    """Inspect all FileSearch stores and their contents"""
    print("=" * 80)
    print("FileSearch Store Inspector")
    print("=" * 80)

    try:
        stores = list(client.file_search_stores.list())

        if not stores:
            print("\n⚠ No FileSearch stores found")
            return

        print(f"\nFound {len(stores)} FileSearch store(s):\n")

        for idx, store in enumerate(stores, 1):
            print(f"\n{'─' * 80}")
            print(f"Store #{idx}")
            print(f"{'─' * 80}")
            print(f"Name: {store.display_name or 'Unnamed'}")
            print(f"ID: {store.name}")

            # Get store details
            if hasattr(store, 'create_time'):
                print(f"Created: {store.create_time}")
            if hasattr(store, 'update_time'):
                print(f"Updated: {store.update_time}")

            # Try to list files in the store
            print(f"\nFiles in this store:")
            try:
                # List files associated with this store
                # Note: FileSearch doesn't expose individual files directly
                # We can only see files via the Files API if they were uploaded separately
                print("  (FileSearch stores embeddings internally - individual files not directly listable)")
                print("  Files are chunked and embedded automatically by Gemini")

            except Exception as e:
                print(f"  Error listing files: {e}")

    except Exception as e:
        print(f"\n✗ Error inspecting stores: {e}")
        import traceback
        traceback.print_exc()

def inspect_uploaded_files(client):
    """Inspect files uploaded via Files API"""
    print(f"\n{'=' * 80}")
    print("Uploaded Files (via Files API)")
    print(f"{'=' * 80}\n")

    try:
        files = list(client.files.list())

        if not files:
            print("⚠ No files found via Files API")
            print("(Files uploaded via upload_to_file_search_store may not appear here)")
            return

        print(f"Found {len(files)} file(s):\n")

        for idx, file in enumerate(files, 1):
            print(f"{idx}. {file.display_name or file.name}")
            print(f"   Name: {file.name}")
            if hasattr(file, 'size_bytes'):
                print(f"   Size: {format_bytes(file.size_bytes)}")
            if hasattr(file, 'mime_type'):
                print(f"   Type: {file.mime_type}")
            if hasattr(file, 'create_time'):
                print(f"   Created: {file.create_time}")
            if hasattr(file, 'uri'):
                print(f"   URI: {file.uri}")
            print()

    except Exception as e:
        print(f"✗ Error listing files: {e}")
        import traceback
        traceback.print_exc()

def explain_embeddings():
    """Explain how embeddings work in FileSearch"""
    print(f"\n{'=' * 80}")
    print("How Embeddings Work in Gemini FileSearch")
    print(f"{'=' * 80}\n")

    explanation = """
📚 EMBEDDING STORAGE ARCHITECTURE:

1. WHERE ARE EMBEDDINGS STORED?
   ✓ Embeddings are stored on Google's cloud infrastructure
   ✓ Managed by Gemini API backend (you don't manage storage directly)
   ✓ Associated with your FileSearch Store ID
   ✓ Persists until you explicitly delete the store

2. WHAT HAPPENS WHEN YOU UPLOAD A FILE?

   Your PDF → [Gemini FileSearch Service]
                      ↓
        ┌─────────────┴─────────────┐
        │                           │
   [Text Extraction]        [Chunking]
        │                           │
        └─────────────┬─────────────┘
                      ↓
            [Embedding Generation]
                      ↓
        Each chunk → 1024-dim vector
                      ↓
          [Store in Vector Index]
                      ↓
            FileSearch Store
         (Cloud-based storage)

3. CHUNKING PROCESS:
   - Your 9.97 MB PDF is split into chunks (~800 tokens each)
   - Each chunk = 1-2 paragraphs of text
   - Overlap between chunks (100 tokens) for context
   - Example: 100-page PDF → ~500-1000 chunks

4. EMBEDDING VECTORS:
   - Each chunk → 1024-dimensional float vector
   - Example vector: [0.023, -0.145, 0.089, ..., 0.234]
   - Captures semantic meaning of the text
   - Similar content = similar vectors (cosine similarity)

5. VECTOR INDEX:
   - All chunk embeddings stored in searchable index
   - Uses approximate nearest neighbor search (ANN)
   - Fast semantic search: O(log n) instead of O(n)

6. CAN YOU SEE RAW EMBEDDINGS?
   ✗ No direct API to download raw embedding vectors
   ✗ Embeddings are internal to Gemini's infrastructure
   ✓ You can see: Store metadata, file list, query results
   ✓ You can use: Semantic search, retrieval, citations

7. STORAGE COSTS:
   FREE TIER:
   - 1 GB storage (embeddings + original files)
   - Your 9.97 MB PDF ≈ 0.01 GB (well within limit!)
   - Embeddings size ≈ 2-3x original file size

   PAID TIER:
   - Tier 1: 10 GB ($0/month, just storage)
   - Tier 2: 100 GB
   - Tier 3: 1 TB

8. DATA PERSISTENCE:
   ✓ Embeddings persist indefinitely (until you delete)
   ✓ Survive across API sessions
   ✓ No need to re-upload unless file changes
   ✓ Store ID in .env allows reuse

9. PRIVACY & SECURITY:
   ✓ Your embeddings are private to your API key
   ✓ Other users cannot access your FileSearch stores
   ✓ Google's standard cloud security applies
   ✓ Data encrypted at rest and in transit

10. WHEN TO RE-UPLOAD:
    - File content changes (updated document)
    - Want different chunking parameters
    - Moving to new FileSearch store
    - Accidentally deleted store
"""
    print(explanation)

def query_example():
    """Show example of how embeddings are used in queries"""
    print(f"\n{'=' * 80}")
    print("How Embeddings Are Used in Queries")
    print(f"{'=' * 80}\n")

    example = """
EXAMPLE QUERY FLOW:

User asks: "Thông tư 17 có hiệu lực khi nào?"

STEP 1: Query Embedding
   Query text → Gemini embedding model
   → Vector: [0.123, -0.456, 0.789, ..., 0.321]

STEP 2: Semantic Search
   Compare query vector with all chunk vectors
   → Find top K most similar chunks (K ≈ 3-5)

   Similarity calculation:
   cosine_similarity(query_vec, chunk_vec)

   Results:
   ✓ Chunk #42: similarity = 0.92 (highest!)
   ✓ Chunk #43: similarity = 0.88
   ✓ Chunk #15: similarity = 0.85

STEP 3: Retrieve Chunks
   Chunk #42: "Thông tư này có hiệu lực từ ngày..."
   Chunk #43: "Thay thế Thông tư 62/2020/TT-BTC..."
   Chunk #15: "Quy định về thời gian áp dụng..."

STEP 4: Generate Answer
   Gemini LLM receives:
   - Original query
   - Top 3 relevant chunks
   - System prompt

   → Generates answer:
   "Thông tư 17/2024/TT-BTC có hiệu lực từ ngày 01/05/2024..."

STEP 5: Citations
   Response includes metadata:
   - Source chunks
   - Document references
   - Confidence scores

WHY SEMANTIC SEARCH IS POWERFUL:

Traditional keyword search:
   Query: "có hiệu lực khi nào"
   → Only matches exact words
   → Misses: "bắt đầu áp dụng", "thời điểm hiệu lực"

Semantic search (embeddings):
   Query: "có hiệu lực khi nào"
   → Understands meaning
   → Matches: "hiệu lực", "áp dụng", "thời điểm", "ngày thi hành"
   → Language-agnostic (Vietnamese, English both work!)
"""
    print(example)

def main():
    """Main function"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("✗ Error: GEMINI_API_KEY not found in .env")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Inspect stores
    inspect_file_search_stores(client)

    # Inspect files
    inspect_uploaded_files(client)

    # Explain embeddings
    explain_embeddings()

    # Query example
    query_example()

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print("""
Key Takeaways:
1. Embeddings stored in Google cloud (not downloadable as raw vectors)
2. You can see: Store metadata, file lists, query results
3. Semantic search uses cosine similarity between vectors
4. Free tier: 1 GB storage (plenty for most use cases)
5. Embeddings persist until you delete the store
6. Private to your API key - secure and isolated
    """)
    print("=" * 80)

if __name__ == '__main__':
    main()
