from fastapi import FastAPI
from api.v1.endpoints import auth
from db.session import engine, Base
import os
import uvicorn

def on_startup():
    # Create all tables (flush models with DB)
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="jasper-voice-gateway", on_startup=[on_startup])

@app.get("/health")
async def health():
    return {"status": "🔥", "message": "System is absolutely crushing it right now 💪"}

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Future: include other modules (voice-management, project-management, etc)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)