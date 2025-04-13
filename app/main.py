import os
import sqlalchemy.exc

# 1. FIRST load environment variables before anything else
from dotenv import load_dotenv
load_dotenv()

# Now import everything else
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import Base, engine, test_db_connection

# Import routers
from app.routes import health, auth, transaction, file_upload
from app.routes.user_detail import router as user_detail_router


# 2. Validate critical configurations immediately
def validate_config():
    required_vars = {
        "GROQ_API_KEY": "Groq API key",
        "DATABASE_URL": "Database connection URL",
        "SECRET_KEY": "JWT secret key"
    }
    
    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var, "").strip():  # Check for empty/whitespace values
            missing.append(f"{desc} ({var})")
    
    if missing:
        error_msg = f"Missing required configurations: {', '.join(missing)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

validate_config()

# 3. Now initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Himalai Expense Analysis",
    version="1.0.0"
)

# CORS configuration
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
origins = [origin.strip() for origin in origins if origin.strip()]  # Clean empty values

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization with better error handling
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except sqlalchemy.exc.OperationalError as e:
    logger.error(f"Database connection failed: {str(e)}")
    logger.error("Please check your DATABASE_URL in .env")
except Exception as e:
    logger.error(f"Unexpected database error: {str(e)}")

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Himalai Expense Analysis API", "docs_url": "/docs"}

@app.get("/db-health")
async def db_health():
    success, message = test_db_connection()
    return {"status": "ok" if success else "error", "message": message}

# Include all routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(transaction.router, prefix=settings.API_V1_STR)
app.include_router(file_upload.router, prefix=settings.API_V1_STR)
app.include_router(
    user_detail_router,
    prefix="/api/users",
    tags=["Users"]
)


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} (Environment: {settings.ENVIRONMENT})")
    logger.debug(f"Allowed origins: {origins}")
    logger.debug(f"Groq model: {settings.GROQ_MODEL}")
    
    success, message = test_db_connection()
    if success:
        logger.info("Database connection successful")
    else:
        logger.error(f"Database connection failed: {message}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )