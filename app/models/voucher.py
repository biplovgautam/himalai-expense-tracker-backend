import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.core.database import Base

class VoucherType(str, PyEnum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"

class Voucher(Base):
    __tablename__ = "vouchers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)  # Title of the voucher
    description = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False, default=VoucherType.FIXED)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, default=1)  # How many times it can be used
    usage_count = Column(Integer, default=0)  # How many times it has been used
    min_purchase_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    image_url = Column(String, nullable=True)  # URL to an image of the voucher
    
    # Optional: track who created the voucher
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", back_populates="created_vouchers")
    
    
    def is_valid(self):
        """Check if voucher is currently valid"""
        now = datetime.utcnow()
        return (
            self.is_active and
            (self.valid_from is None or now >= self.valid_from) and
            (self.valid_until is None or now <= self.valid_until) and
            (self.usage_limit is None or self.usage_count < self.usage_limit)
        )