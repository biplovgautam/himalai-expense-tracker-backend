from sqlalchemy.orm import Session
from datetime import datetime
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate
from typing import List, Optional, Dict
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

def create_transactions_batch(db: Session, transactions_data: List[Dict], user_id: uuid.UUID) -> List[Transaction]:
    """
    Create multiple transactions at once from processed file data
    """
    db_transactions = []
    
    for transaction_data in transactions_data:
        try:
            # Convert string date/time to appropriate objects if needed
            from datetime import datetime
            
            # Create transaction object
            db_transaction = Transaction(
                id=uuid.uuid4(),
                user_id=user_id,
                transaction_id=transaction_data.get("transaction_id"),
                transaction_date=transaction_data.get("transaction_date"),
                transaction_time=transaction_data.get("transaction_time"),
                description=transaction_data.get("description"),
                dr=float(transaction_data.get("dr", 0)),
                cr=float(transaction_data.get("cr", 0)),
                source=transaction_data.get("source", "file_upload"),
                balance=float(transaction_data.get("balance", 0)),
                raw_data=transaction_data.get("raw_data")
            )
            
            db_transactions.append(db_transaction)
            
        except Exception as e:
            print(f"Error creating transaction: {str(e)}")
            # Continue with other transactions
            continue
    
    # Bulk insert all transactions
    if db_transactions:
        db.add_all(db_transactions)
        db.commit()
        
    return db_transactions