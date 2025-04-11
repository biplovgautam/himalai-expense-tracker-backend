import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Get database URL with proper fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./himalai.db")

# Configure engine based on database type
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    # Only add SSL mode for PostgreSQL if not local development
    if not "localhost" in DATABASE_URL and not "127.0.0.1" in DATABASE_URL:
        connect_args = {"sslmode": "require"}

# Create engine with appropriate connect_args
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_db_connection():
    """Test database connection and return status."""
    try:
        # Create a test connection
        with engine.connect() as connection:
            # Use SQLAlchemy's text construct for raw SQL
            result = connection.execute(text("SELECT 1")).scalar()
            
            # Check if we got the expected result
            if result == 1:
                return {"status": "connected", "message": "Database connection successful"}
            else:
                return {"status": "error", "message": "Unexpected result from database"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}