from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
import random
import string
from fastapi import HTTPException, status
from app.models.user import User

from app.models.voucher import Voucher, VoucherType
from app.schemas.voucher import VoucherCreate, VoucherUpdate

def generate_voucher_code(length=8):
    """Generate a random voucher code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_voucher(db: Session, voucher_data: VoucherCreate, creator_id: UUID = None):
    """Create a new voucher"""
    db_voucher = Voucher(
        code=voucher_data.code,
        title=voucher_data.title,  # Make sure this field is included
        description=voucher_data.description,
        points_cost=voucher_data.points_cost,
        amount=voucher_data.amount,
        type=voucher_data.type,
        valid_from=voucher_data.valid_from or datetime.utcnow(),
        valid_until=voucher_data.valid_until,
        is_active=voucher_data.is_active if hasattr(voucher_data, 'is_active') else True,
        usage_limit=voucher_data.usage_limit if hasattr(voucher_data, 'usage_limit') else 1,
        min_purchase_amount=voucher_data.min_purchase_amount if hasattr(voucher_data, 'min_purchase_amount') else 0.0,
        created_by_id=creator_id
    )
    
    db.add(db_voucher)
    db.commit()
    db.refresh(db_voucher)
    return db_voucher  # Add this return statement
# Add this function to your existing voucher_service.py

def purchase_voucher(db: Session, voucher_id: UUID, user_id: UUID):
    """Purchase a voucher with user points"""
    # Get the user and voucher
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}
    
    voucher = get_voucher_by_id(db, voucher_id)
    if not voucher:
        return {"success": False, "message": "Voucher not found"}
    
    # Check if voucher is valid
    if not voucher.is_valid():
        return {"success": False, "message": "Voucher is not available"}
    
    # Check if user has enough points
    if user.profile.points < voucher.points_cost:
        return {"success": False, "message": f"Not enough points. Required: {voucher.points_cost}, Available: {user.profile.points}"}
    
    # Check if user already purchased this voucher
    if voucher in user.purchased_vouchers:
        return {"success": False, "message": "You have already purchased this voucher"}
    
    # Deduct points and add voucher to user's purchased vouchers
    user.profile.points -= voucher.points_cost
    user.purchased_vouchers.append(voucher)
    
    # Increase usage count
    voucher.usage_count += 1
    
    db.commit()
    
    return {
        "success": True, 
        "message": "Voucher purchased successfully", 
        "voucher": voucher,
        "remaining_points": user.profile.points
    }

def get_vouchers(db: Session, skip: int = 0, limit: int = 100, active_only: bool = False):
    """Get all vouchers with optional filtering"""
    query = db.query(Voucher)
    
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            Voucher.is_active == True,
            (Voucher.valid_from == None) | (Voucher.valid_from <= now),
            (Voucher.valid_until == None) | (Voucher.valid_until >= now),
            (Voucher.usage_limit == None) | (Voucher.usage_count < Voucher.usage_limit)
        )
    
    return query.offset(skip).limit(limit).all()

def get_voucher_by_id(db: Session, voucher_id: UUID):
    """Get voucher by ID"""
    return db.query(Voucher).filter(Voucher.id == voucher_id).first()

def get_voucher_by_code(db: Session, code: str):
    """Get voucher by code"""
    return db.query(Voucher).filter(Voucher.code == code).first()

def update_voucher(db: Session, voucher_id: UUID, voucher_data: VoucherUpdate):
    """Update an existing voucher"""
    voucher = get_voucher_by_id(db, voucher_id)
    if not voucher:
        return None
    
    for field, value in voucher_data.dict(exclude_unset=True).items():
        setattr(voucher, field, value)
    
    db.commit()
    db.refresh(voucher)
    return voucher

def delete_voucher(db: Session, voucher_id: UUID):
    """Delete a voucher"""
    voucher = get_voucher_by_id(db, voucher_id)
    if not voucher:
        return False
    
    db.delete(voucher)
    db.commit()
    return True

def validate_voucher(db: Session, code: str, purchase_amount: float = 0):
    """Validate if voucher is applicable"""
    voucher = get_voucher_by_code(db, code)
    
    if not voucher:
        return {"valid": False, "message": "Voucher not found", "voucher": None}
    
    if not voucher.is_active:
        return {"valid": False, "message": "Voucher is inactive", "voucher": voucher}
    
    now = datetime.utcnow()
    if voucher.valid_from and now < voucher.valid_from:
        return {"valid": False, "message": "Voucher is not yet valid", "voucher": voucher}
    
    if voucher.valid_until and now > voucher.valid_until:
        return {"valid": False, "message": "Voucher has expired", "voucher": voucher}
    
    if voucher.usage_limit and voucher.usage_count >= voucher.usage_limit:
        return {"valid": False, "message": "Voucher usage limit exceeded", "voucher": voucher}
    
    if purchase_amount < voucher.min_purchase_amount:
        return {
            "valid": False, 
            "message": f"Minimum purchase amount not met (${voucher.min_purchase_amount})", 
            "voucher": voucher
        }
    
    # Calculate discount
    discount = 0
    if voucher.type == VoucherType.FIXED:
        discount = voucher.amount
    else:  # percentage
        discount = (voucher.amount / 100) * purchase_amount
    
    return {
        "valid": True, 
        "message": "Voucher is valid", 
        "voucher": voucher,
        "discount_amount": discount
    }

def redeem_voucher(db: Session, code: str, purchase_amount: float = 0):
    """Validate and redeem a voucher"""
    result = validate_voucher(db, code, purchase_amount)
    
    if not result["valid"]:
        return result
    
    voucher = result["voucher"]
    voucher.usage_count += 1
    db.commit()
    
    return result