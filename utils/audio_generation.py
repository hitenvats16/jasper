from sqlalchemy.orm import Session
from typing import List, Union, Dict, Any
from services.rate_service import RateService
from schemas.book import ChapterData
from utils.text import count_tokens
from services.credit_service import CreditService
from models.audio_generation_job import AudioGenerationJob
from models.job_status import JobStatus

def estimate_job_cost(db: Session, chapters: List[ChapterData], user_id: int) -> Dict[str, Any]:
    """Estimate the cost of a voice generation job"""
    rate = RateService.get_user_rate_value(db=db, user_id=user_id)
    total_tokens = 0
    for chapter in chapters:
        if isinstance(chapter, ChapterData):
            total_tokens += count_tokens(chapter.content)
        else:
            total_tokens += count_tokens(chapter.get("content", ""))
    return {
        "total_tokens": total_tokens,
        "total_cost": total_tokens * rate
    }

def can_user_afford_job(db: Session, job_estimate: dict, user_id: int) -> bool:
    """Check if a user can afford a voice generation job"""
    user_credit = CreditService.get_or_create_user_credit(db, user_id)
    
    user_credit = user_credit.balance
    # Get processing or in queue jobs and sum up credits
    
    processing_jobs = db.query(AudioGenerationJob).filter(
        AudioGenerationJob.user_id == user_id,
        AudioGenerationJob.status.in_([JobStatus.PROCESSING, JobStatus.QUEUED])
    ).all()

    total_credits = sum([job.total_cost for job in processing_jobs]) + job_estimate["total_cost"]
    return user_credit >= total_credits