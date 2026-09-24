import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_platform")
    JWT_SECRET = os.getenv("JWT_SECRET")
    if not JWT_SECRET:
        if ENVIRONMENT == "production":
            raise RuntimeError("JWT_SECRET must be configured in production")
        JWT_SECRET = secrets.token_urlsafe(32)
        logger.warning("JWT_SECRET is unset; using a temporary development key. Set JWT_SECRET to keep tokens valid across restarts and instances.")
    elif len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gemini-2.5-flash")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")


settings = Settings()
