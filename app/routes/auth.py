from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from jose import jwt, JWTError
from ..core.database import get_db
from ..schemas.user import UserCreateRequest, UserResponse, TokenResponse, VerificationRequest
from ..services.auth_service import create_user, verify_user, authenticate_user, create_access_token
from ..utils.email import send_verification_email
from ..models.user import User
from ..core.config import settings

router = APIRouter(tags=["Authentication"], prefix="/auth")

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
            openapi_extra={
                "requestBody": {
                    "content": {
                        "application/json": {
                            "example": {
                                "email": "user@example.com",
                                "password": "Password123",
                                "confirm_password": "Password123",
                                "first_name": "John",
                                "last_name": "Doe"
                            }
                        }
                    }
                }
            })
async def signup(
    user_request: UserCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user and send verification code to their email.
    """
    # Convert request model to internal model with username
    user_data = user_request.to_user_create()
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    if user_data.username:
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create the user
    user = create_user(db, user_data)
    
    # Send verification email in the background
    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.vr_code
    )
    
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please verify your email first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    # Create refresh token (optional)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(
        data={"sub": user.email, "refresh": True},
        expires_delta=refresh_token_expires
    )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/verify", response_model=TokenResponse)
async def verify_email(
    verification_data: VerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify email with verification code and return JWT tokens.
    """
    # Verify the code
    verified = verify_user(db, verification_data.code, verification_data.email)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or email"
        )
    
    # Get the user
    user = db.query(User).filter(User.email == verification_data.email).first()
    
    # Create tokens as in login endpoint
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token(
        data={"sub": user.email, "refresh": True},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/check-admin")
async def check_admin_status(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if a user is an admin by email.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return {
        "is_admin": user.is_admin,
        "user_id": str(user.id),
        "email": user.email,
        "username": user.username
    }

@router.post("/logout")
async def logout(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Logout endpoint - invalidates the current session
    
    Note: This is a best-practice implementation for JWT authentication.
    The client must remove tokens from local storage after this call.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    
    try:
        # Decode token to get user information
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        
        # Optional: For enhanced security, you could implement token blacklisting here
        # For example, store token in a Redis blacklist with expiry = token's remaining lifetime
        
        # Update last session info if needed
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Optional: Update user's session info if needed
            # user.last_logout = datetime.utcnow()
            # db.commit()
            pass
            
        return {"status": "success", "message": "Successfully logged out"}
        
    except JWTError:
        # Token is invalid, which is fine for logout
        return {"status": "success", "message": "Successfully logged out"}