from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    quota: Optional[int] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    quota: int
    used_space: int
    is_admin: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class FileCreate(BaseModel):
    filename: str
    parent_id: Optional[int] = None
    is_directory: bool = False

class FileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: Optional[str]
    created_at: datetime
    modified_at: datetime
    parent_id: Optional[int]
    is_directory: bool
    
    class Config:
        from_attributes = True

class PhotoResponse(BaseModel):
    id: int
    file_path: str
    thumbnail_path: Optional[str]
    width: int
    height: int
    capture_date: Optional[datetime]
    location: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ShareCreate(BaseModel):
    file_id: int
    shared_with: Optional[int] = None
    expires_in_hours: Optional[int] = None
