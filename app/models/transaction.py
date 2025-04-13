from sqlalchemy import Column, String, Date, Time, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
import uuid

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False)
    transaction_time = Column(Time, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    dr = Column(Float, default=0.0)
    cr = Column(Float, default=0.0)
    source = Column(String, nullable=False)
    balance = Column(Float, nullable=False)
    raw_data = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="transactions")