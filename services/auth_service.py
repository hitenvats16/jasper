from sqlalchemy.orm import Session
from models.user import User, OAuthAccount
from models.config import Config
from schemas.user import UserCreate
from core.security import hash_password, verify_password
from typing import Optional
from utils.email import send_email_async
from core.config import settings
from services.voice_service import VoiceService
from services.credit_service import CreditService
from models.rate import Rate
from clients.fal import FalModels
from workers.audio_generation.enums import SilencingStrategies
import random, string
import httpx
from datetime import datetime, timezone, timedelta
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# In-memory store for verification codes (for demo; use Redis in prod)
verification_codes = {}

def create_default_config(db: Session, user_id: int):
    """Create a default config for a new user."""
    try:
        default_config = Config(
            user_id=user_id,
            tts_model=FalModels.CHATTERBOX_TEXT_TO_SPEECH.value,
            tts_model_data={},
            silence_strategy=SilencingStrategies.FIXED_SILENCING.value,
            silence_data={"value": 300},
            sample_rate=24000
        )
        db.add(default_config)
        db.commit()
        db.refresh(default_config)
        logger.info(f"Successfully created default config for user {user_id}")
        return default_config
    except Exception as e:
        logger.error(f"Failed to create default config for user {user_id}: {str(e)}")
        # Don't fail user registration if config creation fails
        return None

def register_user(db: Session, user_in: UserCreate):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise ValueError("User already exists")
    hashed_pw = hash_password(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Seed default voices for the new user
    try:
        VoiceService.seed_default_voices_for_user(db, user.id)
        logger.info(f"Successfully seeded default voices for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to seed default voices for user {user.id}: {str(e)}")
        # Don't fail user registration if voice seeding fails
    
    # Create default config for the new user
    try:
        create_default_config(db, user.id)
        logger.info(f"Successfully created default config for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to create default config for user {user.id}: {str(e)}")
        # Don't fail user registration if config creation fails
    
    # Add default credits to the new user
    try:
        CreditService.add_credit(
            db, 
            user.id, 
            settings.DEFAULT_USER_CREDITS,
            f"Welcome bonus - New user registration"
        )
        logger.info(f"Successfully added {settings.DEFAULT_USER_CREDITS} default credits for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to add default credits for user {user.id}: {str(e)}")
        # Don't fail user registration if credit addition fails
    
    # Create default rate for the new user
    try:
        rate = Rate(
            user_id=user.id,
            values=settings.DEFAULT_PER_TOKEN_RATE
        )
        db.add(rate)
        db.commit()
        logger.info(f"Successfully created default rate for user {user.id}: {settings.DEFAULT_PER_TOKEN_RATE}")
    except Exception as e:
        logger.error(f"Failed to create default rate for user {user.id}: {str(e)}")
        # Don't fail user registration if rate creation fails
    
    # Generate and send verification code
    code = ''.join(random.choices(string.digits, k=6))
    verification_codes[user.email] = code
    # Send email (async)
    subject = "Verify your email"
    body = f"Your verification code is: {code}"
    # In production, use background tasks
    import asyncio; asyncio.create_task(send_email_async(subject, user.email, body))
    return user

def verify_email(db: Session, email: str, code: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")
    if verification_codes.get(email) != code:
        raise ValueError("Invalid verification code")
    user.is_verified = True
    db.commit()
    db.refresh(user)
    verification_codes.pop(email, None)
    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_or_create_user_by_google_oauth(db: Session, code: str, redirect_uri: str):
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async def fetch_tokens():
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)
            resp.raise_for_status()
            return resp.json()
    import asyncio
    token_data = asyncio.run(fetch_tokens())
    access_token = token_data["access_token"]
    id_token = token_data.get("id_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None

    # Fetch user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    async def fetch_userinfo():
        async with httpx.AsyncClient() as client:
            resp = await client.get(userinfo_url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    userinfo = asyncio.run(fetch_userinfo())
    google_id = userinfo["id"]
    email = userinfo["email"]
    verified = userinfo.get("verified_email", False)
    print(userinfo)
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, is_verified=verified, is_active=True, first_name=userinfo.get("given_name"), last_name=userinfo.get("family_name"), profile_picture=userinfo.get("picture"))
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Seed default voices for the new OAuth user
        try:
            VoiceService.seed_default_voices_for_user(db, user.id)
            logger.info(f"Successfully seeded default voices for OAuth user {user.id}")
        except Exception as e:
            logger.error(f"Failed to seed default voices for OAuth user {user.id}: {str(e)}")
            # Don't fail OAuth user creation if voice seeding fails
        
        # Create default config for the new OAuth user
        try:
            create_default_config(db, user.id)
            logger.info(f"Successfully created default config for OAuth user {user.id}")
        except Exception as e:
            logger.error(f"Failed to create default config for OAuth user {user.id}: {str(e)}")
            # Don't fail OAuth user creation if config creation fails
        
        # Add default credits to the new OAuth user
        try:
            CreditService.add_credit(
                db, 
                user.id, 
                settings.DEFAULT_USER_CREDITS,
                f"Welcome bonus - OAuth user registration"
            )
            logger.info(f"Successfully added {settings.DEFAULT_USER_CREDITS} default credits for OAuth user {user.id}")
        except Exception as e:
            logger.error(f"Failed to add default credits for OAuth user {user.id}: {str(e)}")
            # Don't fail OAuth user creation if credit addition fails
        
        # Create default rate for the new OAuth user
        try:
            rate = Rate(
                user_id=user.id,
                values=settings.DEFAULT_PER_TOKEN_RATE
            )
            db.add(rate)
            db.commit()
            logger.info(f"Successfully created default rate for OAuth user {user.id}: {settings.DEFAULT_PER_TOKEN_RATE}")
        except Exception as e:
            logger.error(f"Failed to create default rate for OAuth user {user.id}: {str(e)}")
            # Don't fail OAuth user creation if rate creation fails
    # Find or create OAuthAccount
    oauth = db.query(OAuthAccount).filter_by(user_id=user.id, provider="google").first()
    if not oauth:
        oauth = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        db.add(oauth)
    else:
        oauth.access_token = access_token
        oauth.refresh_token = refresh_token
        oauth.expires_at = expires_at
    db.commit()
    return user 