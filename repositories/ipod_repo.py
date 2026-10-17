from datetime import datetime
from itertools import batched
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import IpodPlay
from repositories.base import BaseRepository
from services.ipod import PendingPlay

# keeps each insert well under Postgres' bind parameter limit
INSERT_BATCH_SIZE = 1000


class IPodRepository(BaseRepository):
    """
    Repository for managing iPod related database operations.
    """
    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)

    async def add_plays(self, plays: list[PendingPlay], generation: str) -> int:
        """Store captured plays, skipping any already stored. Returns the number of new plays."""
        rows = [
            {
                "dbid": f"{play.track.dbid:016x}",
                "generation": generation,
                "play_number": play.play_number,
                "track_name": play.track.title,
                "artist_name": play.track.artist,
                "album_name": play.track.album,
                "duration": play.track.duration_ms,
                "played_at": play.played_at,
                "played_at_estimated": play.estimated,
            }
            for play in plays
        ]

        inserted = 0
        async with self._get_session() as session:
            for batch in batched(rows, INSERT_BATCH_SIZE):
                query = (
                    insert(IpodPlay)
                    .values(list(batch))
                    .on_conflict_do_nothing(index_elements=["dbid", "generation", "play_number"])
                    .returning(IpodPlay.id)
                )
                result = await session.execute(query)
                inserted += len(result.all())
            await session.commit()

        return inserted

    async def get_pending_plays(self, since: datetime) -> list[IpodPlay]:
        """Plays since the given time that have been neither scrobbled nor discarded."""
        query = (
            select(IpodPlay)
            .where(
                IpodPlay.scrobbled_at.is_(None),
                IpodPlay.discarded_at.is_(None),
                IpodPlay.played_at >= since,
            )
            .order_by(IpodPlay.played_at)
        )
        result = await self.execute(query)
        return result.scalars().all()

    async def mark_scrobbled(self, play_id: int, scrobbled_at: datetime) -> None:
        query = update(IpodPlay).where(IpodPlay.id == play_id).values(scrobbled_at=scrobbled_at)
        async with self._get_session() as session:
            await session.execute(query)
            await session.commit()

    async def discard_plays(self, play_ids: list[int], discarded_at: datetime) -> None:
        query = update(IpodPlay).where(IpodPlay.id.in_(play_ids)).values(discarded_at=discarded_at)
        async with self._get_session() as session:
            await session.execute(query)
            await session.commit()
