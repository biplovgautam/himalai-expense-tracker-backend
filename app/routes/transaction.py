from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..core.database import get_db
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
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Create a new transaction for the user with the provided user ID
    """
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return create_transaction(db=db, transaction_data=transaction_data, user_id=user.id)

@router.get("/", response_model=List[Transaction])
async def get_all_transactions(
    requesting_user_id: UUID,  # Add requesting user ID parameter
    db: Session = Depends(get_db)
):
    """
    Get all transactions for the user with the provided user ID
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return get_transactions(db=db, user_id=user.id)

@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: UUID,
    requesting_user_id: UUID,  # Add requesting user ID parameter
    db: Session = Depends(get_db)
):
    """
    Get specific transaction by ID
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    transaction = get_transaction_by_id(db=db, transaction_id=transaction_id)
    
    # Verify ownership or admin status
    if transaction.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this transaction"
        )
    
    return transaction