from contextlib import asynccontextmanager
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db


class BaseRepository:
    """
    Base repository class that handles database session management.
    All repositories should inherit from this class.
    """
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize repository with optional database session.

        Args:
            db: Optional AsyncSession. If not provided, sessions will be created on-demand.
        """
        self._db = db

    @asynccontextmanager
    async def _get_session(self):
        """
        Either use provided one or create temporary one.
        """
        if self._db is not None:
            # Use provided session (no cleanup needed)
            yield self._db
        else:
            # Create temporary session for this operation
            async with get_db() as session:
                yield session

    async def add(self, obj: Any) -> Any:
        """Add a single object to the database."""
        async with self._get_session() as session:
            session.add(obj)
            await session.flush()
            return obj

    async def add_all(self, objs: list[Any]) -> list[Any]:
        """Add multiple objects to the database."""
        async with self._get_session() as session:
            session.add_all(objs)
            await session.flush()
            return objs

    async def add_and_commit(self, objs: list[Any] | Any) -> None:
        """Add objects and commit immediately."""
        if not isinstance(objs, list):
            # Wrap single object in a list
            objs = [objs]

        async with self._get_session() as session:
            session.add_all(objs)
            await session.commit()

    async def delete(self, obj: Any) -> None:
        """Delete a single object from the database."""
        async with self._get_session() as session:
            await session.delete(obj)
            await session.flush()

    async def commit(self) -> None:
        """Commit the current transaction."""
        async with self._get_session() as session:
            await session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        async with self._get_session() as session:
            await session.rollback()

    async def refresh(self, obj: Any) -> Any:
        """Refresh an object from the database."""
        async with self._get_session() as session:
            await session.refresh(obj)
            return obj

    async def execute(self, query):
        """Execute a raw query."""
        async with self._get_session() as session:
            result = await session.execute(query)
            return result
