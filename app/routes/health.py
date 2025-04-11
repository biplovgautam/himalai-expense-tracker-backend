from fastapi import APIRouter, Depends
from ..core.database import test_db_connection

router = APIRouter(tags=["Health"])

@router.get("/health", operation_id="himalai_health_check")
async def health_check():
    """
    Check the health of the API and its dependencies.
    """
    return {
        "status": "ok", 
        "service": "himalai-backend", 
        "database": test_db_connection()
    }