from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..schemas.user import UserCreateRequest, UserResponse  # Update import
from ..services.auth_service import create_user, verify_user
from ..utils.email import send_verification_email
from ..models.user import User

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
    user_request: UserCreateRequest,  # Change from UserCreate to UserCreateRequest
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

@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_email(verification_code: str, email: str, db: Session = Depends(get_db)):
    """
    Verify a user's email using the verification code.
    """
    if verify_user(db, verification_code, email):
        return {"message": "Email verified successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or code expired"
        )