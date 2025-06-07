from sqlalchemy.orm import Session
from models.credit import UserCredit, CreditTransaction, TransactionType
from models.user import User
from typing import Optional

class CreditService:
    @staticmethod
    def get_or_create_user_credit(db: Session, user_id: int) -> UserCredit:
        credit = db.query(UserCredit).filter_by(user_id=user_id).first()
        if not credit:
            credit = UserCredit(user_id=user_id, balance=0.0)
            db.add(credit)
            db.commit()
            db.refresh(credit)
        return credit

    @staticmethod
    def add_credit(db: Session, user_id: int, amount: float, description: Optional[str] = None) -> UserCredit:
        credit = CreditService.get_or_create_user_credit(db, user_id)
        credit.balance += amount
        db.add(credit)
        db.commit()
        db.refresh(credit)
        # Log transaction
        txn = CreditTransaction(user_credit_id=credit.id, type=TransactionType.ADD, amount=amount, description=description)
        db.add(txn)
        db.commit()
        return credit

    @staticmethod
    def deduct_credit(db: Session, user_id: int, amount: float, description: Optional[str] = None) -> UserCredit:
        credit = CreditService.get_or_create_user_credit(db, user_id)
        if credit.balance < amount:
            raise ValueError("Insufficient credits")
        credit.balance -= amount
        db.add(credit)
        db.commit()
        db.refresh(credit)
        # Log transaction
        txn = CreditTransaction(user_credit_id=credit.id, type=TransactionType.DEDUCT, amount=amount, description=description)
        db.add(txn)
        db.commit()
        return credit

    @staticmethod
    def get_balance(db: Session, user_id: int) -> float:
        credit = CreditService.get_or_create_user_credit(db, user_id)
        return credit.balance

    @staticmethod
    def get_transactions(db: Session, user_id: int):
        credit = CreditService.get_or_create_user_credit(db, user_id)
        return credit.transactions 