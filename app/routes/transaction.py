from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..core.database import get_db
from ..core.auth import get_current_user
from ..schemas.transaction import Transaction, TransactionCreate
from ..models.user import User
from ..services.transaction_service import create_transaction, get_transaction_by_id, get_transactions

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

@router.post("/", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_new_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new transaction for the authenticated user
    """
    return create_transaction(db=db, transaction_data=transaction_data, user_id=current_user.id)