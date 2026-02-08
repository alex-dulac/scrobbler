from datetime import datetime
from typing import Any, Optional

from pylast import PlayedTrack
from sqlalchemy import select, func, desc, extract, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import (
    Album,
    Artist,
    Scrobble,
    Track,
)
from models.schemas import LastFmTrack
from repositories.base import BaseRepository
from repositories.filters import ScrobbleFilter, build_query, to_lower, like_lower


class ScrobbleRepository(BaseRepository):
    """
    Repository for interacting with scrobble data in the database.
    Inherits session management from BaseRepository.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)

    async def get_scrobbles(self, f: ScrobbleFilter = None) -> list[Scrobble]:
        """Get scrobbles with optional filtering."""
        query = await build_query(f)
        result = await self.execute(query)
        return result.scalars().all()

    async def add_scrobble(self, lastfm_track: LastFmTrack):
        db_scrobble = Scrobble(
            artist_name=lastfm_track.artist,
            album_name=lastfm_track.album,
            track_name=lastfm_track.name,
            scrobbled_at=lastfm_track.scrobbled_at
        )
        await self.add_and_commit(db_scrobble)

    async def get_artists_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.artist_name)
        )
        result = await self.execute(query)
        return result.scalars().all()

    async def get_albums_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.album_name, Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.album_name)
        )
        result = await self.execute(query)
        return result.all()

    async def get_tracks_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.track_name, Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.track_name)
        )
        result = await self.execute(query)
        return result.all()

    async def get_artists_with_no_ref_data(self) -> Any:
        query = (
            select(Scrobble.artist_name)
            .outerjoin(Artist, Scrobble.artist_name == Artist.name)
            .where(Artist.name.is_(None))
            .distinct()
            .order_by(Scrobble.artist_name)
        )
        result = await self.execute(query)
        return result.scalars().all()

    async def get_albums_with_no_ref_data(self) -> Any:
        query = (
            select(Scrobble.album_name, Scrobble.artist_name)
            .outerjoin(Album, Scrobble.album_name == Album.title)
            .outerjoin(Artist, Scrobble.artist_name == Artist.name)
            .where(Album.title.is_(None))
            .distinct()
            .order_by(Scrobble.album_name)
        )
        result = await self.execute(query)
        return result.all()

    async def get_tracks_with_no_ref_data(self) -> Any:
        query = (
            select(Scrobble.track_name, Scrobble.artist_name)
            .outerjoin(Track, Scrobble.track_name == Track.title)
            .outerjoin(Artist, Scrobble.artist_name == Artist.name)
            .where(Track.title.is_(None))
            .distinct()
            .order_by(Scrobble.track_name)
        )
        result = await self.execute(query)
        return result.all()

    async def get_top_tracks_by_artist(self, artist_name: str, limit: int = None) -> Any:
        query = (
            select(
                func.max(Scrobble.track_name).label('track_name'),
                func.max(Scrobble.album_name).label('album_name'),
                func.count(Scrobble.id).label('play_count')
            )
            .where(to_lower(Scrobble.artist_name) == to_lower(artist_name))
            .group_by(to_lower(Scrobble.track_name), to_lower(Scrobble.album_name))
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.execute(query)
        return result.all()

    async def get_top_albums_by_artist(self, artist_name: str, limit: int = None) -> Any:
        query = (
            select(
                func.max(Scrobble.album_name).label('album_name'),
                func.count(Scrobble.id).label('play_count')
            )
            .where(to_lower(Scrobble.artist_name) == to_lower(artist_name))
            .group_by(to_lower(Scrobble.album_name))
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.execute(query)
        return result.all()

    async def get_artist_counts_by_year(self, artist_name: str) -> Any:
        query = (
            select(
                func.extract('year', Scrobble.scrobbled_at).label('year'),
                func.count(Scrobble.id).label('play_count')
            )
            .where(Scrobble.artist_name == artist_name)
            .group_by('year')
            .order_by('year')
        )
        result = await self.execute(query)
        return result.all()

    async def get_scrobbles_batch(self, track_data: list[PlayedTrack]) -> list[Scrobble]:
        """
        Efficiently check for existing scrobbles in a sync batch.

        Args:
            track_data: List of PlayedTrack objects from Last.fm API

        Returns:
            List of Scrobble objects that already exist in the database
        """
        if not track_data:
            return []

        conditions = []
        for t in track_data:
            track_name = t.track.title
            artist_name = t.track.artist.name if t.track.artist else "Unknown Artist"
            timestamp = int(t.timestamp)
            scrobbled_at = datetime.fromtimestamp(timestamp)

            condition = (
                    (to_lower(Scrobble.track_name) == to_lower(track_name))
                    & (to_lower(Scrobble.artist_name) == to_lower(artist_name))
                    & (Scrobble.scrobbled_at == scrobbled_at)
            )
            conditions.append(condition)

        if not conditions:
            return []

        query = select(Scrobble).where(or_(*conditions))
        result = await self.execute(query)
        return result.scalars().all()

    async def get_scrobbles_like_track(self, track_name: str, artist_name: str) -> Any:
        # If we passed in "Song Name", ideally we would get results like
        # "Song Name", "Song Name (Remastered)", "Song Name - Single Version", etc.
        query = (
            select(Scrobble)
            .where(like_lower(Scrobble.track_name, f"%{track_name}%"))
            .where(to_lower(Scrobble.artist_name) == to_lower(artist_name))
            .order_by(Scrobble.scrobbled_at)
        )
        result = await self.execute(query)
        return result.scalars().all()

    async def get_top_artists_by_year(self, year: int, limit: int = 10) -> list[tuple[str, int]]:
        query = (
            select(
                Scrobble.artist_name,
                func.count(Scrobble.id).label('play_count')
            )
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .group_by(Scrobble.artist_name)
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.execute(query)
        return result.all()

    async def get_top_tracks_by_year(self, year: int, limit: int = 10) -> list[tuple[str, str, str, int]]:
        query = (
            select(
                Scrobble.track_name,
                Scrobble.artist_name,
                Scrobble.album_name,
                func.count(Scrobble.id).label('play_count')
            )
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .group_by(Scrobble.track_name, Scrobble.artist_name, Scrobble.album_name)
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.execute(query)
        return result.all()

    async def get_top_albums_by_year(self, year: int, limit: int = 10) -> list[tuple[str, str, int]]:
        query = (
            select(
                Scrobble.album_name,
                Scrobble.artist_name,
                func.count(Scrobble.id).label('play_count')
            )
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .group_by(Scrobble.album_name, Scrobble.artist_name)
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.execute(query)
        return result.all()

    async def get_total_scrobbles_by_year(self, year: int) -> int:
        query = (
            select(func.count(Scrobble.id))
            .where(extract('year', Scrobble.scrobbled_at) == year)
        )
        result = await self.execute(query)
        return result.scalar() or 0

    async def get_unique_artists_by_year(self, year: int) -> int:
        query = (
            select(func.count(func.distinct(Scrobble.artist_name)))
            .where(extract('year', Scrobble.scrobbled_at) == year)
        )
        result = await self.execute(query)
        return result.scalar() or 0

    async def get_unique_tracks_by_year(self, year: int) -> int:
        query = (
            select(func.count(func.distinct(Scrobble.track_name)))
            .where(extract('year', Scrobble.scrobbled_at) == year)
        )
        result = await self.execute(query)
        return result.scalar() or 0

    async def get_unique_albums_by_year(self, year: int) -> int:
        query = (
            select(func.count(func.distinct(Scrobble.album_name)))
            .where(extract('year', Scrobble.scrobbled_at) == year)
        )
        result = await self.execute(query)
        return result.scalar() or 0

    async def get_scrobbles_by_month(self, year: int) -> list[tuple[int, int]]:
        query = (
            select(
                extract('month', Scrobble.scrobbled_at).label('month'),
                func.count(Scrobble.id).label('count')
            )
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .group_by('month')
            .order_by('month')
        )
        result = await self.execute(query)
        return result.all()

    async def get_first_scrobble_by_year(self, year: int) -> Optional[Scrobble]:
        query = (
            select(Scrobble)
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .order_by(Scrobble.scrobbled_at.asc())
            .limit(1)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def get_most_active_day_by_year(self, year: int) -> Optional[tuple[str, int]]:
        query = (
            select(
                func.date(Scrobble.scrobbled_at).label('date'),
                func.count(Scrobble.id).label('count')
            )
            .where(extract('year', Scrobble.scrobbled_at) == year)
            .group_by('date')
            .order_by(desc('count'))
            .limit(1)
        )
        result = await self.execute(query)
        return result.first()

    async def get_year_overview(self, year: int) -> dict[str, Any]:
        """Get comprehensive overview of listening stats for a year."""
        return {
            'year': year,
            'total_scrobbles': await self.get_total_scrobbles_by_year(year),
            'unique_artists': await self.get_unique_artists_by_year(year),
            'unique_tracks': await self.get_unique_tracks_by_year(year),
            'unique_albums': await self.get_unique_albums_by_year(year),
            'top_artists': await self.get_top_artists_by_year(year, limit=10),
            'top_tracks': await self.get_top_tracks_by_year(year, limit=10),
            'top_albums': await self.get_top_albums_by_year(year, limit=10),
            'monthly_breakdown': await self.get_scrobbles_by_month(year),
            'first_scrobble': await self.get_first_scrobble_by_year(year),
            'most_active_day': await self.get_most_active_day_by_year(year)
        }

