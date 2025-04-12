from sqlalchemy.orm import Session
from datetime import datetime
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate
from typing import List, Optional
import uuid

def create_transaction(db: Session, transaction_data: TransactionCreate, user_id: uuid.UUID) -> Transaction:
    """Create a new transaction record for a user"""
    db_transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        transaction_id=transaction_data.transaction_id,
        date=transaction_data.date,
        time=transaction_data.time,
        description=transaction_data.description,
        dr=transaction_data.dr,
        cr=transaction_data.cr,
        source=transaction_data.source,
        balance=transaction_data.balance,
        raw_data=transaction_data.raw_data
    )
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_transactions(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Transaction]:
    """Get all transactions for a user with pagination"""
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.date.desc(), Transaction.time.desc()).offset(skip).limit(limit).all()

def get_transaction_by_id(db: Session, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Transaction]:
    """Get a specific transaction by ID for a user"""
    return db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()