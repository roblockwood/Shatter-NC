"""Redis client singleton for distributed coordination and caching."""
import logging
from typing import Optional
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instances (sync and async)
_redis_client: Optional[Redis] = None
_async_redis_client: Optional[AsyncRedis] = None


def get_redis() -> Redis:
    """Get synchronous Redis client (singleton)."""
    global _redis_client
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client


async def get_async_redis() -> AsyncRedis:
    """Get asynchronous Redis client (singleton) for locks and async operations."""
    global _async_redis_client
    if _async_redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _async_redis_client


def init_redis() -> bool:
    """
    Initialize Redis connections (sync and async). Returns True if successful.
    
    Raises RuntimeError if Redis is unavailable (fail-fast since Redis is required).
    """
    global _redis_client, _async_redis_client
    try:
        # Sync client for simple operations (set/get)
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=False,  # Binary mode
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Test connection
        _redis_client.ping()
        
        # Async client for locks and async operations
        import redis.asyncio as redis_asyncio
        _async_redis_client = redis_asyncio.from_url(
            settings.redis_url,
            decode_responses=False,  # Binary mode for locks
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
        logger.info(f"Redis client initialized successfully: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise RuntimeError(f"Failed to initialize Redis - application cannot start: {e}") from e


async def close_redis():
    """Close Redis connections (called on shutdown)."""
    global _redis_client, _async_redis_client
    if _redis_client:
        try:
            _redis_client.close()
            logger.info("Redis sync client closed")
        except Exception as e:
            logger.warning(f"Error closing Redis sync client: {e}")
        finally:
            _redis_client = None
    
    if _async_redis_client:
        try:
            await _async_redis_client.close()
            logger.info("Redis async client closed")
        except Exception as e:
            logger.warning(f"Error closing Redis async client: {e}")
        finally:
            _async_redis_client = None

