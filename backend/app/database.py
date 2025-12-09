"""
Database configuration and setup for Argos.
Uses SQLAlchemy async with SQLite for persistence.
"""
import os
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


# Database file path
DB_PATH = Path(__file__).parent.parent / "data" / "argos.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Database URL
DATABASE_URL = os.getenv("VM_DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("VM_DB_ECHO", "false").lower() == "true",
    future=True,
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def init_db():
    """Initialize database and create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Base de datos inicializada")


async def close_db():
    """Close database connections."""
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session (for non-route usage)."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
