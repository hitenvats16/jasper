from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class OAuthAccountRead(BaseModel):
    provider: str
    provider_user_id: str
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    is_deleted: bool = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    oauth_accounts: List[OAuthAccountRead] = []

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    is_active: Optional[bool]
    is_verified: Optional[bool]
    is_deleted: Optional[bool] 