from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class PersistentDataBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, description="Unique key for the data")
    data: Dict[str, Any] = Field(..., description="JSON data to store")

class PersistentDataCreate(PersistentDataBase):
    pass

class PersistentDataRead(PersistentDataBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 