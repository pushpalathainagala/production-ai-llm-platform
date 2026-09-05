import redis

from app.config import settings


redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def check_redis():
    return redis_client.ping()