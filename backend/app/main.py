"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: import models to register them, load embedding model
    from app.models import user, movie, taste_profile, library, follow  # noqa: F401
    print(f"[{settings.APP_NAME}] Models registered.")

    # Lazy-load embedding model on first use (avoid blocking startup)
    yield

    # Shutdown
    from app.database import engine
    await engine.dispose()
    print(f"[{settings.APP_NAME}] Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered movie discovery platform built on a taste graph.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Register Routers ---
from app.routers import auth, profile, recommend, library, social  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["Recommend"])
app.include_router(library.router, prefix="/api/library", tags=["Library"])
app.include_router(social.router, prefix="/api/social", tags=["Social"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
