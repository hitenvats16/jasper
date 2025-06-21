from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Union

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: datetime

class TokenData(BaseModel):
    email: Union[str, None] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    code: str

class OAuthToken(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    provider: str
    provider_user_id: str

    class Config:
        from_attributes = True 