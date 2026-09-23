import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL or "sqlite:///./ai_platform.db"

try:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
    )
    # Validate driver import
    engine.connect().close()
except Exception as e:
    logger.warning(
        f"PostgreSQL driver/connection unavailable ({e}). Using local SQLite: sqlite:///./ai_platform.db"
    )
    engine = create_engine(
        "sqlite:///./ai_platform.db",
        connect_args={"check_same_thread": False},
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()