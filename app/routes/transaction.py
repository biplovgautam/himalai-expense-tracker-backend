from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..core.database import get_db
from ..schemas.transaction import Transaction, TransactionCreate, TransactionUpdate
from ..models.user import User
from ..services.transaction_service import (
    create_transaction,
    get_transaction_by_id,
    get_transactions,
    create_transactions_batch
)

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

@router.get("/", response_model=List[Transaction])
async def get_all_transactions(
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000)
):
    """
    Get all transactions for the requesting user.
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fetch transactions
    transactions = get_transactions(db=db, user_id=user.id, skip=skip, limit=limit)
    return transactions

@router.post("/", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_new_transaction(
    transaction_data: TransactionCreate,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Create a new transaction for the requesting user.
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create transaction
    return create_transaction(db=db, transaction_data=transaction_data, user_id=user.id)

@router.patch("/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: UUID,
    transaction_data: TransactionUpdate,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Update an existing transaction for the requesting user.
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fetch the transaction
    transaction = get_transaction_by_id(db=db, transaction_id=transaction_id, user_id=user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update transaction
    for field, value in transaction_data.dict(exclude_unset=True).items():
        setattr(transaction, field, value)
    
    db.commit()
    db.refresh(transaction)
    return transaction

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a transaction for the requesting user.
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fetch the transaction
    transaction = get_transaction_by_id(db=db, transaction_id=transaction_id, user_id=user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Delete transaction
    db.delete(transaction)
    db.commit()
    return None

@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: UUID,
    requesting_user_id: UUID,
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