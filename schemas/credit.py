from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.credit import TransactionType

class CreditTransactionRead(BaseModel):
    id: int
    type: TransactionType
    amount: float
    description: Optional[str]
    is_deleted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreditRead(BaseModel):
    balance: float
    is_deleted: bool = False
    updated_at: datetime
    transactions: Optional[List[CreditTransactionRead]] = None

    class Config:
        from_attributes = True