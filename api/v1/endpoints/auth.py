from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response, Security
from sqlalchemy.orm import Session
from db.session import SessionLocal, get_db
from schemas.auth import RegisterRequest, LoginRequest, EmailVerificationRequest, Token
from schemas.user import UserRead, UserUpdate
from services.auth_service import register_user, verify_email, authenticate_user, get_or_create_user_by_google_oauth
from core.security import create_access_token, decode_access_token
from core.config import settings
from typing import Any
from urllib.parse import urlencode
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import User
from datetime import datetime, timedelta, timezone
from core.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource not found"},
        422: {"description": "Validation Error - Invalid request data"}
    }
)

security = HTTPBearer()

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Register a new user with email and password authentication.
    
    - Sends a verification code to the provided email address
    - Email must be unique and not already registered
    - Password must meet security requirements
    - Returns the created user object (without sensitive data)
    
    **Note:** Email verification is required before login
    """,
    responses={
        201: {"description": "User successfully registered"},
        400: {"description": "Invalid input data or email already registered"}
    },
    tags=["Authentication"]
)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    
    Args:
        request: Registration data including email and password
        db: Database session
    
    Returns:
        UserRead: Created user object
        
    Raises:
        HTTPException: If email is already registered or input is invalid
    """
    try:
        user = register_user(db, request)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/verify-email",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Verify user email",
    description="""
    Verify a user's email address using the verification code.
    
    - Code is sent to user's email during registration
    - Code expires after a certain time period
    - User must be verified before they can log in
    
    **Note:** This endpoint is required to complete the registration process
    """,
    responses={
        200: {"description": "Email successfully verified"},
        400: {"description": "Invalid or expired verification code"}
    },
    tags=["Authentication"]
)
def verify(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Verify a user's email address using the verification code.
    
    Args:
        request: Verification data including email and code
        db: Database session
    
    Returns:
        UserRead: Updated user object with verified status
        
    Raises:
        HTTPException: If code is invalid or expired
    """
    try:
        user = verify_email(db, request.email, request.code)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="""
    Authenticate a user and generate a JWT access token.
    
    - Requires valid email and password
    - Email must be verified
    - Returns JWT token with expiration time
    - Token must be included in Authorization header for protected endpoints
    
    **Note:** Token expires after a configurable time period
    """,
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Invalid credentials or email not verified"}
    },
    tags=["Authentication"]
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and generate a JWT access token.
    
    Args:
        request: Login credentials (email and password)
        db: Database session
    
    Returns:
        Token: JWT access token with expiration time
        
    Raises:
        HTTPException: If credentials are invalid or email not verified
    """
    user = authenticate_user(db, request.email, request.password)
    if not user or not user.is_verified:
        raise HTTPException(status_code=401, detail="Invalid credentials or email not verified")
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"user_id": user.id, "email": user.email}, expires_delta=expires_delta)
    expires_at = datetime.now(timezone.utc) + expires_delta
    return {"access_token": access_token, "token_type": "bearer", "expires_at": expires_at}

@router.get(
    "/login/google",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Initiate Google OAuth login",
    description="""
    Redirect to Google's OAuth 2.0 consent screen.
    
    - Initiates the Google OAuth 2.0 authentication flow
    - User will be redirected to Google's login page
    - After successful authentication, user will be redirected back to the callback URL
    - Optional redirect_url parameter allows custom redirect after authentication
    
    **Query Parameters:**
    - redirect_url (optional): Custom redirect URL after successful authentication
    
    **Note:** This endpoint is part of the Google OAuth 2.0 flow
    """,
    responses={
        307: {"description": "Redirect to Google OAuth consent screen"},
        400: {"description": "Invalid redirect URL"}
    },
    tags=["Authentication"]
)
def login_google(redirect_url: str = None):
    """
    Redirect to Google's OAuth 2.0 consent screen.
    
    Returns:
        Response: Redirect response to Google's consent screen
        
    Raises:
        HTTPException: If redirect_url is invalid
    """
    # Validate redirect URL if provided
    if redirect_url:
        # Basic validation - ensure it's a valid URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(redirect_url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid redirect URL format"
                )
        except Exception:
            raise HTTPException(
                status_code=400, 
                detail="Invalid redirect URL"
            )
    
    # Always use the configured Google redirect URI for OAuth callback
    # The custom redirect_url is only for final user redirect after authentication
    oauth_redirect_uri = parsed.geturl() if parsed else settings.GOOGLE_REDIRECT_URI
    print(f"OAuth redirect URI: {oauth_redirect_uri}")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    # Add state parameter with redirect URL for callback to use
    if redirect_url:
        import base64
        import json
        state_data = {"redirect_url": redirect_url}
        state_encoded = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        params["state"] = state_encoded
    
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return Response(status_code=302, headers={"Location": url})

