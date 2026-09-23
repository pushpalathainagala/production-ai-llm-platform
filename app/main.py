import logging
from time import perf_counter

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.database import Base, engine, get_db
from app import models
from app.schemas import LoginRequest, TokenResponse, ChatRequest
from app.auth import verify_password, create_access_token, get_current_user, require_roles
from app.llm import ask_gemini, LLMTimeoutError, LLMProviderError
from app.redis_client import get_cached_response, set_cached_response, check_redis

logger = logging.getLogger(__name__)

# Safe database initialization
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:
    logger.warning(f"Database table initialization skipped (DB may not be ready yet): {exc}")

app = FastAPI(
    title="AI/LLM Platform API",
    description="Production-grade AI Question Answering API with Caching, Auth, and Observability",
    version="1.1.0",
)


@app.middleware("http")
async def track_requests(request, call_next):
    start_time = perf_counter()

    response = await call_next(request)

    duration = perf_counter() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response


@app.get("/health")
def health():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    redis_status = "connected" if check_redis() else "unreachable"
    overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
        "service": "ai-llm-platform",
    }


@app.post("/auth/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.username == login_data.username)
        .first()
    )

    if not user or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token(
        username=user.username,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.post("/chat")
def chat(
    chat_data: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    cache_key = f"chat:{chat_data.question.strip().lower()}"

    # Attempt cache lookup with graceful degradation if Redis is down
    cached_answer = get_cached_response(cache_key)

    if cached_answer:
        return {
            "username": current_user["username"],
            "role": current_user["role"],
            "question": chat_data.question,
            "answer": cached_answer,
            "cached": True,
            "tokens_used": 0,
            "model": "redis-cache",
        }

    try:
        answer, tokens_used, model_used = ask_gemini(chat_data.question)
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM request timed out: {exc}",
        )
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM upstream provider failure: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while generating LLM response: {exc}",
        )

    # Persist in cache (silently ignores if Redis is unreachable)
    set_cached_response(cache_key, answer, ttl=300)

    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "question": chat_data.question,
        "answer": answer,
        "cached": False,
        "tokens_used": tokens_used,
        "model": model_used,
    }


@app.get("/admin/system-status")
def admin_status(
    current_user: dict = Depends(require_roles(["admin"])),
):
    """Admin-only endpoint demonstrating Role-Based Access Control (RBAC)."""
    return {
        "admin_user": current_user["username"],
        "role": current_user["role"],
        "redis_healthy": check_redis(),
        "primary_model": settings.PRIMARY_MODEL,
        "fallback_model": settings.FALLBACK_MODEL,
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

