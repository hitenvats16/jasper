from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from schemas.rate import RateCreate, RateRead
from services.rate_service import RateService
from typing import List

router = APIRouter(prefix="/rates", tags=["Rates"])

def is_admin():
    # TODO: Implement real admin check
    return True

@router.post("/", response_model=RateRead, summary="Create a new service rate")
def create_rate(
    rate_in: RateCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin),
):
    if not admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    rate = RateService.create_rate(db, rate_in)
    return rate

@router.get("/", response_model=List[RateRead], summary="List all service rates")
def list_rates(
    db: Session = Depends(get_db),
):
    return RateService.list_rates(db) 