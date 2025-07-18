from sqlalchemy.orm import Session
from models.persistent_data import PersistentData
from schemas.persistent_data import PersistentDataCreate
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

class PersistentDataService:
    @staticmethod
    def get_data(db: Session, user_id: int, key: str) -> Optional[PersistentData]:
        """
        Get persistent data by key for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            key: Data key
            
        Returns:
            Optional[PersistentData]: The persistent data if found, None otherwise
        """
        return db.query(PersistentData).filter(
            PersistentData.user_id == user_id,
            PersistentData.key == key
        ).first()

    @staticmethod
    def upsert_data(
        db: Session,
        user_id: int,
        data_in: PersistentDataCreate
    ) -> PersistentData:
        """
        Create or update persistent data for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            data_in: Data to store
            
        Returns:
            PersistentData: Created or updated persistent data
        """
        # Check if data exists
        existing_data = PersistentDataService.get_data(db, user_id, data_in.key)
        
        if existing_data:
            # Update existing data
            existing_data.data = data_in.data
            db.add(existing_data)
            db.commit()
            db.refresh(existing_data)
            return existing_data
        
        # Create new data
        db_data = PersistentData(
            user_id=user_id,
            key=data_in.key,
            data=data_in.data
        )
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        return db_data

    @staticmethod
    def delete_data(db: Session, user_id: int, key: str) -> bool:
        """
        Permanently delete persistent data by key for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            key: Data key
            
        Returns:
            bool: True if data was deleted, False if not found
        """
        result = db.query(PersistentData).filter(
            PersistentData.user_id == user_id,
            PersistentData.key == key
        ).delete()
        
        db.commit()
        return result > 0 