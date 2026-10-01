from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_real_ip(request: Request) -> str:
    """Extract real client IP behind reverse proxies using X-Forwarded-For or remote address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP address in the X-Forwarded-For comma-separated chain
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    return get_remote_address(request)

# Rate Limiter setup using real client IP address
limiter = Limiter(key_func=get_real_ip, default_limits=["100/minute"])
