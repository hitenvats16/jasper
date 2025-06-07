from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.credit import TransactionType

class CreditTransactionRead(BaseModel):
    id: int
    type: TransactionType
    amount: float
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreditRead(BaseModel):
    balance: float
    updated_at: datetime
    transactions: Optional[List[CreditTransactionRead]] = None

    class Config:
        from_attributes = True

class AddCreditRequest(BaseModel):
    amount: float
    description: Optional[str] = None 