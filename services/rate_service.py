from sqlalchemy.orm import Session
from models.rate import Rate
from typing import List
from core.config import settings

class RateService:
    @staticmethod
    def get_user_rate_value(db: Session, user_id: int) -> float:
        rate = db.query(Rate).filter(Rate.user_id == user_id).first()
        return rate.values if rate else settings.DEFAULT_PER_TOKEN_RATE