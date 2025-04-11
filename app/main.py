from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .routes import health, auth
from .core.logging import logger
from .core.database import Base, engine
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

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

# Create database tables (comment out if using Alembic)
Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "Welcome to Himalai Expense Analysis API", "docs_url": "/docs"}

# Include routers with API prefix
app.include_router(auth.router, prefix=settings.API_V1_STR)  # Original inclusion
app.include_router(auth.router)  # Add this line to include auth router without prefix
app.include_router(health.router, prefix=settings.API_V1_STR)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Himalai Expense Analysis API")  # Updated from "Tripo API"

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Himalai Expense Analysis API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)