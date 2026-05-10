from app.cache import redis_client
from datetime import datetime
from fastapi import Request, HTTPException

# Configuration
RATE_LIMIT_REQUESTS = 10        # max requests
RATE_LIMIT_WINDOW = 60          # per 60 seconds


def is_rate_limited(ip: str, endpoint: str = "global") -> tuple[bool, int, int]:
    """
    Check if an IP is rate limited.
    
    Returns:
        (is_limited, current_count, limit)
    """
    # Key includes current minute — auto resets every minute
    current_minute = datetime.now().strftime("%Y%m%d%H%M")
    key = f"ratelimit:{endpoint}:{ip}:{current_minute}"

    # Atomic increment — thread safe
    current_count = redis_client.incr(key)

    # Set TTL only on first request (when count == 1)
    if current_count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW)

    is_limited = current_count > RATE_LIMIT_REQUESTS
    return is_limited, current_count, RATE_LIMIT_REQUESTS


def get_remaining_requests(ip: str, endpoint: str = "global") -> int:
    """How many requests does this IP have left this window"""
    current_minute = datetime.now().strftime("%Y%m%d%H%M")
    key = f"ratelimit:{endpoint}:{ip}:{current_minute}"
    
    current = redis_client.get(key)
    if not current:
        return RATE_LIMIT_REQUESTS
    
    remaining = RATE_LIMIT_REQUESTS - int(current)
    return max(0, remaining)


def rate_limit_dependency(endpoint: str = "global"):
    """
    Factory function — returns a FastAPI dependency for a specific endpoint.
    Usage: Depends(rate_limit_dependency("shorten"))
    """
    def dependency(request: Request):
        # Get client IP
        ip = request.client.host

        # Check rate limit
        is_limited, count, limit = is_rate_limited(ip, endpoint)

        if is_limited:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "message": f"Limit is {limit} requests per minute",
                    "retry_after": "60 seconds"
                },
                headers={"Retry-After": "60"}
            )

    return dependency