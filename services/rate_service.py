from sqlalchemy.orm import Session
from models.rate import Rate
from typing import List, Optional
from schemas.rate import RateCreate

class RateService:
    @staticmethod
    def create_rate(db: Session, rate_in: RateCreate) -> Rate:
        rate = Rate(**rate_in.dict())
        db.add(rate)
        db.commit()
        db.refresh(rate)
        return rate

    @staticmethod
    def get_rate_by_slug(db: Session, slug: str) -> Optional[Rate]:
        return db.query(Rate).filter_by(slug=slug).first()

    @staticmethod
    def list_rates(db: Session) -> List[Rate]:
        return db.query(Rate).all() 