import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_platform")
    JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gemini-2.5-flash")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")


settings = Settings()