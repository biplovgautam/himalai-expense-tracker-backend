from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from app.models.user import User, UserProfile
from app.schemas.user import (
    UserResponse, PaginatedUserResponse,
    ProfileResponse, ProfileUpdate  # Import from schemas
)

router = APIRouter()

@router.get("/", response_model=PaginatedUserResponse)
def get_users(
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None
):
    """
    Get all users with pagination and optional search.
    Only accessible by admin users.
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
    
    # Continue with the existing logic
    query = db.query(User)
    
    # Apply search if provided
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term))
        )
    
    # Get total count for pagination
    total = query.count()
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    
    # Format response with user profiles included
    result = []
    for user in users:
        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "profile": {
                "points": user.profile.points if user.profile else 0,
                "total_uploads": user.profile.total_uploads if user.profile else 0,
                # Include other profile fields as needed
            }
        }
        result.append(user_dict)
    
    return {
        "items": result,
        "total": total,
        "page": skip // limit + 1,
        "pages": (total + limit - 1) // limit
    }

@router.get("/profile", response_model=ProfileResponse)
def get_user_profile(
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the current user's profile with points
    """
    user = db.query(User).filter(User.id == requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return profile, create one if it doesn't exist
    if not user.profile:
        profile = UserProfile(user_id=user.id, points=0, total_uploads=0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    
    return user.profile

@router.patch("/{user_id}/profile", response_model=ProfileResponse)
def update_user_profile(
    user_id: UUID,
    profile_data: ProfileUpdate,
    requesting_user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Update user profile.
    Users can only update their own profile unless they are an admin.
    """
    # Check if requesting user exists
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if not requesting_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )
    
    # Check permissions - users can only update their own profile unless they are admin
    if str(requesting_user_id) != str(user_id) and not requesting_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update another user's profile"
        )
    
    # Get the target user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get or create profile
    profile = user.profile
    if not profile:
        profile = UserProfile(user_id=user.id, points=0, total_uploads=0)
        db.add(profile)
    
    # Update profile fields
    for field, value in profile_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.
    Admin can get any user. Regular users can only get their own data.
    """
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if not requesting_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )
    
    if not requesting_user.is_admin and str(requesting_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_data: dict,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Update a user. Admin only.
    """
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
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    for field, value in user_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    requesting_user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a user. Admin only.
    """
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
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    return None
