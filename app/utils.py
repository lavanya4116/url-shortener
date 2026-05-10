BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

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