"""
Tests for API endpoints.
"""
import pytest
from httpx import AsyncClient


class TestHealth:
    """Health endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns ok."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "visionmind"


class TestConfig:
    """Configuration endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_config(self, client: AsyncClient):
        """Test getting configuration."""
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "video_source" in data
        assert "model_size" in data
        assert "confidence_threshold" in data

    @pytest.mark.asyncio
    async def test_update_config(self, client: AsyncClient, sample_config_update):
        """Test updating configuration."""
        response = await client.put("/api/config", json=sample_config_update)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert "config" in data


class TestZones:
    """Zone endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_zones(self, client: AsyncClient):
        """Test getting zones list."""
        response = await client.get("/api/zones")
        assert response.status_code == 200
        data = response.json()
        assert "zones" in data
        assert isinstance(data["zones"], list)

    @pytest.mark.asyncio
    async def test_create_and_delete_zone(self, client: AsyncClient, sample_zone):
        """Test creating and deleting a zone."""
        # Create
        response = await client.post("/api/zones", json=sample_zone)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["zone"]["id"] == sample_zone["id"]

        # Delete
        response = await client.delete(f"/api/zones/{sample_zone['id']}")
        assert response.status_code == 200


class TestAuth:
    """Authentication endpoint tests."""

    @pytest.mark.asyncio
    async def test_auth_status(self, client: AsyncClient):
        """Test auth status endpoint."""
        response = await client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data

    @pytest.mark.asyncio
    async def test_login_when_auth_disabled(self, client: AsyncClient):
        """Test login returns token when auth is disabled."""
        response = await client.post(
            "/api/auth/login",
            json={"username": "test", "password": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestRecordings:
    """Recordings endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_recordings(self, client: AsyncClient):
        """Test getting recordings list."""
        response = await client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data
        assert "total_size_mb" in data

    @pytest.mark.asyncio
    async def test_get_recording_status(self, client: AsyncClient):
        """Test getting recording status."""
        response = await client.get("/api/recordings/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_recording" in data
        assert "buffer_seconds" in data


class TestAnalytics:
    """Analytics endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_summary(self, client: AsyncClient):
        """Test getting analytics summary."""
        response = await client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "alerts" in data

    @pytest.mark.asyncio
    async def test_get_realtime(self, client: AsyncClient):
        """Test getting realtime analytics."""
        response = await client.get("/api/analytics/realtime")
        assert response.status_code == 200
        data = response.json()
        assert "total_detections" in data
        assert "hourly_counts" in data

    @pytest.mark.asyncio
    async def test_get_heatmap(self, client: AsyncClient):
        """Test getting heatmap data."""
        response = await client.get("/api/analytics/heatmap")
        assert response.status_code == 200
        data = response.json()
        assert "heatmap" in data
        assert "days" in data
