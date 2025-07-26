from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class PersistentDataBase(BaseModel):
    key: str
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PersistentDataCreate(PersistentDataBase):
    pass

class PersistentDataRead(PersistentDataBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 