from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate Limiter setup using client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
