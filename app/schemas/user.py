from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Union, Dict, Any

from datetime import datetime
import re
import uuid

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    
    @validator('username', pre=True, always=True)
    def default_username_from_email(cls, v, values):
        if not v and 'email' in values:
            email_username = values['email'].split('@')[0]
            return email_username
        return v

# This schema is used specifically for the API input - no username field
class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    # Convert to UserCreate model which includes the username
    def to_user_create(self) -> 'UserCreate':
        user_data = self.dict()
        return UserCreate(**user_data)

# Internal model that includes username
class UserCreate(UserBase):
    password: str
    confirm_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserResponse(UserBase):
    id: Union[str, uuid.UUID]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True
        
    @validator('id', pre=True)
    def str_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

class UserProfileBase(BaseModel):
    bio: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: str
    user_id: str
    points: int
    total_uploads: int
    total_transactions: int
    total_savings: float
    profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class UserWithProfile(UserResponse):
    profile: Optional[UserProfileResponse] = None
    
    class Config:
        orm_mode = True

class TokenData(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

class VerificationRequest(BaseModel):
    email: EmailStr
    code: str

class PaginatedUserResponse(BaseModel):
    items: List[Dict[str, Any]]  # Using Dict instead of UserResponse to avoid circular refs
    total: int
    page: int
    pages: int
    
    class Config:
        from_attributes = True
        orm_mode = True