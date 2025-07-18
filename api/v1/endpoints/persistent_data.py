from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from schemas.persistent_data import PersistentDataCreate, PersistentDataRead
from services.persistent_data_service import PersistentDataService
from models.user import User
from db.session import get_db
from core.dependencies import get_current_user
from typing import Optional

router = APIRouter(
    prefix="/persistent-data",
    tags=["Persistent Data"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource not found"},
        422: {"description": "Validation Error - Invalid request data"}
    }
)

@router.get(
    "/{key}",
    response_model=PersistentDataRead,
    status_code=status.HTTP_200_OK,
    summary="Get persistent data by key",
    description="""
    Retrieve persistent data for the authenticated user by key.
    
    - Requires authentication
    - Returns data associated with the provided key
    - Returns 404 if no data found for the key
    
    **Note:** Each user's data is isolated and can only be accessed by that user
    """,
    responses={
        200: {"description": "Successfully retrieved data"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        404: {"description": "Data not found for the given key"}
    }
)
def get_data(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get persistent data by key for the authenticated user.
    
    Args:
        key: The key to retrieve data for
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        PersistentDataRead: The retrieved data
        
    Raises:
        HTTPException: If data not found
    """
    data = PersistentDataService.get_data(db, current_user.id, key)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for key: {key}"
        )
    return data

@router.put(
    "/{key}",
    response_model=PersistentDataRead,
    status_code=status.HTTP_200_OK,
    summary="Create or update persistent data",
    description="""
    Create or update persistent data for the authenticated user.
    
    - Requires authentication
    - Creates new data if key doesn't exist
    - Updates existing data if key exists
    - Returns the created/updated data
    
    **Note:** Each user's data is isolated and can only be modified by that user
    """,
    responses={
        200: {"description": "Successfully created/updated data"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        422: {"description": "Validation Error - Invalid data format"}
    }
)
def upsert_data(
    key: str,
    data_in: PersistentDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update persistent data for the authenticated user.
    
    Args:
        key: The key to store data under
        data_in: Data to store
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        PersistentDataRead: The created/updated data
    """
    # Ensure the key in the path matches the key in the data
    if key != data_in.key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key in URL must match key in request body"
        )
    
    return PersistentDataService.upsert_data(db, current_user.id, data_in) 

@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete persistent data",
    description="""
    Permanently delete persistent data for the authenticated user.
    
    - Requires authentication
    - Permanently deletes data associated with the provided key
    - Returns 204 on successful deletion
    - Returns 404 if no data found for the key
    
    **Warning:** This is a permanent deletion and cannot be undone
    
    **Note:** Each user's data is isolated and can only be deleted by that user
    """,
    responses={
        204: {"description": "Successfully deleted data"},
        401: {"description": "Unauthorized - Invalid or expired token"},
        404: {"description": "Data not found for the given key"}
    }
)
def delete_data(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete persistent data by key for the authenticated user.
    
    Args:
        key: The key of the data to delete
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        None
        
    Raises:
        HTTPException: If data not found
    """
    deleted = PersistentDataService.delete_data(db, current_user.id, key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for key: {key}"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT) 