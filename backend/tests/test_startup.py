"""Tests that app starts without Redis and health endpoint works."""
import pytest
from fastapi.testclient import TestClient

# Import app after any env mocks if needed; app must not depend on Redis
from app.main import app


def test_app_import_has_no_redis():
    """App module does not import redis_client (Redis removed)."""
    import app.main as main_module
    assert not hasattr(main_module, "init_redis")
    # Ensure no redis_client in sys.modules for main's direct imports
    import sys
    assert "app.utils.redis_client" not in sys.modules


def test_health_returns_200():
    """GET /health returns 200 when app is running."""
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
