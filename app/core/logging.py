import logging
import sys
from pathlib import Path
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()  # Get log level from environment variable
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                os.path.join("logs", "app.log"),
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=5  # Keep 5 backup files
            )
        ]
    )
    
    # Setup specific loggers
    logger = logging.getLogger("himalai")  # Changed from "tripo" to "himalai"
    logger.setLevel(logging.DEBUG)
    
    return logger

# Create logger instance
logger = setup_logging()

# Example usage
logger.info("Logging setup complete.")
