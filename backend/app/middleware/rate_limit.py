"""Rate limiting middleware for API endpoints."""
import logging
import time
from fastapi import Request, HTTPException, status as http_status
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window algorithm."""
    
    RATE_LIMIT = 100  # requests per window
    WINDOW_SECONDS = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:api:{client_ip}"
        
        try:
            redis = get_redis()
            # Sliding window: use sorted set
            now = time.time()
            window_start = now - self.WINDOW_SECONDS
            
            # Remove old entries
            redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            count = redis.zcard(key)
            
            if count >= self.RATE_LIMIT:
                # Calculate retry after
                oldest = redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] - window_start) + 1
                else:
                    retry_after = self.WINDOW_SECONDS
                
                raise HTTPException(
                    status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Add current request
            redis.zadd(key, {str(now): now})
            redis.expire(key, self.WINDOW_SECONDS)
            
        except HTTPException:
            # Re-raise HTTP exceptions (rate limit exceeded)
            raise
        except Exception as e:
            # If Redis fails, log but allow request (fail open)
            logger.warning(f"Rate limit check failed: {e}")
        
        return await call_next(request)

