from .auth import router as auth_router
from .voice import router as voice_router
from .credit import router as credit_router
from .project import router as project_router
from .book import router as book_router
from .payment import router as payment_router
from .persistent_data import router as persistent_data_router
from .voice_generation import router as voice_generation_router
from .config import router as config_router

__all__ = [
    "auth_router",
    "voice_router",
    "credit_router",
    "project_router",
    "book_router",
    "payment_router",
    "persistent_data_router",
    "voice_generation_router",
    "config_router",
]