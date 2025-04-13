from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
# Add this to your imports in voucher_router.py
from typing import List, Optional, Dict, Any  # Add Dict, Any
from app.core.database import get_db
from app.models.user import User
from app.schemas.voucher import VoucherCreate, VoucherUpdate, VoucherResponse, VoucherValidateResponse
from app.services.voucher_service import (
    create_voucher, get_vouchers, get_voucher_by_id, 
    update_voucher, delete_voucher, validate_voucher, redeem_voucher,
    purchase_voucher  # Add this line
)
router = APIRouter()

@router.post("/", response_model=VoucherResponse, status_code=status.HTTP_201_CREATED)
def create_new_voucher(
    voucher_data: VoucherCreate,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Create a new voucher (Admin only)
    """
    # Verify the requesting user exists and is an admin
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if not requesting_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )
    
    if not requesting_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required"
        )
    
    return create_voucher(db=db, voucher_data=voucher_data, creator_id=requesting_user.id)

@router.get("/", response_model=List[VoucherResponse])
def get_all_vouchers(
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = False
):
    """
    Get all vouchers with pagination
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Regular users can only see active vouchers
    if not user.is_admin:
        active_only = True
    
    return get_vouchers(db=db, skip=skip, limit=limit, active_only=active_only)

# Move this route BEFORE any routes with path parameters like /{id}
@router.get("/purchased", response_model=List[VoucherResponse])
def get_purchased_vouchers(
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all vouchers purchased by the user
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if the user has purchased vouchers
    if not hasattr(user, 'purchased_vouchers'):
        # Return empty list if relationship doesn't exist
        return []
    
    return user.purchased_vouchers

@router.get("/{voucher_id}", response_model=VoucherResponse)
def get_voucher(
    voucher_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific voucher by ID
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    voucher = get_voucher_by_id(db=db, voucher_id=voucher_id)
    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voucher not found"
        )
    
    # Regular users can only see active vouchers
    if not user.is_admin and not voucher.is_valid():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voucher is not available"
        )
    
    return voucher

@router.patch("/{voucher_id}", response_model=VoucherResponse)
def update_existing_voucher(
    voucher_id: UUID,
    voucher_data: VoucherUpdate,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Update a voucher (Admin only)
    """
    # Verify the requesting user exists and is an admin
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if not requesting_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )
    
    if not requesting_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required"
        )
    
    updated_voucher = update_voucher(db=db, voucher_id=voucher_id, voucher_data=voucher_data)
    if not updated_voucher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voucher not found"
        )
    
    return updated_voucher

@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_voucher(
    voucher_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a voucher (Admin only)
    """
    # Verify the requesting user exists and is an admin
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if not requesting_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )
    
    if not requesting_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required"
        )
    
    result = delete_voucher(db=db, voucher_id=voucher_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voucher not found"
        )
    
    return None

@router.post("/validate/{code}", response_model=VoucherValidateResponse)
def validate_voucher_code(
    code: str,
    requesting_user_id: UUID,
    purchase_amount: float = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Validate a voucher code without redeeming it
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = validate_voucher(db=db, code=code, purchase_amount=purchase_amount)
    return result

@router.post("/redeem/{code}", response_model=VoucherValidateResponse)
def redeem_voucher_code(
    code: str,
    requesting_user_id: UUID,
    purchase_amount: float = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Validate and redeem a voucher code
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = redeem_voucher(db=db, code=code, purchase_amount=purchase_amount)
    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result

# Add this endpoint to your voucher router

@router.post("/{voucher_id}/purchase", response_model=Dict[str, Any])
def purchase_voucher_endpoint(
    voucher_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Purchase a voucher with user points
    """
    # Verify user exists
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = purchase_voucher(db=db, voucher_id=voucher_id, user_id=user.id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result
