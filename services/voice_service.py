from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc, asc
from models.voice import Voice
from models.default_voice import DefaultVoice
from utils.message_publisher import message_publisher
from core.config import settings
from typing import List, Optional
from schemas.voice import VoiceFilters, VoiceListResponse
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class VoiceService:
    """Service class for managing voice operations including seeding default voices."""
    
    @staticmethod
    def seed_default_voices_for_user(db: Session, user_id: int) -> List[Voice]:
        """
        Seed default voices marked as public from default_voice table into voice table for a new user.
        
        Args:
            db: Database session
            user_id: ID of the user to seed voices for
            
        Returns:
            List[Voice]: List of created voice objects
        """
        try:
            # Get all public default voices
            default_voices = db.query(DefaultVoice).filter(
                DefaultVoice.is_public == True
            ).all()
            
            if not default_voices:
                logger.info(f"No public default voices found for user {user_id}")
                return []
            
            created_voices = []
            
            for default_voice in default_voices:
                # Create voice record for the user
                voice = Voice(
                    name=default_voice.name,
                    description=default_voice.description,
                    s3_key=default_voice.s3_key,
                    user_id=user_id,
                    voice_metadata={
                        "source": "default_voice",
                        "default_voice_id": default_voice.id,
                        "seeded_at": datetime.utcnow().isoformat(),
                    },
                    is_default=True
                )
                db.add(voice)
                created_voices.append(voice)
            
            db.commit()
            logger.info(f"Successfully seeded {len(created_voices)} default voices for user {user_id}")
            return created_voices
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to seed default voices for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_voices(
        db: Session,
        user_id: int,
        filters: VoiceFilters
    ) -> VoiceListResponse:
        """
        Get filtered, sorted, and paginated list of voices for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            filters: Filter and sort parameters
            
        Returns:
            VoiceListResponse: Paginated list of voices with metadata
        """
        # Start with base query
        query = db.query(Voice).filter(
            Voice.user_id == user_id,
            Voice.is_deleted == False
        )
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Voice.name.ilike(search_term),
                    Voice.description.ilike(search_term)
                )
            )
        
        # Filter by default/custom voices
        if filters.is_default is not None:
            query = query.filter(Voice.is_default == filters.is_default)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        sort_column = getattr(Voice, filters.sort_by.value)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)
        
        # Execute query
        voices = query.all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / filters.page_size)
        
        return VoiceListResponse(
            items=voices,
            total=total_count,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages
        )
    
    @staticmethod
    def get_voice_by_id(db: Session, voice_id: int, user_id: int) -> Optional[Voice]:
        """
        Get a specific voice by ID, ensuring it belongs to the user.
        
        Args:
            db: Database session
            voice_id: ID of the voice
            user_id: ID of the user (for ownership verification)
            
        Returns:
            Optional[Voice]: Voice object if found and owned by user, None otherwise
        """
        return db.query(Voice).filter(
            Voice.id == voice_id,
            Voice.user_id == user_id,
            Voice.is_deleted == False
        ).first() 