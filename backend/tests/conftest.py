"""
Pytest configuration and fixtures for Argos tests.
"""
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport

# Import app and database for testing
from app.main import app
from app.database import init_db


# Initialize database at module load
import asyncio
asyncio.get_event_loop().run_until_complete(init_db())


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
