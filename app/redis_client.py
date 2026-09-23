import logging
import redis

from app.config import settings

logger = logging.getLogger(__name__)

try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
    )
except Exception as e:
    logger.warning(f"Could not initialize Redis client: {e}")
    redis_client = None


def check_redis() -> bool:
    try:
        if redis_client:
            return bool(redis_client.ping())
    except Exception as exc:
        logger.warning(f"Redis health check failed: {exc}")
    return False


def get_cached_response(key: str):
    try:
        if redis_client:
            return redis_client.get(key)
    except Exception as exc:
        logger.warning(f"Redis get error (degrading gracefully): {exc}")
    return None


def set_cached_response(key: str, value: str, ttl: int = 300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, value)
    except Exception as exc:
        logger.warning(f"Redis set error (degrading gracefully): {exc}")