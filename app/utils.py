BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def get_client_ip(request) -> str:
    """
    Resolve the real client IP.

    Render (and most PaaS platforms) sit behind a reverse proxy, so
    request.client.host is the proxy's IP, not the caller's. The proxy
    sets X-Forwarded-For: <original client>, <proxy1>, <proxy2>, ...
    We trust the first entry since we only have one hop (Render's edge proxy).
    Falls back to request.client.host for local dev, where there's no proxy.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def encode_base62(num: int) -> str:
    """Convert an integer ID to a Base62 short code"""
    if num == 0:
        return BASE62_CHARS[0]
    
    result = []
    while num > 0:
        result.append(BASE62_CHARS[num % 62])
        num //= 62
    
    return "".join(reversed(result))


def decode_base62(short_code: str) -> int:
    """Convert a Base62 short code back to integer ID"""
    result = 0
    for char in short_code:
        result = result * 62 + BASE62_CHARS.index(char)
    return result