from pydantic import BaseModel
from typing import Optional, Dict

class RateBase(BaseModel):
    slug: str
    name: str
    flags: Optional[Dict[str, bool]] = None
    rate: float
    currency: str = "USD"
    description: Optional[str] = None

class RateCreate(RateBase):
    pass

class RateRead(RateBase):
    id: int

    class Config:
        from_attributes = True 