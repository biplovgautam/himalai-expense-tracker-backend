from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import pandas as pd
from io import StringIO
import uuid
import json
import re

from ..core.database import get_db
from ..models.user import User
from ..models.transaction import Transaction
from ..services.file_processor import detect_format, process_file
from ..services.transaction_service import csv_to_transactions

router = APIRouter(
    prefix="/files",
    tags=["file processing"]
)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    """
    Process financial file upload and save transactions
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    try:
        # Process the file to get CSV data
        result = await process_file(file)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["message"]
            )
        
        # Process and save transactions
        from app.services.transaction_service import process_and_save_transactions
        
        save_result = await process_and_save_transactions(
            csv_data=result["data"], 
            user_id=user_id, 
            source=result["source"],
            db=db
        )
        
        # Update user profile statistics if available
        if save_result["success"]:
            if hasattr(user, 'profile') and user.profile:
                user.profile.total_uploads = user.profile.total_uploads + 1
                user.profile.total_transactions = user.profile.total_transactions + save_result["count"] if hasattr(user.profile, "total_transactions") else save_result["count"]
                user.profile.points = user.profile.points + min(10, save_result["count"]) # Award points based on transactions
                db.commit()
        
        return save_result
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )