import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["status"] in ("healthy", "degraded")
        assert payload["data"]["service"] == "QUIZVERSE API"
        assert payload["data"]["version"] == "1.0.0"
        assert payload["meta"]["version"] == "v1"
        assert "uptime_seconds" in payload["data"]
        assert "database_status" in payload["data"]

        # Ensure no database credentials or secrets leaked
        serialized = str(payload)
        assert "password" not in serialized.lower()
        assert "service_role" not in serialized.lower()


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "QUIZVERSE API"
        assert payload["docs"] == "/docs"


@pytest.mark.asyncio
async def test_404_handler():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/nonexistent-route")
        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "HTTP_404"
