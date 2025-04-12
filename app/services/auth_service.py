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
from jose import jwt
from typing import Optional
from ..core.config import settings

# Silence the specific bcrypt warning
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

# Password verification
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

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
        id=uuid.uuid4(),  # Don't convert to string - keep as UUID object
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
        id=uuid.uuid4(),  # Don't convert to string - keep as UUID object
        user_id=db_user.id,
        points=10  # Start with 10 points as a welcome bonus
    )
    
    # Add both user and profile
    db.add(db_profile)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username/email and password.
    Returns the user if authentication is successful, None otherwise.
    """
    # Check if input is email or username
    if "@" in username_or_email:
        user = db.query(User).filter(User.email == username_or_email).first()
    else:
        user = db.query(User).filter(User.username == username_or_email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password):
        return None
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT token with the provided data and expiration time.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt

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