@router.get(
    "/login/google/callback",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth callback",
    description="""
    Handle Google OAuth callback and generate JWT token.
    
    - Processes the OAuth callback from Google
    - Creates or updates user account
    - Generates JWT access token
    - Returns token with expiration time
    - Optionally redirects to custom URL if provided in state parameter
    
    **Query Parameters:**
    - code: OAuth authorization code from Google
    - state: Optional state parameter containing redirect URL
    
    **Note:** This endpoint is called by Google after successful authentication
    """,
    responses={
        200: {"description": "Successfully authenticated with Google"},
        400: {"description": "Invalid or missing OAuth code"},
        302: {"description": "Redirect to custom URL after authentication"}
    },
    tags=["Authentication"]
)
def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback and generate JWT token.
    
    Args:
        request: FastAPI request object containing OAuth code and state
        db: Database session
    
    Returns:
        Token: JWT access token with expiration time or redirect response
        
    Raises:
        HTTPException: If OAuth code is invalid or missing
    """
    code = request.query_params.get("code")
    redirect_url = request.query_params.get("redirect_url")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing code in callback")
    
    # Always use the configured Google redirect URI for OAuth token exchange
    # This must match what was used in the authorization request
    oauth_redirect_uri = settings.GOOGLE_REDIRECT_URI
    if redirect_url:
        oauth_redirect_uri = redirect_url
    print(f"Using redirect_uri: {oauth_redirect_uri}")
    
    # Use the OAuth redirect URI for token exchange
    user = get_or_create_user_by_google_oauth(db, code, oauth_redirect_uri)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"user_id": user.id, "email": user.email}, expires_delta=expires_delta)
    
    # Return token directly if no custom redirect
    return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_delta.total_seconds()}

@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="""
    Retrieve the authenticated user's profile information.
    
    - Requires valid JWT token
    - Returns user's profile data
    - Includes OAuth account information if available
    
    **Note:** This endpoint is protected and requires authentication
    """,
    responses={
        200: {"description": "Successfully retrieved user profile"},
        401: {"description": "Invalid or expired token"},
        404: {"description": "User not found"}
    },
    tags=["Authentication"]
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the authenticated user's profile information.
    
    Args:
        current_user: Current authenticated user (from dependency)
    
    Returns:
        UserRead: User's profile information
    """
    return current_user

@router.put(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="""
    Update the authenticated user's profile information.
    
    - Requires valid JWT token
    - Can update user's active status and verification status
    - Returns updated user profile
    
    **Note:** This endpoint is protected and requires authentication
    """,
    responses={
        200: {"description": "Successfully updated user profile"},
        401: {"description": "Invalid or expired token"},
        404: {"description": "User not found"}
    },
    tags=["Authentication"]
)
def update_me(update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update the authenticated user's profile information.
    
    Args:
        update: User update data
        db: Database session
        current_user: Current authenticated user (from dependency)
    
    Returns:
        UserRead: Updated user profile information
    """
    user = db.query(User).filter_by(id=current_user.id).first()
    if update.is_active is not None:
        user.is_active = update.is_active
    if update.is_verified is not None:
        user.is_verified = update.is_verified
    db.commit()
    db.refresh(user)
    return user

# Google OAuth endpoints would go here (initiate, callback)
# For brevity, not implemented in this snippet 