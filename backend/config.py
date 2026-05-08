"""
SkinSense Configuration — All settings loaded from environment variables.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """Application configuration loaded from environment variables."""

    # --- Security ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-change-me-in-production')

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'frontend', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'webp'}

    # --- ML Models ---
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'backend', 'ml_models', 'skin_model.pkl')

    # --- Gemini API ---
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

    # --- Tesseract OCR ---
    # On Render/Linux: tesseract is installed via apt and available in PATH
    # On Windows dev: set TESSERACT_CMD env var or it uses default path
    TESSERACT_CMD = os.environ.get(
        'TESSERACT_CMD',
        'tesseract'  # Default: assumes tesseract is in PATH (Linux/Mac)
    )
