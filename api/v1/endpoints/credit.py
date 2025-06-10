from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.credit import AddCreditRequest, UserCreditRead, CreditTransactionRead
from services.credit_service import CreditService
from models.user import User
from typing import List
from db.session import get_db
from core.dependencies import get_current_user

router = APIRouter(prefix="/credits", tags=["Credits"])

@router.post("/add", response_model=UserCreditRead, summary="Add credits to your account")
def add_credits(
    req: AddCreditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")
    credit = CreditService.add_credit(db, current_user.id, req.amount, req.description)
    return credit

@router.get("/balance", response_model=UserCreditRead, summary="Get your current credit balance")
def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    credit = CreditService.get_or_create_user_credit(db, current_user.id)
    return credit

@router.get("/transactions", response_model=List[CreditTransactionRead], summary="List your credit transactions")
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txns = CreditService.get_transactions(db, current_user.id)
    return txns 