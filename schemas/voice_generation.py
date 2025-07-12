from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChapterData(BaseModel):
    chapter_id: str
    chapter_title: str
    chapter_content: str
    meta_data: Dict[str, Any]

class AudioGenerationParams(BaseModel):
    exaggeration: Optional[float] = 0.65
    temperature: Optional[float] = 0.7
    cfg: Optional[float] = 0.1
    seed: Optional[int] = None

class VoiceGenerationRequest(BaseModel):
    chapters: List[ChapterData]
    book_id: int
    voice_id: Optional[int] = None
    audio_generation_params: Optional[AudioGenerationParams] = None

class VoiceGenerationResponse(BaseModel):
    job_id: int
    status: str
    message: str
    created_at: datetime

class ProcessedVoiceChunkResponse(BaseModel):
    id: int
    s3_key: str
    s3_public_link: str  # S3 public URL for the voice file
    index: int
    chapter_id: str
    data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True 