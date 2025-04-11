from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
import uuid
from ..models.user import User, UserProfile
from ..schemas.user import UserCreate
from passlib.context import CryptContext
import logging
from ..core.logging import logger

# Silence the specific bcrypt warning
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def generate_verification_code() -> str:
    """Generate a random 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))

def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user with verification code and create user profile.
    Returns the created user.
    """
    # Generate hashed password and verification code
    hashed_password = get_password_hash(user_data.password)
    verification_code = generate_verification_code()
    
    # Create User instance
    db_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username or user_data.email.split('@')[0],
        password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=False,  # User starts as inactive until email is verified
        vr_code=verification_code,
        vr_code_expires=datetime.utcnow() + timedelta(hours=24)  # Code expires in 24 hours
    )
    
    # Add and flush to get the user ID
    db.add(db_user)
    db.flush()
    
    # Create user profile
    db_profile = UserProfile(
        id=str(uuid.uuid4()),
        user_id=db_user.id,
        points=10  # Start with 10 points as a welcome bonus
    )
    
    # Add both user and profile
    db.add(db_profile)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def verify_user(db: Session, verification_code: str, email: str) -> bool:
    """
    Verify a user's email using the verification code.
    Returns True if verification is successful, False otherwise.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user or user.vr_code != verification_code:
        return False
    
    # Check if verification code has expired
    if datetime.utcnow() > user.vr_code_expires:
        return False
    
    # Activate the user
    user.is_active = True
    user.vr_code = None  # Clear the verification code
    user.vr_code_expires = None
    
    db.commit()
    return True