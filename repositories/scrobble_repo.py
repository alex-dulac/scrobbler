from typing import Any, Optional

from sqlalchemy import select, func, desc
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


