from pydantic import BaseModel, EmailStr
from typing import Optional, List

class OAuthAccountRead(BaseModel):
    provider: str
    provider_user_id: str
    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    oauth_accounts: List[OAuthAccountRead] = []
    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    is_active: Optional[bool]
    is_verified: Optional[bool] 