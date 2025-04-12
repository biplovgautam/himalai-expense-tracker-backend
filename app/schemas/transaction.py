from pydantic import BaseModel, UUID4, Field
from typing import Optional
from datetime import date, time, datetime

class TransactionBase(BaseModel):
    transaction_id: Optional[str] = None
    date: date
    time: time
    description: Optional[str] = None
    dr: float = 0.0
    cr: float = 0.0
    source: str
    balance: float
    raw_data: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    transaction_id: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    description: Optional[str] = None
    dr: Optional[float] = None
    cr: Optional[float] = None
    source: Optional[str] = None
    balance: Optional[float] = None
    raw_data: Optional[str] = None

class TransactionInDB(TransactionBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime

    class Config:
        orm_mode = True

class Transaction(TransactionInDB):
    pass