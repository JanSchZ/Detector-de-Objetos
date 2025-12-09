"""
Pytest configuration and fixtures for VisionMind tests.
"""
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport

# Import app for testing
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_zone():
    """Sample zone data for testing."""
    return {
        "id": "test-zone-1",
        "name": "Test Zone",
        "type": "warning",
        "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
        "color": "#f59e0b",
        "enabled": True,
    }


@pytest.fixture
def sample_config_update():
    """Sample config update for testing."""
    return {
        "model_size": "nano",
        "confidence_threshold": 0.5,
        "max_fps": 30,
    }
