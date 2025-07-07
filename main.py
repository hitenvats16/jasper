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
from fastapi.responses import JSONResponse
from api.v1.endpoints import credit_router, rate_router, project_router
from core.dependencies import get_optional_user
from models.user import User
import logging
import sys
from utils.message_publisher import get_rabbitmq_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def on_startup():
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

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

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
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/health")
@limiter.limit("100/minute")
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
            "email": current_user.email
        }
    
    return response

# Include routers with rate limiting
app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["Authentication"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

app.include_router(
    voice.router,
    prefix="/api/v1",
    tags=["Voice Management"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

app.include_router(
    credit_router,
    prefix="/api/v1",
    tags=["Credits"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

app.include_router(
    rate_router,
    prefix="/api/v1",
    tags=["Rates"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

app.include_router(
    admin.router,
    prefix="/api/v1",
    tags=["Admin"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

app.include_router(
    project_router,
    prefix="/api/v1",
    tags=["Projects"],
    dependencies=[Depends(lambda: limiter.limit("100/minute"))]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)