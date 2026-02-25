"""Tests for in-memory API rate limit middleware."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.middleware import rate_limit

# Don't raise 4xx/5xx so we can assert on 429 response
client = TestClient(app, raise_server_exceptions=False)


def test_health_not_rate_limited():
    """Health and root paths are not rate limited."""
    for _ in range(5):
        r = client.get("/health")
        assert r.status_code == 200
    r = client.get("/")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_limit():
    """More than RATE_LIMIT requests in window returns 429."""
    rate_limit._rate_window.clear()
    middleware = rate_limit.RateLimitMiddleware(app=MagicMock())
    middleware.RATE_LIMIT = 3
    middleware.WINDOW_SECONDS = 60

    async def call_next(request):
        return MagicMock(status_code=200)

    def make_request():
        req = MagicMock()
        req.url = MagicMock(path="/api/foo")
        req.client = MagicMock(host="192.168.1.100", port=12345)
        return req

    for _ in range(3):
        r = await middleware.dispatch(make_request(), call_next)
        assert r.status_code == 200

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(make_request(), call_next)
    assert exc_info.value.status_code == 429
    assert "retry-after" in [k.lower() for k in exc_info.value.headers.keys()]
