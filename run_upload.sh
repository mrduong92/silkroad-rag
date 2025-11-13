#!/bin/bash
# Wrapper script to run upload_document.py with proper UTF-8 encoding

# Set UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

echo "Running upload script with UTF-8 encoding..."
echo "LANG=$LANG"
echo "LC_ALL=$LC_ALL"
echo "PYTHONIOENCODING=$PYTHONIOENCODING"
echo ""

# Run the upload script
python3 upload_document.py
