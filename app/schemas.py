from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# Auth schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    profile_photo_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Story schemas
class StoryCreate(BaseModel):
    close_friends_list: Optional[str] = None  # Comma-separated user IDs

class StoryResponse(BaseModel):
    id: int
    media_url: str
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Post schemas
class PostItemCreate(BaseModel):
    media_url: str  
    order: int = 0

class PostCreate(BaseModel):
    description: Optional[str] = None
    items: List[PostItemCreate]  # One post can have multiple photos

class PostItemResponse(BaseModel):
    id: int
    media_url: str
    order: int
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: int
    description: Optional[str]
    user_id: int
    created_at: datetime
    items: List[PostItemResponse]
    
    class Config:
        from_attributes = True

# Follow schemas
class FollowResponse(BaseModel):
    follower_id: int
    following_id: int
    created_at: datetime