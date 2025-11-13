# -*- coding: utf-8 -*-
"""
Test script to diagnose setup issues
"""
import sys

print("=" * 60)
print("Silkroad RAG - Setup Diagnostic Tool")
print("=" * 60)

# Test 1: Python version
print("\n1. Python Version:")
print(f"   {sys.version}")
print(f"   Executable: {sys.executable}")

# Test 2: Check packages
print("\n2. Checking required packages:")
packages = {
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS',
    'google.genai': 'google-genai',
    'dotenv': 'python-dotenv',
}

for module_name, package_name in packages.items():
    try:
        if module_name == 'google.genai':
            from google import genai
            print(f"   ✓ {package_name}: installed")
            # Try to get version
            try:
                import importlib.metadata
                version = importlib.metadata.version('google-genai')
                print(f"     Version: {version}")
            except:
                print(f"     Version: unknown")
        else:
            __import__(module_name)
            print(f"   ✓ {package_name}: installed")
    except ImportError as e:
        print(f"   ✗ {package_name}: NOT installed")
        print(f"     Error: {e}")

# Test 3: Check .env file
print("\n3. Checking .env file:")
import os
from pathlib import Path

env_path = Path('.env')
if env_path.exists():
    print("   ✓ .env file exists")

    # Load and check variables
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    store_id = os.getenv('FILE_SEARCH_STORE_ID')

    if api_key:
        print(f"   ✓ GEMINI_API_KEY is set (length: {len(api_key)})")
    else:
        print("   ✗ GEMINI_API_KEY is NOT set")

    if store_id:
        print(f"   ✓ FILE_SEARCH_STORE_ID is set")
        print(f"     Value: {store_id}")
    else:
        print("   ⚠ FILE_SEARCH_STORE_ID is NOT set (will be created by upload script)")
else:
    print("   ✗ .env file does NOT exist")
    print("     Run: cp .env.example .env")

# Test 4: Check documents folder
print("\n4. Checking documents folder:")
docs_folder = Path('documents')
if docs_folder.exists():
    pdf_files = list(docs_folder.glob('*.pdf'))
    print(f"   ✓ documents/ folder exists")
    print(f"   Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"     - {pdf.name} ({size_mb:.2f} MB)")
else:
    print("   ✗ documents/ folder does NOT exist")
    print("     Will be created automatically")

# Test 5: Test Gemini API connection
print("\n5. Testing Gemini API connection:")
try:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("   ⚠ Skipping (no API key)")
    else:
        from google import genai
        client = genai.Client(api_key=api_key)
        print("   ✓ Client initialized successfully")

        # Try to list stores
        try:
            stores = list(client.file_search_stores.list())
            print(f"   ✓ API connection working")
            print(f"   Found {len(stores)} existing FileSearch store(s)")
            for store in stores[:3]:  # Show first 3
                print(f"     - {store.display_name or 'Unnamed'}")
                print(f"       ID: {store.name}")
        except Exception as e:
            print(f"   ⚠ Cannot list stores: {e}")

except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("Diagnostic Summary")
print("=" * 60)
print("\nIf all checks pass, you can run:")
print("  python upload_document.py")
print("\nIf there are errors, please:")
print("  1. Install missing packages: pip install -r requirements.txt")
print("  2. Create .env file: cp .env.example .env")
print("  3. Add your GEMINI_API_KEY to .env")
print("  4. Add PDF files to documents/ folder")
print("=" * 60)
