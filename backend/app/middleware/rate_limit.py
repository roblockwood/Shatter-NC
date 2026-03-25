"""Rate limiting middleware for API endpoints."""
import asyncio
import logging
import time
from collections import deque
from typing import Dict

from fastapi import Request, status as http_status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# In-memory sliding window: client_ip -> deque of request timestamps (oldest first)
_rate_window: Dict[str, deque] = {}
_rate_lock = asyncio.Lock()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using in-memory sliding window."""

    RATE_LIMIT = 100  # requests per window
    WINDOW_SECONDS = 60  # 1 minute

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.WINDOW_SECONDS

        async with _rate_lock:
            if client_ip not in _rate_window:
                _rate_window[client_ip] = deque()
            timestamps = _rate_window[client_ip]
            # Prune old entries
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()
            count = len(timestamps)
            if count >= self.RATE_LIMIT:
                retry_after = int(timestamps[0] - window_start) + 1 if timestamps else self.WINDOW_SECONDS
                retry_after = max(1, min(retry_after, self.WINDOW_SECONDS))
                # Return a response here; raising HTTPException from BaseHTTPMiddleware.dispatch
                # does not propagate correctly (Starlette TaskGroup → 500 + noisy logs).
                return JSONResponse(
                    status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)

        return await call_next(request)
