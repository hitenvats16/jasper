from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response, Security
from sqlalchemy.orm import Session
from db.session import SessionLocal
from schemas.auth import RegisterRequest, LoginRequest, EmailVerificationRequest, Token
from schemas.user import UserRead, UserUpdate
from services.auth_service import register_user, verify_email, authenticate_user, get_or_create_user_by_google_oauth
from core.security import create_access_token, decode_access_token
from core.config import settings
from typing import Any
from urllib.parse import urlencode
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import User
from datetime import datetime, timedelta, UTC

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

security = HTTPBearer()

def get_current_user(db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter_by(id=payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with email/password",
    description="Register a new user using email and password. Sends a verification code to the user's email.",
    tags=["auth"],
)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password. Sends a verification code to the user's email address.
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
    description="Verify a user's email address using the code sent to their email.",
    tags=["auth"],
)
def verify(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Verify a user's email address using the code sent to their email.
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
    description="Authenticate a user using email and password. Returns a JWT access token.",
    tags=["auth"],
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user using email and password. Returns a JWT access token if credentials are valid and email is verified.
    """
    user = authenticate_user(db, request.email, request.password)
    if not user or not user.is_verified:
        raise HTTPException(status_code=401, detail="Invalid credentials or email not verified")
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"user_id": user.id, "email": user.email}, expires_delta=expires_delta)
    expires_at = datetime.now(UTC) + expires_delta
    return {"access_token": access_token, "token_type": "bearer", "expires_at": expires_at}

@router.get(
    "/login/google",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Initiate Google OAuth login",
    description="Redirects the user to Google's OAuth 2.0 consent screen.",
    tags=["auth"],
)
def login_google():
    """
    Redirect the user to Google's OAuth 2.0 consent screen to initiate Google login.
    """
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    print(url)
    return Response(status_code=302, headers={"Location": url})

@router.get(
    "/login/google/callback",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth callback",
    description="Handles the callback from Google OAuth, exchanges code for tokens, and returns a JWT access token.",
    tags=["auth"],
)
def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the callback from Google OAuth, exchanges the code for tokens, fetches user info, creates or updates the user, and returns a JWT access token.
    """
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code in callback")
    user = get_or_create_user_by_google_oauth(db, code, settings.GOOGLE_REDIRECT_URI)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"user_id": user.id, "email": user.email}, expires_delta=expires_delta)
    expires_at = datetime.now(UTC) + expires_delta
    return {"access_token": access_token, "token_type": "bearer", "expires_at": expires_at}

@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user info",
    description="Get the authenticated user's information.",
    tags=["auth"],
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the authenticated user's information.
    """
    return current_user

@router.put(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user info",
    description="Update the authenticated user's information.",
    tags=["auth"],
)
def update_me(update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update the authenticated user's information.
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