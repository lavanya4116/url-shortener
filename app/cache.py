import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Create Redis client
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True      # returns strings, not bytes
)

# How long to cache a URL (in seconds)
CACHE_TTL = 3600               # 1 hour


def get_cached_url(short_code: str) -> str | None:
    """Try to get original URL from Redis cache"""
    return redis_client.get(f"url:{short_code}")


def set_cached_url(short_code: str, original_url: str) -> None:
    """Store URL in Redis with TTL"""
    redis_client.setex(
        name=f"url:{short_code}",
        time=CACHE_TTL,
        value=original_url
    )


def delete_cached_url(short_code: str) -> None:
    """Remove URL from cache (called on delete)"""
    redis_client.delete(f"url:{short_code}")


def is_redis_healthy() -> bool:
    """Health check for Redis"""
    try:
        redis_client.ping()
        return True
    except Exception:
        return False