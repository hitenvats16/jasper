from pydantic import EmailStr, validator
from typing import Optional
from pydantic_settings import BaseSettings
import logging
import os
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "jasper-voice-gateway"
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # Database settings with default value
    SQLALCHEMY_DATABASE_URL: str 
    
    # Optional settings with defaults
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_ENDPOINT: Optional[str] = None  # Changed from AWS_S3_ENDPOINT to AWS_ENDPOINT
    AWS_PUBLIC_URL: Optional[str] = None
    
    # RabbitMQ settings
    RABBITMQ_URL: str
    RABBITMQ_VHOST: str = ""
    VOICE_PROCESSING_QUEUE: str = "voice_processing"
    TEXT_PARSER_QUEUE: str = "text_parser"
    VOICE_GENERATION_QUEUE: str = "audio_generation"
    
    # Qdrant settings
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] 

    # Checkpoints settings
    CHECKPOINTS_URL: str = "https://pub-ac88a2c53a93464980d73555cf36e296.r2.dev/voice_processing/checkpoints_v2_0417.zip"

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

    @validator("SQLALCHEMY_DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("SQLALCHEMY_DATABASE_URL is required")
        
        # Parse the URL and encode special characters
        if v.startswith("postgresql://"):
            # Split the URL into parts
            protocol, rest = v.split("://", 1)
            auth, host = rest.split("@", 1)
            username, password = auth.split(":", 1)
            
            # URL encode the password
            encoded_password = quote_plus(password)
            
            # Reconstruct the URL
            v = f"{protocol}://{username}:{encoded_password}@{host}"
            
        logger.info(f"Database URL configured (masked): {v.split('@')[0]}@***")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "allow"

# Load settings and log the database URL (masked)
settings = Settings()
logger.info(f"Loaded database URL: {settings.SQLALCHEMY_DATABASE_URL}") 