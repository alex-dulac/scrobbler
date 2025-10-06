from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession

from core import config
from models.db import Base


class SessionManager:
    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def init_db(self) -> None:
        self.engine = create_async_engine(
            url=config.DATABASE_URL,
            poolclass=AsyncAdaptedQueuePool,
            pool_pre_ping=True,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession
        )

        async with self.engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def close_db(self) -> None:
        if self.engine:
            await self.engine.dispose()


session_manager = SessionManager()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if not session_manager.session_factory:
        raise RuntimeError("Database session factory is not initialized.")
    async with session_manager.session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


