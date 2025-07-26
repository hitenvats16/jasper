from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class VoiceSortField(str, Enum):
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class VoiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    voice_metadata: Optional[Dict[str, Any]] = None
    is_deleted: bool = False
    is_default: bool = False

class VoiceCreate(VoiceBase):
    pass

class VoiceUpdate(VoiceBase):
    name: Optional[str] = None
    description: Optional[str] = None
    is_deleted: Optional[bool] = None

class VoiceRead(VoiceBase):
    id: int
    s3_key: str
    s3_public_link: HttpUrl
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VoiceFilters(BaseModel):
    """Query parameters for filtering voices"""
    search: Optional[str] = Field(None, description="Search term for name or description")
    is_default: Optional[bool] = Field(None, description="Filter default/custom voices")
    sort_by: Optional[VoiceSortField] = Field(VoiceSortField.CREATED_AT, description="Field to sort by")
    sort_order: Optional[SortOrder] = Field(SortOrder.DESC, description="Sort order (asc/desc)")
    page: Optional[int] = Field(1, ge=1, description="Page number")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="Items per page")

class VoiceListResponse(BaseModel):
    """Response model for paginated voice list"""
    items: List[VoiceRead]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True 