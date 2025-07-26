from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from core.dependencies import get_current_user
from models.user import User
from models.project import Project
from models.audio_generation_job import AudioGenerationJob
from models.job_status import JobStatus
from schemas.voice_generation import AudioGenerationResponse, AudioGenerationRequest
from utils.s3 import upload_file_to_s3
from typing import Optional
import json
from uuid import uuid4
from datetime import datetime, timezone
from io import BytesIO

router = APIRouter()

@router.post(
    "/audiobook/{project_id}/{voice_id}",
    response_model=AudioGenerationResponse,
    summary="Generate audiobook from processed book data",
    description="""
    Create an audio generation job for a book in a project using the specified voice.
    The book data should be in the processed format (BookDataProcessingJob).
    """
)
async def generate_audiobook(
    project_id: int,
    voice_id: int,
    request: AudioGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project exists and belongs to user
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.is_deleted == False
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )

    # Generate unique S3 key for the processed data
    s3_key = f"preprocessed_audiobook/{current_user.id}_{project_id}_{uuid4()}.json"
    
    try:
        # Convert book data to JSON and create a file-like object
        book_data_json = request.book_data.model_dump_json()
        file_obj = BytesIO(book_data_json.encode('utf-8'))
        
        # Upload to S3
        upload_file_to_s3(
            file_obj=file_obj,
            filename=s3_key.split('/')[-1],
            custom_key=s3_key
        )
        
        # Create audio generation job
        job = AudioGenerationJob(
            user_id=current_user.id,
            project_id=project_id,
            voice_id=voice_id,
            input_data_s3_key=s3_key,
            status=JobStatus.QUEUED,
            job_metadata=request.model_dump(exclude={'book_data'}),
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        return AudioGenerationResponse(
            job_id=job.id,
            status=job.status,
            created_at=job.created_at,
            s3_url=job.s3_url
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audio generation job: {str(e)}"
        ) 