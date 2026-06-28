import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

CACHE_TTL = 3600  # 1 hour for URL cache


def get_cached_url(short_code: str) -> str | None:
    """Get original URL from Redis cache"""
    return redis_client.get(f"url:{short_code}")


def set_cached_url(short_code: str, original_url: str) -> None:
    """Store URL in Redis with TTL"""
    redis_client.setex(
        name=f"url:{short_code}",
        time=CACHE_TTL,
        value=original_url
    )


def delete_cached_url(short_code: str) -> None:
    """Remove URL from cache"""
    redis_client.delete(f"url:{short_code}")



def increment_click_redis(short_code: str) -> int:
    """
    Atomically increment click count in Redis.
    Returns new count.
    This never touches PostgreSQL — that's the whole point.
    """
    key = f"clicks:{short_code}"
    count = redis_client.incr(key)
    return count


def get_redis_click_count(short_code: str) -> int:
    """Get buffered click count from Redis"""
    key = f"clicks:{short_code}"
    val = redis_client.get(key)
    return int(val) if val else 0


def get_all_pending_clicks() -> dict[str, int]:
    """
    Get all short codes that have pending click counts in Redis.
    Used by the background flush job.
    Returns dict of {short_code: count}
    """
    keys = redis_client.keys("clicks:*")
    if not keys:
        return {}

    result = {}
    for key in keys:
        val = redis_client.get(key)
        if val:
            short_code = key.replace("clicks:", "")
            result[short_code] = int(val)

    return result


def reset_click_count(short_code: str) -> None:
    """Reset Redis click counter after flushing to DB"""
    redis_client.delete(f"clicks:{short_code}")


def is_redis_healthy() -> bool:
    try:
        redis_client.ping()
        return True
    except Exception:
        return False