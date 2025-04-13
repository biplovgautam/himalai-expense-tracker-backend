from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum

class VoucherType(str, Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"

class VoucherBase(BaseModel):
    code: str
    title: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    amount: float
    type: VoucherType = VoucherType.FIXED
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    usage_limit: Optional[int] = 1
    min_purchase_amount: float = 0.0

class VoucherCreate(VoucherBase):
    @validator('amount')
    def validate_amount(cls, v, values):
        if 'type' in values and values['type'] == VoucherType.PERCENTAGE and (v < 0 or v > 100):
            raise ValueError('Percentage discount must be between 0 and 100')
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v

class VoucherUpdate(BaseModel):
    description: Optional[str] = None
    image_url: Optional[str] = None
    title: Optional[str] = None
    code: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[VoucherType] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None
    usage_limit: Optional[int] = None
    min_purchase_amount: Optional[float] = None

class VoucherResponse(VoucherBase):
    id: UUID
    usage_count: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True
        orm_mode = True
        
class VoucherValidateResponse(BaseModel):
    valid: bool
    message: str
    voucher: Optional[VoucherResponse] = None
    discount_amount: Optional[float] = None