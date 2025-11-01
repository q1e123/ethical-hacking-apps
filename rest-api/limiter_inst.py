from slowapi import Limiter
from slowapi.util import get_remote_address

# Default per-IP limit
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
