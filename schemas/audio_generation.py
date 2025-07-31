from pydantic import BaseModel, Field, field_validator, HttpUrl
from datetime import datetime, timezone
from models.job_status import JobStatus
from typing import Optional, Dict, Any, List
from enum import Enum
from schemas.book import BookDataProcessingJob
from schemas.audio_config import SampleRate, BitRate, VoiceEmotion, VoiceId, Language, AudioFormat
from models.audiobook_generation import AudiobookType

class AudioSettings(BaseModel):
    sample_rate: SampleRate = Field(default=SampleRate.SR_32000, description="Audio sample rate in Hz")
    bitrate: BitRate = Field(default=BitRate.BR_256000, description="Audio bitrate in bps")
    channel: int = Field(default=1, ge=1, le=2, description="Number of audio channels (1 for mono, 2 for stereo)")
    format: AudioFormat = Field(default=AudioFormat.mp3, description="Audio format")

class VoiceSettings(BaseModel):
    voice_id: VoiceId = Field(
        default=VoiceId.Wise_Woman,
        description="Predefined voice ID to use for synthesis"
    )
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech speed (0.5-2.0)"
    )
    vol: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Volume (0-10)"
    )
    pitch: int = Field(
        default=0,
        ge=-12,
        le=12,
        description="Voice pitch (-12 to 12)"
    )
    emotion: Optional[VoiceEmotion] = Field(
        default=VoiceEmotion.neutral,
        description="Emotion of the generated speech"
    )
    english_normalization: bool = Field(
        default=False,
        description="Enables English text normalization to improve number reading performance"
    )

class AudioGenerationRequest(BaseModel):
    language_boost: Language = Field(default=Language.auto, description="Language to optimize the audio generation for")
    audio_setting: AudioSettings = Field(default_factory=AudioSettings, description="Audio output settings")
    voice_setting: VoiceSettings = Field(default_factory=VoiceSettings, description="Voice synthesis settings")
    pronunciation_dict: Dict[str, List[str]] = Field(
        default_factory=lambda: {"tone_list": []},
        description="Pronunciation dictionary containing tone list"
    )
    book_data: BookDataProcessingJob = Field(default_factory=BookDataProcessingJob, description="Book data to generate audio from")

    @field_validator('pronunciation_dict')
    @classmethod
    def validate_pronunciation_dict(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        allowed_keys = {"tone_list"}
        actual_keys = set(v.keys())
        
        if actual_keys != allowed_keys:
            raise ValueError(f"pronunciation_dict can only contain 'tone_list' key. Found: {actual_keys}")
        
        return v

class AudioGenerationResponse(BaseModel):
    """Response model for audio generation job creation"""
    job_id: int
    status: JobStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    s3_url: HttpUrl

    class Config:
        from_attributes = True 

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class AudioJobSortField(str, Enum):
    CREATED_AT = "created_at"
    ENDED_AT = "ended_at"
    STATUS = "status"
    PROJECT_ID = "project_id"

class AudiobookGenerationRead(BaseModel):
    """Schema for audiobook generation data"""
    id: int
    key: str
    data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    s3_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True

class AudioGenerationJobRead(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    voice_id: int
    input_data_s3_key: str
    job_metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status: JobStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    s3_url: Optional[HttpUrl] = None
    # New fields for audiobook generation
    chapterwise_audios: Optional[List[AudiobookGenerationRead]] = None
    full_audio: Optional[AudiobookGenerationRead] = None
    has_full_audio: bool = False

    class Config:
        from_attributes = True

class AudioGenerationJobFilters(BaseModel):
    """Query parameters for filtering audio generation jobs"""
    project_id: Optional[int] = Field(None, description="Filter by project ID")
    voice_id: Optional[int] = Field(None, description="Filter by voice ID")
    status: Optional[JobStatus] = Field(None, description="Filter by job status")
    language: Optional[Language] = Field(None, description="Filter by language boost setting")
    created_after: Optional[datetime] = Field(None, description="Filter jobs created after this datetime")
    created_before: Optional[datetime] = Field(None, description="Filter jobs created before this datetime")
    ended_after: Optional[datetime] = Field(None, description="Filter jobs that ended after this datetime")
    ended_before: Optional[datetime] = Field(None, description="Filter jobs that ended before this datetime")
    sort_by: Optional[AudioJobSortField] = Field(AudioJobSortField.CREATED_AT, description="Field to sort by")
    sort_order: Optional[SortOrder] = Field(SortOrder.DESC, description="Sort order (asc/desc)")
    page: Optional[int] = Field(1, ge=1, description="Page number")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="Items per page")
    s3_url: Optional[HttpUrl] = Field(None, description="Filter by S3 URL")

class AudioGenerationJobListResponse(BaseModel):
    """Response model for paginated audio generation job list"""
    items: List[AudioGenerationJobRead]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True 


