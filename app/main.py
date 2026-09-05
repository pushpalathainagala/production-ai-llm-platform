from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from time import perf_counter

from app.metrics import REQUEST_COUNT, REQUEST_LATENCY

from app.database import Base, engine, get_db
from app import models
from app.schemas import LoginRequest, TokenResponse, ChatRequest
from app.auth import verify_password, create_access_token, get_current_user
from app.llm import ask_gemini
from app.redis_client import redis_client


Base.metadata.create_all(bind=engine)

app = FastAPI(
    
    title="AI/LLM Platform API",
    description="Production-style AI Question Answering API",
    version="1.0.0",
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
    return {"status": "healthy"}


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

    cached_answer = redis_client.get(cache_key)

    if cached_answer:
        return {
            "username": current_user["username"],
            "role": current_user["role"],
            "question": chat_data.question,
            "answer": cached_answer,
            "cached": True,
        }

    answer = ask_gemini(chat_data.question)

    redis_client.setex(
        cache_key,
        300,
        answer,
    )

    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "question": chat_data.question,
        "answer": answer,
        "cached": False,
    }

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
