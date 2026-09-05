import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    REDIS_URL = os.getenv("REDIS_URL")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))


settings = Settings()