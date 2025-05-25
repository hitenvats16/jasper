from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional, List
from datetime import datetime

class VoiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class VoiceCreate(VoiceBase):
    pass

class VoiceUpdate(VoiceBase):
    name: Optional[str] = None

class VoiceRead(VoiceBase):
    id: int
    s3_link: HttpUrl
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class VoiceList(BaseModel):
    items: List[VoiceRead]
    total: int 