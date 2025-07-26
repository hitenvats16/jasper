from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class OAuthAccountRead(BaseModel):
    provider: str
    provider_user_id: str
    class Config:
        from_attributes = True

class RateRead(BaseModel):
    id: int
    values: float = Field(..., description="Per token rate for the user")

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    oauth_accounts: List[OAuthAccountRead] = []
    profile_picture: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    rate: Optional[RateRead] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Create a dict of the base attributes
        obj_dict = {
            "id": obj.id,
            "email": obj.email,
            "is_active": obj.is_active,
            "is_verified": obj.is_verified,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "oauth_accounts": obj.oauth_accounts,
            "profile_picture": obj.profile_picture,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "rate": obj.rate if hasattr(obj, 'rate') and obj.rate and not obj.rate.is_deleted else None
        }
        return cls(**obj_dict)

class UserUpdate(BaseModel):
    is_active: Optional[bool]
    is_verified: Optional[bool]
    is_deleted: Optional[bool] 