"""
MindPulse backend entrypoint.

Connects to MongoDB, creates indexes, exposes a health check, and wires the
student, AI, risk, and student-initiated referral APIs.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from ai.sentiment_model import warm_up as warm_up_sentiment_model
from app.auth.routes import router as auth_router
from app.behavior.routes import router as behavior_router
from app.chat.routes import router as chat_router
from app.consent.routes import router as consent_router
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.db.indexes import create_indexes
from app.risk_engine.routes import router as risk_router
from app.sentiment.routes import router as sentiment_router
from app.referral.routes import router as referral_router
from app.dashboards.routes import router as dashboards_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await create_indexes(get_database())
    # Load the sentiment model in the background so the server starts
    # immediately (first run downloads the model, which can take minutes).
    warm_up_task = asyncio.create_task(warm_up_sentiment_model())
    yield
    # Shutdown
    warm_up_task.cancel()
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description="AI-driven student well-being support system with ethical, "
    "explainable risk detection. Not a diagnostic tool.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health_check():
    """Basic liveness + DB connectivity check."""
    db = get_database()
    await db.command("ping")
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(consent_router, prefix="/consent", tags=["consent"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(behavior_router, prefix="/behavior", tags=["behavior"])
app.include_router(sentiment_router, prefix="/sentiment", tags=["sentiment"])
app.include_router(risk_router, prefix="/risk", tags=["risk"])
app.include_router(referral_router, prefix="/referral", tags=["referral"])
app.include_router(dashboards_router, prefix="/dashboard", tags=["dashboard"])
