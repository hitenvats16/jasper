from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db.session import SessionLocal
from models.user import User
from core.security import decode_access_token
from typing import Optional, Generator
import time
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    start_time = time.time()
    logger.info("🔄 Getting database session...")
    
    db = SessionLocal()
    try:
        db_time = time.time() - start_time
        logger.info(f"✅ Database session acquired in {db_time:.3f}s")
        yield db
    finally:
        close_start = time.time()
        db.close()
        close_time = time.time() - close_start
        logger.info(f"🔄 Database session closed in {close_time:.3f}s")

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency for getting the current authenticated user.
    Raises 401 if token is invalid or expired, 404 if user not found.
    """
    start_time = time.time()
    logger.info("🔐 Starting user authentication...")
    
    try:
        token = credentials.credentials
        
        # Time token validation
        token_start = time.time()
        payload = decode_access_token(token)
        token_time = time.time() - token_start
        logger.info(f"🔑 Token validation took {token_time:.3f}s")
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Time database query with timeout
        db_start = time.time()
        try:
            # Use a more efficient query with timeout
            user = db.query(User).filter(User.id == payload["user_id"]).first()
            db_time = time.time() - db_start
            logger.info(f"📊 Database user query took {db_time:.3f}s")
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        except Exception as e:
            db_time = time.time() - db_start
            logger.error(f"❌ Database user query failed after {db_time:.3f}s: {str(e)}")
            raise
        
        # Add user to request state for easy access
        request.state.user = user
        
        total_time = time.time() - start_time
        logger.info(f"✅ User authentication completed in {total_time:.3f}s")
        return user
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"❌ User authentication failed after {total_time:.3f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Dependency for getting the current user if authenticated, None otherwise.
    Useful for endpoints that can work with or without authentication.
    """
    start_time = time.time()
    logger.info("🔐 Starting optional user authentication...")
    
    if not credentials:
        logger.info("🔄 No credentials provided, skipping authentication")
        return None
    
    try:
        token = credentials.credentials
        
        # Time token validation
        token_start = time.time()
        payload = decode_access_token(token)
        token_time = time.time() - token_start
        logger.info(f"🔑 Optional token validation took {token_time:.3f}s")
        
        if not payload:
            logger.info("🔄 Invalid token, returning None")
            return None
        
        # Time database query with timeout
        db_start = time.time()
        try:
            # Use a more efficient query
            user = db.query(User).filter(User.id == payload["user_id"]).first()
            db_time = time.time() - db_start
            logger.info(f"📊 Optional database user query took {db_time:.3f}s")
        except Exception as e:
            db_time = time.time() - db_start
            logger.error(f"❌ Optional database user query failed after {db_time:.3f}s: {str(e)}")
            return None
        
        if user:
            request.state.user = user
        
        total_time = time.time() - start_time
        logger.info(f"✅ Optional user authentication completed in {total_time:.3f}s")
        return user
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.warning(f"⚠️ Optional user authentication failed after {total_time:.3f}s: {str(e)}")
        return None

async def get_current_admin_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency for getting the current authenticated admin user.
    Raises 401 if token is invalid or expired, 403 if user is not admin.
    """
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Add user to request state for easy access
        request.state.user = user
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        ) 