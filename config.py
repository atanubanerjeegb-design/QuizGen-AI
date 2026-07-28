import os
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environmental variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    """Application configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-1234567890')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "database.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB limit (unlimited)
    
    # Quiz Configurations
    QUIZ_QUESTION_OPTIONS = [5, 10, 15, 20, 25]
    DEFAULT_QUESTION_COUNT = 15
    
    # Google Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    
    # OCR Settings
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', '')
