# -*- coding: utf-8 -*-
"""
Configuration file for Silkroad RAG Chatbot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""

    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FILE_SEARCH_STORE_ID = os.getenv('FILE_SEARCH_STORE_ID')

    # Model Configuration
    MODEL_NAME = 'gemini-2.5-flash'  # or 'gemini-2.5-pro' for better quality

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # File Upload Configuration
    DOCUMENTS_FOLDER = 'documents'
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'pdf'}

    # Chatbot Configuration
    MAX_HISTORY_LENGTH = 10
    TEMPERATURE = 0.0  # Fully deterministic responses (0.0 = no randomness)
    MAX_OUTPUT_TOKENS = 1500  # Allow complete answers while staying concise

    # Zalo Message Limits
    ZALO_MAX_MESSAGE_LENGTH = 2000  # Conservative limit for Zalo OA messages (chars)

    @staticmethod
    def validate():
        """Validate required configuration"""
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        if not Config.FILE_SEARCH_STORE_ID:
            raise ValueError("FILE_SEARCH_STORE_ID is not set. Run upload_document.py first.")
