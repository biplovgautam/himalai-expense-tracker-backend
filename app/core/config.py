import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Basic settings
    APP_NAME: str = "THimalai Expense Analysis API"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS settings
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# Create settings instance
settings = Settings()

print(f"ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
print(f"ENVIRONMENT: {settings.ENVIRONMENT}")