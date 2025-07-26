from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from models.job_status import JobStatus
from typing import Optional, Dict, Any, List
from enum import Enum
from schemas.book import BookDataProcessingJob
from pydantic import HttpUrl

class Language(str, Enum):
    CHINESE = "Chinese"
    CHINESE_YUE = "Chinese,Yue"
    ENGLISH = "English"
    ARABIC = "Arabic"
    RUSSIAN = "Russian"
    SPANISH = "Spanish"
    FRENCH = "French"
    PORTUGUESE = "Portuguese"
    GERMAN = "German"
    TURKISH = "Turkish"
    DUTCH = "Dutch"
    UKRAINIAN = "Ukrainian"
    VIETNAMESE = "Vietnamese"
    INDONESIAN = "Indonesian"
    JAPANESE = "Japanese"
    ITALIAN = "Italian"
    KOREAN = "Korean"
    THAI = "Thai"
    POLISH = "Polish"
    ROMANIAN = "Romanian"
    GREEK = "Greek"
    CZECH = "Czech"
    FINNISH = "Finnish"
    HINDI = "Hindi"
    AUTO = "auto"

class VoiceId(str, Enum):
    WISE_WOMAN = "Wise_Woman"
    FRIENDLY_PERSON = "Friendly_Person"
    INSPIRATIONAL_GIRL = "Inspirational_girl"
    DEEP_VOICE_MAN = "Deep_Voice_Man"
    CALM_WOMAN = "Calm_Woman"
    CASUAL_GUY = "Casual_Guy"
    LIVELY_GIRL = "Lively_Girl"
    PATIENT_MAN = "Patient_Man"
    YOUNG_KNIGHT = "Young_Knight"
    DETERMINED_MAN = "Determined_Man"
    LOVELY_GIRL = "Lovely_Girl"
    DECENT_BOY = "Decent_Boy"
    IMPOSING_MANNER = "Imposing_Manner"
    ELEGANT_MAN = "Elegant_Man"
    ABBESS = "Abbess"
    SWEET_GIRL_2 = "Sweet_Girl_2"
    EXUBERANT_GIRL = "Exuberant_Girl"

class SampleRate(int, Enum):
    SR_8000 = 8000
    SR_16000 = 16000
    SR_22050 = 22050
    SR_24000 = 24000
    SR_32000 = 32000
    SR_44100 = 44100

class BitRate(int, Enum):
    BR_32000 = 32000
    BR_64000 = 64000
    BR_128000 = 128000
    BR_256000 = 256000

class VoiceEmotion(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"

class AudioSettings(BaseModel):
    sample_rate: SampleRate = Field(default=SampleRate.SR_32000, description="Audio sample rate in Hz")
    bitrate: BitRate = Field(default=BitRate.BR_256000, description="Audio bitrate in bps")
    channel: int = Field(default=1, ge=1, le=2, description="Number of audio channels (1 for mono, 2 for stereo)")

class VoiceSettings(BaseModel):
    voice_id: VoiceId = Field(
        default=VoiceId.WISE_WOMAN,
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
        default=VoiceEmotion.NEUTRAL,
        description="Emotion of the generated speech"
    )
    english_normalization: bool = Field(
        default=False,
        description="Enables English text normalization to improve number reading performance"
    )

class AudioGenerationRequest(BaseModel):
    language_boost: Language = Field(default=Language.AUTO, description="Language to optimize the audio generation for")
    audio_settings: AudioSettings = Field(default_factory=AudioSettings, description="Audio output settings")
    voice_settings: VoiceSettings = Field(default_factory=VoiceSettings, description="Voice synthesis settings")
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
    created_at: datetime
    s3_url: HttpUrl

    class Config:
        from_attributes = True 


