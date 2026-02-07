"""
Contract tests for API response shapes.
Focus on admin revenue and subscription status.
"""

from unittest.mock import AsyncMock


def test_admin_revenue_contract(app, monkeypatch):
    from fastapi.testclient import TestClient
    from utils import get_current_admin_user
    from routes import admin_routes

    app.dependency_overrides[get_current_admin_user] = lambda: {
        "id": "admin_test",
        "email": "admin@example.com",
        "role": "admin",
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(side_effect=[[], [], []])
    mock_conn.fetchrow = AsyncMock(
        return_value={"mrr": 0, "pro_count": 0, "business_count": 0}
    )

    async def fake_get_db():
        return mock_conn

    async def fake_release_db(_conn):
        return None

    monkeypatch.setattr(admin_routes, "get_db", fake_get_db)
    monkeypatch.setattr(admin_routes, "release_db", fake_release_db)

    client = TestClient(app)
    response = client.get("/api/v1/admin/revenue")
    assert response.status_code == 200
    data = response.json()
    assert "business_subscribers" in data
    assert "pro_subscribers" in data
    assert "mrr" in data
    app.dependency_overrides.clear()


def test_subscription_status_contract(app, monkeypatch):
    from fastapi.testclient import TestClient
    from routes import polar_routes

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=0)

    async def fake_get_db():
        return mock_conn

    async def fake_release_db(_conn):
        return None

    async def fake_user():
        return {
            "id": "user_test",
            "email": "user@example.com",
            "role": "user",
        }

    monkeypatch.setattr(polar_routes, "get_db", fake_get_db)
    monkeypatch.setattr(polar_routes, "release_db", fake_release_db)
    app.dependency_overrides[polar_routes.get_current_user_for_polar] = fake_user
    monkeypatch.setattr(polar_routes, "get_db", fake_get_db)
    monkeypatch.setattr(polar_routes, "release_db", fake_release_db)

    client = TestClient(app)
    response = client.get("/api/v1/subscription/status")
    assert response.status_code == 200
    data = response.json()
    assert "plan_tier" in data
    assert "limits" in data
    assert "usage" in data
    assert "max_licenses_per_project" in data["limits"]
    app.dependency_overrides.clear()
