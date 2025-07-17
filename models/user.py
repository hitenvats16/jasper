from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from db.session import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_admin = Column(Boolean, default=False)
    profile_picture = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Optimized relationships - using lazy loading instead of eager loading
    # This prevents the 23-second delay caused by 13 JOIN operations
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan", lazy="select")
    voices = relationship("Voice", back_populates="user", cascade="all, delete-orphan", lazy="select")
    credit = relationship("UserCredit", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="select")
    voice_jobs = relationship("VoiceProcessingJob", back_populates="user", cascade="all, delete-orphan", lazy="select")
    book_processing_jobs = relationship("BookProcessingJob", back_populates="user", cascade="all, delete-orphan", lazy="select")
    book_voice_processing_jobs = relationship("BookVoiceProcessingJob", back_populates="user", cascade="all, delete-orphan", lazy="select")
    processed_voice_chunks = relationship("ProcessedVoiceChunks", back_populates="user", cascade="all, delete-orphan", lazy="select")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan", lazy="select")
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan", lazy="select")
    config = relationship("Config", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="select")
    # Payment relationships
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan", lazy="select")
    refunds = relationship("PaymentRefund", back_populates="user", cascade="all, delete-orphan", lazy="select")
    # Rate relationship
    rate = relationship("Rate", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="select")

class OAuthAccount(Base):
    __tablename__ = "oauth_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    provider = Column(String, nullable=False)  # e.g., 'google', 'facebook'
    provider_user_id = Column(String, nullable=False)  # The unique ID from the provider
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="oauth_accounts", lazy="select") 