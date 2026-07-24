"""Sanitized API error messages for production responses."""
from app.core.config import settings


def public_error_detail(exc: Exception, *, context: str = "Request failed") -> str:
    """Return exception text in DEBUG, otherwise a generic message."""
    if settings.LOG_LEVEL.upper() == "DEBUG":
        return str(exc)
    return context
