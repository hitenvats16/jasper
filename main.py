from fastapi import FastAPI, Request, Depends
from api.v1.endpoints import auth
from db.session import engine, Base, init_db
import os
import uvicorn
from api.v1.endpoints import voice
from api.v1.endpoints import admin
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from api.v1.endpoints import credit_router, project_router, book_router, payment, persistent_data_router
from core.dependencies import get_optional_user
from models.user import User
import logging
import sys
from utils.message_publisher import get_rabbitmq_connection
from api.v1.endpoints import config_router, voice_generation_router
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def on_startup():
    # Check if we're in fast startup mode
    fast_startup = os.environ.get("FAST_STARTUP", "0") == "1"
    
    if fast_startup:
        logger.info("🚀 Fast startup mode - skipping heavy operations")
        return
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # Test RabbitMQ connection in a non-blocking way
    try:
        logger.info("Testing RabbitMQ connection...")
        connection = get_rabbitmq_connection()
        connection.close()
        logger.info("Successfully connected to RabbitMQ")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {str(e)}")
        logger.warning("Application will start without RabbitMQ. Some features may be limited.")
    
    # Skip LemonSqueezy sync if environment variable is set
    if os.environ.get("SKIP_LEMONSQUEEZY_SYNC", "0") == "1":
        logger.info("Skipping LemonSqueezy sync due to SKIP_LEMONSQUEEZY_SYNC=1")
        return
    
    # Make LemonSqueezy sync non-blocking - don't await it
    try:
        logger.info("Starting LemonSqueezy product sync in background...")
        import asyncio
        asyncio.create_task(sync_lemonsqueezy_products())
        logger.info("LemonSqueezy sync started in background")
    except Exception as e:
        logger.warning(f"Failed to start LemonSqueezy sync: {str(e)}")
        logger.warning("Application will continue without synced products.")

async def sync_lemonsqueezy_products():
    """Sync LemonSqueezy products"""
    try:
        logger.info("Starting LemonSqueezy product sync...")
        from services.lemonsqueezy_service import LemonSqueezyService
        from db.session import SessionLocal
        
        lemon_service = LemonSqueezyService()
        db = SessionLocal()
        
        try:
            sync_result = await lemon_service.sync_products_to_plans(db)
            logger.info(f"LemonSqueezy product sync completed: {sync_result}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to sync LemonSqueezy products: {str(e)}")
        logger.warning("Application will continue without synced products. Payment plans may not be available.")

# Initialize rate limiter with optimized settings for better performance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # Set a reasonable default limit
    storage_uri="memory://",  # Use in-memory storage for faster performance
    headers_enabled=True,
    retry_after="http-date"
)

app = FastAPI(
    title="Jasper Voice Gateway API",
    description="""
    Jasper Voice Gateway API Documentation

    Welcome to the Jasper Voice Gateway API! This API provides endpoints for voice processing, management, and analysis.

    Features:
    - Authentication: Secure user authentication with JWT tokens
    - Voice Processing: Upload and process voice samples
    - Voice Management: Create, update, and manage voice profiles
    - Asynchronous Processing: Background job processing with RabbitMQ
    - Cloud Storage: S3 integration for voice file storage

    Getting Started:
    1. Register a new account using the /auth/register endpoint
    2. Verify your email using the code sent to your inbox
    3. Login to get your access token
    4. Use the token in the Authorization header for protected endpoints

    Authentication:
    All protected endpoints require a valid JWT token in the Authorization header:
    Authorization: Bearer <your_token>

    Rate Limiting:
    - API calls are limited to 100 requests per minute per IP
    - File uploads are limited to 50MB per file
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    on_startup=[on_startup]
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add timing middleware to debug the 20-second delay
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start_time = time.time()
    logger.info(f"🚀 Request started: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"✅ Request completed in {process_time:.2f}s: {request.method} {request.url}")
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ Request failed after {process_time:.2f}s: {request.method} {request.url} - Error: {str(e)}")
        raise

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"Bearer": []}]
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        },
        {
            "url": "https://api.jasper.ai",
            "description": "Production server"
        }
    ]
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints",
            "externalDocs": {
                "description": "Authentication Guide",
                "url": "https://docs.jasper.ai/auth"
            }
        },
        {
            "name": "Voice Management",
            "description": "Voice sample processing and management endpoints",
            "externalDocs": {
                "description": "Voice Processing Guide",
                "url": "https://docs.jasper.ai/voice"
            }
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints for managing default voices and system settings",
            "externalDocs": {
                "description": "Admin Guide",
                "url": "https://docs.jasper.ai/admin"
            }
        },
        {
            "name": "Projects",
            "description": "Project management endpoints for creating and managing user projects",
            "externalDocs": {
                "description": "Project Management Guide",
                "url": "https://docs.jasper.ai/projects"
            }
        },
        {
            "name": "Books",
            "description": "Book management endpoints for uploading and managing book files",
            "externalDocs": {
                "description": "Book Management Guide",
                "url": "https://docs.jasper.ai/books"
            }
        },
        {
            "name": "Voice Generation",
            "description": "Voice generation endpoints for creating audio from text chapters",
            "externalDocs": {
                "description": "Voice Generation Guide",
                "url": "https://docs.jasper.ai/voice-generation"
            }
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/health")
@limiter.limit("200/minute")
async def health(
    request: Request,
    current_user: User = Depends(get_optional_user)
):
    """
    Health check endpoint that can optionally include user information if authenticated.
    """
    response = {
        "status": "🔥",
        "message": "System is absolutely crushing it right now 💪",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    if current_user:
        response["user"] = {
            "id": current_user.id,
            "email": current_user.email,
            "is_verified": current_user.is_verified
        }
    
    return response

# Simple rate limiting dependency to reduce overhead
def get_rate_limit():
    # Allow disabling rate limiting for development
    if os.environ.get("DISABLE_RATE_LIMITING", "0") == "1":
        return lambda: None  # No-op function
    return limiter.limit("200/minute")  # Simplified dependency

# Include routers with simplified rate limiting
app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["Authentication"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    voice.router,
    prefix="/api/v1",
    tags=["Voice Management"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    credit_router,
    prefix="/api/v1",
    tags=["Credits"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    admin.router,
    prefix="/api/v1",
    tags=["Admin"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    project_router,
    prefix="/api/v1",
    tags=["Projects"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    book_router,
    prefix="/api/v1",
    tags=["Books"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    config_router,
    prefix="/api/v1/config",
    tags=["Config"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    payment.router,
    prefix="/api/v1/payments",
    tags=["Payments"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    persistent_data_router,
    prefix="/api/v1/persistent-data",
    tags=["Persistent Data"],
    dependencies=[Depends(get_rate_limit)]
)

app.include_router(
    voice_generation_router,
    prefix="/api/v1/voice-generation",
    tags=["Voice Generation"],
    dependencies=[Depends(get_rate_limit)]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    
    # Optimized settings for direct execution
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port,
        reload=True
)