from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from models.voice_job import JobStatus

class VoiceProcessingJobCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class VoiceProcessingJobRead(BaseModel):
    id: int
    s3_link: HttpUrl
    metadata: Optional[Dict[str, Any]]
    status: JobStatus
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    class Config:
        from_attributes = True 