from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .routes import health, auth, transaction, file_upload
from .core.logging import logger
from .core.database import Base, engine, test_db_connection, get_db
from dotenv import load_dotenv
import os
import sqlalchemy.exc
from app.routes.user_detail import router as user_detail_router

# Load environment variables
load_dotenv()
#
# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Himalai Expense Analysis",
    version="1.0.0"
)

# Alternative solution for main.py
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attempt to create database tables with better error handling
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except sqlalchemy.exc.OperationalError as e:
    logger.error(f"Failed to create database tables: {str(e)}")
    logger.error("Please check your database connection settings")
except Exception as e:
    logger.error(f"Unexpected error creating database tables: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Welcome to Himalai Expense Analysis API", "docs_url": "/docs"}

# Add a database health check endpoint
@app.get("/db-health")
async def db_health():
    success, message = test_db_connection()
    if success:
        return {"status": "ok", "message": message}
    else:
        return {"status": "error", "message": message}

# Include routers with API prefix
app.include_router(auth.router, prefix=settings.API_V1_STR)
# app.include_router(auth.router)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(transaction.router, prefix=settings.API_V1_STR)
app.include_router(
    user_detail_router,
    prefix="/api/users",  # This sets the base path for all routes in user_detail.py
    tags=["Users"]        # This organizes routes in the auto-generated docs
)
app.include_router(
    file_upload.router,
    prefix=settings.API_V1_STR  # Check what this value is
)
# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Himalai Expense Analysis API")
    
    # Test database connection
    success, message = test_db_connection()
    if success:
        logger.info(message)
    else:
        logger.error(message)
        logger.error("Application started with database connection issues")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Himalai Expense Analysis API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)