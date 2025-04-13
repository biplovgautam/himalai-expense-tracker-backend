import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Settings:
    # App Settings
    APP_NAME: str = os.getenv("APP_NAME", "Himalai Expense Analysis")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # API Settings
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-replace-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # CORS Settings
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8000,http://localhost:5173"
    ).split(",")
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost/himalai_db"
    )
    DB_CONNECT_ARGS: Dict[str, str] = {
        "sslmode": os.getenv("DB_SSLMODE", "prefer")
    }
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    # Groq Settings (using working model)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")  # Confirmed working model
    GROQ_API_ENDPOINT: str = os.getenv("GROQ_API_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")

    # File Settings
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./app/output")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")

    def __init__(self):
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required")
        
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

settings = Settings()