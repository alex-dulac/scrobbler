from asyncio import shield
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from loguru import logger
from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession

from core import config
from models.db import Base


class SessionManager:
    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def init_db(self) -> None:
        url = config.DATABASE_URL

        if url is None:
            raise ValueError('DATABASE_URL environment variable is not set')

        is_local = url.find("localhost") != -1
        logger.info(f"Connecting to {"local" if is_local else "remote"} database...")

        self.engine = create_async_engine(
            url=url,
            poolclass=AsyncAdaptedQueuePool,
            # Library endpoints fan out ~11-13 concurrent queries; keep those
            # connections open so each request doesn't reconnect to a remote DB.
            # No overflow: the hosted plan allows 20 connections (3 reserved), so
            # bursts must queue for a pooled connection rather than be refused.
            pool_size=15,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=1800,
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
    session = session_manager.session_factory()
    try:
        yield session
    finally:
        await shield(session.close())


