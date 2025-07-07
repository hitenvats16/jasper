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
    Table,
)
from sqlalchemy.orm import relationship
from db.session import Base
from core.config import settings

# Association table for linking books to projects (optional relationship)
book_project_association = Table(
    'book_project_association',
    Base.metadata,
    Column('book_id', Integer, ForeignKey('book.id'), primary_key=True),
    Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
)

class Book(Base):
    __tablename__ = "book"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    s3_key = Column(String, nullable=True)  # S3 key for file storage
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # User who generated
    data = Column(JSON, nullable=True)  # JSON data storage
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="books", lazy="joined")
    # Optional relationship with projects through association table
    projects = relationship("Project", secondary=book_project_association, back_populates="books", lazy="joined") 

    @property
    def s3_public_link(self):
        """Returns the public AWS S3 URL for this voice file."""
        return f"{settings.AWS_PUBLIC_URL}/{self.s3_key}"