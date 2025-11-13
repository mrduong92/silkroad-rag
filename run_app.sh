#!/bin/bash
# Wrapper script to run app.py with proper UTF-8 encoding

# Set UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

echo "Starting chatbot with UTF-8 encoding..."
echo ""

# Run the Flask app
python3 app.py
