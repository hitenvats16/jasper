from pydantic import BaseModel, EmailStr
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime

class TokenData(BaseModel):
    user_id: int
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    code: str 