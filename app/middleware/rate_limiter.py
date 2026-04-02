from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def get_user_or_ip(request):
    """Rate limit key: authenticated user hash or IP address."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return f"user:{hash(auth_header[7:])}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip, default_limits=[settings.RATE_LIMIT], storage_uri=None)
