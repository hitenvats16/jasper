from pydantic import EmailStr, validator
from typing import Optional
from pydantic_settings import BaseSettings
import logging
import os
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # S3 Presigned URL Settings
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # 1 hour in seconds
    S3_PRESIGNED_URL_CACHE_TTL: int = 1800  # 30 minutes in seconds

    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # Database settings with default value
    SQLALCHEMY_DATABASE_URL: str 
    
    # Optional settings with defaults
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_ENDPOINT: Optional[str] = None  # Changed from AWS_S3_ENDPOINT to AWS_ENDPOINT
    
    # RabbitMQ settings
    RABBITMQ_URL: str
    VOICE_PROCESSING_QUEUE: str = "voice_processing"
    TEXT_PARSER_QUEUE: str = "book_parser"
    VOICE_GENERATION_QUEUE: str = "audio_generation"

    # Groq settings
    GROQ_API_KEY: str

    # Fal.AI settings
    FAL_API_KEY: str
    
    # LemonSqueezy settings
    LEMON_SQUEEZY_API_KEY: Optional[str] = None
    LEMON_SQUEEZY_WEBHOOK_SECRET: Optional[str] = None
    LEMON_SQUEEZY_STORE_ID: Optional[str] = None

    DEFAULT_PER_TOKEN_RATE: Optional[float] = 0.0067
    
    # Credit settings
    DEFAULT_USER_CREDITS: float = 1000.0
    
    # Email settings
    RESEND_API_KEY: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@zovoice.com"
    FRONTEND_URL: str = "https://zovoice.com"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "allow"

# Load settings and log the database URL (masked)
settings = Settings()
logger.info(f"Loaded database URL: {settings.SQLALCHEMY_DATABASE_URL}") 