from fastapi import Request, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import decode_access_token
from models.user import User
from db.session import SessionLocal
from typing import Optional, Callable
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def timing_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to log request timing information.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in the chain
        
    Returns:
        Response: FastAPI response object
    """
    start_time = time.time()
    logger.info(f"Request started: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request completed in {process_time:.2f}s: {request.method} {request.url}")
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed after {process_time:.2f}s: {request.method} {request.url} - Error: {str(e)}")
        raise

def get_current_user_from_request(request: Request) -> Optional[User]:
    """Get the current user from the request for middleware purposes"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            return None
            
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(id=payload["user_id"], is_deleted=False).first()
            return user
        finally:
            db.close()
    except Exception:
        return None

def require_auth():
    """Decorator to require authentication for a route"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            user = get_current_user_from_request(request)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
            
            # Add user to request state
            request.state.user = user
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def public():
    """Decorator to mark a route as public (no authentication required)"""
    def decorator(func):
        func.is_public = True
        return func
    return decorator 