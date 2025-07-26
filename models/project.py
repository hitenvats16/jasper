from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship
from db.session import Base


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Store tags as JSON array
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    data = Column(JSON, nullable=True)  # Store any additional JSON data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationship with User
    user = relationship("User", back_populates="projects", lazy="select")
    
    # Relationship with Books (optional - through association table)
    books = relationship("Book", secondary="book_project_association", back_populates="projects", lazy="select")
    
    # Relationship with Audio Generation Jobs
    audio_generation_jobs = relationship("AudioGenerationJob", back_populates="project", lazy="select")