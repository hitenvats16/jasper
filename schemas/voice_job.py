from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from models.voice_job import JobStatus
from datetime import datetime

class VoiceProcessingJobCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class VoiceProcessingJobRead(BaseModel):
    id: int
    s3_link: str
    meta_data: Optional[Dict[str, Any]]
    status: JobStatus
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    is_deleted: bool = False
    user_id: int
    voice_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 