# -*- coding: utf-8 -*-
"""
Upload sample_questions.xlsx to EXISTING FileSearch store
No need to create new store - add to current store!
"""
import os
import sys
import io
import time
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

def upload_to_existing_store(client, file_path, store_id):
    """
    Upload file to EXISTING FileSearch store
    """
    file_name = Path(file_path).name

    try:
        print(f"\nUploading to existing store...")
        print(f"  File: {file_name}")
        print(f"  Store: {store_id}")

        # Upload file to existing store
        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(file_path),
            file_search_store_name=store_id,
            config={'display_name': file_name}
        )

        print(f"\n  Upload initiated. Waiting for indexing...")

        # Wait for completion
        while not operation.done:
            time.sleep(2)
            operation = client.operations.get(operation)
            print("  .", end="", flush=True)

        print("\n\n✓ File uploaded and indexed successfully!")
        return True

    except Exception as e:
        print(f"\n✗ Error uploading: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def list_files_in_store(client, store_id):
    """
    List all files in the store
    Note: FileSearch doesn't expose individual files directly,
    but we can check if upload was successful
    """
    try:
        print(f"\nStore Information:")
        print(f"  Store ID: {store_id}")
        print(f"  Files are indexed and searchable")
        print(f"  (Individual files not directly listable via FileSearch API)")
        return True
    except Exception as e:
        print(f"Error checking store: {e}")
        return False

def main():
    """Main function"""
    print("=" * 80)
    print("Upload Q&A Examples to Existing FileSearch Store")
    print("=" * 80)

    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("\n✗ Error: GEMINI_API_KEY not found!")
        sys.exit(1)

    # Check Store ID
    store_id = os.getenv('FILE_SEARCH_STORE_ID')
    if not store_id:
        print("\n✗ Error: FILE_SEARCH_STORE_ID not found!")
        print("  Run upload_document.py first to create a store")
        sys.exit(1)

    print(f"\n✓ Using existing store: {store_id}")

    # Initialize client
    print("\nInitializing Gemini client...")
    try:
        client = genai.Client(api_key=api_key)
        print("✓ Client initialized")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)

    # Find xlsx files
    xlsx_files = list(Path('.').glob('*.xlsx')) + list(Path('documents').glob('*.xlsx'))

    if not xlsx_files:
        print("\n✗ No .xlsx files found")
        print("  Please add sample_questions.xlsx to the project folder")
        sys.exit(1)

    print(f"\nFound {len(xlsx_files)} Excel file(s):")
    for i, f in enumerate(xlsx_files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {i}. {f.name} ({size_mb:.2f} MB)")

    # Select file
    if len(xlsx_files) == 1:
        selected_file = xlsx_files[0]
        print(f"\n✓ Auto-selected: {selected_file.name}")
    else:
        choice = int(input("\nSelect file number to upload: ").strip()) - 1
        if 0 <= choice < len(xlsx_files):
            selected_file = xlsx_files[choice]
        else:
            print("Invalid choice")
            sys.exit(1)

    # Confirm
    print("\n" + "=" * 80)
    print("Upload Summary")
    print("=" * 80)
    print(f"  File: {selected_file.name}")
    print(f"  Store: {store_id}")
    print(f"  Action: Add to EXISTING store (not creating new store)")
    print("=" * 80)

    confirm = input("\nProceed with upload? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("Upload cancelled")
        sys.exit(0)

    # Upload
    print("\n" + "=" * 80)
    print("Uploading...")
    print("=" * 80)

    success = upload_to_existing_store(client, selected_file, store_id)

    if success:
        print("\n" + "=" * 80)
        print("✓ SUCCESS")
        print("=" * 80)
        print(f"\n  {selected_file.name} has been added to your FileSearch store!")
        print(f"\n  Your store now contains:")
        print(f"    - nd11.pdf (main document)")
        print(f"    - {selected_file.name} (Q&A examples)")
        print(f"\n  When querying, bot will search BOTH files")
        print(f"\n  No need to change FILE_SEARCH_STORE_ID in .env")
        print(f"  (Already using: {store_id})")

        print("\n" + "=" * 80)
        print("Next Steps")
        print("=" * 80)
        print("\n  Option 1: Use standard app (retrieves from both files)")
        print("    python3 app.py")
        print("\n  Option 2: Use app with few-shot learning")
        print("    python3 load_qa_examples.py  # Extract examples from xlsx")
        print("    python3 app_with_examples.py  # Use few-shot + FileSearch")
        print("\n  Option 3: Hybrid (RECOMMENDED)")
        print("    - xlsx in FileSearch → Bot can retrieve examples")
        print("    - Few-shot learning → Bot learns format from examples")
        print("    → Best of both worlds!")
        print("\n" + "=" * 80)

    else:
        print("\n✗ Upload failed")
        print("  Check error messages above")

if __name__ == '__main__':
    main()
