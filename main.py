from fastapi import FastAPI
from api.v1.endpoints import auth
from db.session import engine, Base

def on_startup():
    # Create all tables (flush models with DB)
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="jasper-voice-gateway", on_startup=[on_startup])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Future: include other modules (voice-management, project-management, etc)