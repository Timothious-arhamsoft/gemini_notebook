from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, health, notebooks, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀  NoteGenio API starting...")
    from app import models
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    print("👋  Shutting down")


app = FastAPI(
    title="NoteGenio API",
    description="NotebookLM-inspired RAG backend powered by FastAPI + Gemini",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["Notebooks"])
app.include_router(sources.router, prefix="/api/v1/notebooks", tags=["Sources"])
