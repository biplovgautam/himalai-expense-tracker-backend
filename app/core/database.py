import time
import sqlalchemy.exc
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings
from ..core.logging import logger

# Create engine with better error handling
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Detect disconnections
        pool_recycle=3600,   # Recycle connections after 1 hour
        connect_args=settings.DB_CONNECT_ARGS  # Get SSL settings from config
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Error creating database engine: {str(e)}")
    # Create a fallback SQLite engine for development if PostgreSQL fails
    if settings.ENVIRONMENT == "development":
        logger.warning("Falling back to SQLite for development")
        engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    else:
        logger.error("Could not create database engine, application may not function correctly")
        raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session.
    Implements retries for transient database errors.
    """
    db = None
    retry_count = 0
    max_retries = 3
    retry_delay = 1  # seconds
    
    while retry_count < max_retries:
        try:
            db = SessionLocal()
            # Test connection
            db.execute(sqlalchemy.text("SELECT 1"))
            yield db
            break
        except sqlalchemy.exc.OperationalError as e:
            retry_count += 1
            logger.warning(f"Database connection error (attempt {retry_count}/{max_retries}): {str(e)}")
            if db:
                db.close()
            
            if retry_count >= max_retries:
                logger.error(f"Maximum retry attempts reached. Database connection failed: {str(e)}")
                raise
            
            # Wait before retrying
            time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected database error: {str(e)}")
            if db:
                db.close()
            raise
        finally:
            if db:
                db.close()

def test_db_connection():
    """Test database connection and report any issues"""
    try:
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            conn.commit()
            result.fetchone()
        return True, "Database connection successful"
    except sqlalchemy.exc.OperationalError as e:
        return False, f"Database connection error: {str(e)}"
    except Exception as e:
        return False, f"Database error: {str(e)}"