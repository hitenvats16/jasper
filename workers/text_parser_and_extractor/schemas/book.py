from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ContentType(str, Enum):
    HEADLINE = "headline"
    PARAGRAPH = "paragraph"
    EMPTY = "empty"
    FALLBACK = "fallback"
    CHAPTER_TITLE = "chapter_title"
    
    @staticmethod
    def get_all_values():
        return [content_type.value for content_type in ContentType]


class Section(BaseModel):
    section_id: str = Field(description="Unique ID for the section.")
    content: str = Field(description="The extracted textual content of the section.")
    content_type: ContentType = Field(default=ContentType.PARAGRAPH, description="Type of content in the book section.")
    level: Optional[int] = Field(
        None, description="Heading level if content_type is 'headline'."
    )


class Chapter(BaseModel):
    chapter_id: str = Field(description="Unique ID for the chapter.")
    title: Optional[str] = Field(None, description="Title of the chapter.")
    sections: List[Section] = Field(
        default_factory=list, description="List of sections within the chapter."
    )


class BookStructure(BaseModel):
    book_id: str = Field(description="Unique ID for the book.")
    title: Optional[str] = Field(None, description="Title of the book.")
    author: Optional[str] = Field(None, description="Author of the book.")
    chapters: List[Chapter] = Field(
        default_factory=list, description="List of chapters in the book."
    )
