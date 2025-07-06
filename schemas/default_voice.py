from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DefaultVoiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    s3_key: str
    is_public: bool = True

class DefaultVoiceCreate(DefaultVoiceBase):
    pass

class DefaultVoiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    s3_key: Optional[str] = None
    is_public: Optional[bool] = None

class DefaultVoiceRead(DefaultVoiceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 