# -*- coding: utf-8 -*-
"""
Script to upload PDF documents to Gemini FileSearch Store
Run this script once to index your documents before starting the chatbot
"""
import os
import sys
import io
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Fix encoding for Vietnamese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

def create_file_search_store(client, store_name="Silkroad Documents Store"):
    """Create a new FileSearch store"""
    print(f"Creating FileSearch store: {store_name}...")

    file_search_store = client.file_search_stores.create(
        config={'display_name': store_name}
    )

    print(f"✓ Store created successfully!")
    print(f"  Store ID: {file_search_store.name}")
    return file_search_store

def upload_document_to_store(client, file_search_store, file_path):
    """Upload a document to the FileSearch store"""
    file_name = Path(file_path).name

    # Safe print for Vietnamese filename
    try:
        print(f"\nUploading document: {file_name}...")
    except UnicodeEncodeError:
        print(f"\nUploading document: {file_name.encode('utf-8', errors='replace').decode('utf-8')}...")

    try:
        # Upload file directly to FileSearch store (combines upload + import)
        # Use UTF-8 encoding for display name
        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(file_path),
            file_search_store_name=file_search_store.name,
            config={'display_name': file_name}
        )

        print(f"  Upload initiated. Waiting for indexing to complete...")

        # Wait for operation to complete
        # Pass the operation object itself, not the name string
        while not operation.done:
            time.sleep(2)
            operation = client.operations.get(operation)
            print("  .", end="", flush=True)

        print("\n✓ Document uploaded and indexed successfully!")
        return operation

    except Exception as e:
        print(f"\n✗ Error uploading document: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def list_existing_stores(client):
    """List all existing FileSearch stores"""
    print("\nExisting FileSearch stores:")
    try:
        stores = list(client.file_search_stores.list())

        if not stores:
            print("  No stores found.")
            return None

        for idx, store in enumerate(stores, 1):
            print(f"  {idx}. {store.display_name or 'Unnamed'}")
            print(f"     ID: {store.name}")

        return stores
    except Exception as e:
        print(f"  Error listing stores: {str(e)}")
        return None

def update_env_file(store_id):
    """Update .env file with the FileSearch store ID"""
    env_path = Path('.env')

    if env_path.exists():
        # Read existing content
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update or add FILE_SEARCH_STORE_ID
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('FILE_SEARCH_STORE_ID='):
                lines[i] = f'FILE_SEARCH_STORE_ID={store_id}\n'
                updated = True
                break

        if not updated:
            lines.append(f'\nFILE_SEARCH_STORE_ID={store_id}\n')

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)
    else:
        # Create new .env file
        with open(env_path, 'w') as f:
            f.write(f'GEMINI_API_KEY={os.getenv("GEMINI_API_KEY", "")}\n')
            f.write(f'FILE_SEARCH_STORE_ID={store_id}\n')

    print(f"\n✓ Updated .env file with store ID")

def main():
    """Main function to upload documents"""
    print("=" * 60)
    print("Silkroad RAG - Document Upload Tool")
    print("=" * 60)

    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("\n✗ Error: GEMINI_API_KEY not found!")
        print("  Please set your API key in .env file")
        print("  Get your API key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    # Initialize Gemini client
    print("\nInitializing Gemini client...")
    try:
        client = genai.Client(api_key=api_key)
        print("✓ Client initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing client: {str(e)}")
        sys.exit(1)

    # Check if documents folder exists
    docs_folder = Path('documents')
    if not docs_folder.exists():
        docs_folder.mkdir()
        print(f"\n✓ Created 'documents' folder")
        print(f"  Please place your PDF files in the 'documents' folder and run this script again")
        sys.exit(0)

    # Find PDF files
    pdf_files = list(docs_folder.glob('*.pdf'))

    if not pdf_files:
        print(f"\n✗ No PDF files found in 'documents' folder")
        print(f"  Please add your PDF files and run this script again")
        sys.exit(1)

    print(f"\nFound {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        file_size = pdf.stat().st_size / (1024 * 1024)  # Convert to MB
        try:
            print(f"  - {pdf.name} ({file_size:.2f} MB)")
        except UnicodeEncodeError:
            # Fallback for encoding issues
            print(f"  - {pdf.name.encode('utf-8', errors='replace').decode('utf-8')} ({file_size:.2f} MB)")

    # Ask user to create new store or use existing
    print("\n" + "=" * 60)
    print("Choose an option:")
    print("  1. Create new FileSearch store")
    print("  2. Use existing FileSearch store")
    print("=" * 60)

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == '1':
        # Create new store
        store_name = input("Enter store name (or press Enter for default): ").strip()
        if not store_name:
            store_name = "Silkroad Documents Store"

        file_search_store = create_file_search_store(client, store_name)

    elif choice == '2':
        # List existing stores
        stores = list_existing_stores(client)
        if not stores:
            print("\nCreating new store instead...")
            file_search_store = create_file_search_store(client, "Silkroad Documents Store")
        else:
            store_idx = int(input("\nEnter store number to use: ").strip()) - 1
            if 0 <= store_idx < len(stores):
                file_search_store = stores[store_idx]
                print(f"\n✓ Using store: {file_search_store.display_name}")
            else:
                print("Invalid store number. Exiting.")
                sys.exit(1)

    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    # Upload all PDF files
    print("\n" + "=" * 60)
    print("Uploading documents...")
    print("=" * 60)

    success_count = 0
    for pdf_file in pdf_files:
        result = upload_document_to_store(client, file_search_store, str(pdf_file))
        if result:
            success_count += 1

    # Update .env file
    update_env_file(file_search_store.name)

    # Summary
    print("\n" + "=" * 60)
    print("Upload Summary")
    print("=" * 60)
    print(f"  Total files: {len(pdf_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(pdf_files) - success_count}")
    print(f"\n  Store ID: {file_search_store.name}")
    print("\n✓ Setup complete! You can now run the chatbot with:")
    print("  python app.py")
    print("=" * 60)

if __name__ == '__main__':
    main()
