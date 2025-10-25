from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.db import (
    Album,
    AlbumTag,
    AlbumTrack,
    Artist,
    ArtistTag,
    ArtistTopAlbum,
    ArtistTopTrack,
    Scrobble,
    Track,
    SimilarArtist,
    SimilarTrack
)
from repositories.filters import ScrobbleFilter, build_query


class ScrobbleRepository:
    """
    Repository for interacting with data in the database.
    Last.fm's API is limited when it comes to querying a user's library.
    By syncing the user's scrobbles to a database, we can run sql against it.
    This class provides methods to add and query data in the database.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_and_commit(self, objs: list[Any]) -> Any:
        self.db.add_all(objs)
        return await self.db.commit()

    async def get_scrobbles(self, f: ScrobbleFilter = None) -> Any:
        query = await build_query(f)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_artists_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.artist_name)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_albums_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.album_name, Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.album_name)
        )
        result = await self.db.execute(query)
        return result.all()

    async def get_tracks_from_scrobbles(self) -> Any:
        query = (
            select(Scrobble.track_name, Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.track_name)
        )
        result = await self.db.execute(query)
        return result.all()

    async def get_track(self, track_name: str, artist_name: str) -> Any:
        query = (
            select(Track)
            .where(Track.title == track_name)
            .where(Track.artist_name == artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_album(self, album_name: str, artist_name: str) -> Any:
        query = (
            select(Album)
            .where(Album.title == album_name)
            .where(Album.artist_name == artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_artist(self, artist_name: str) -> Any:
        query = (
            select(Artist)
            .where(Artist.name == artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_similar_artist(self, artist_name: str, similar_artist_name: str) -> Any:
        query = (
            select(SimilarArtist)
            .where(SimilarArtist.artist_name == artist_name)
            .where(SimilarArtist.similar_artist_name == similar_artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_top_track(self, artist_name: str, track_name: str) -> Any:
        query = (
            select(ArtistTopTrack)
            .where(ArtistTopTrack.artist_name == artist_name)
            .where(ArtistTopTrack.track_name == track_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_top_album(self, artist_name: str, album_name: str) -> Any:
        query = (
            select(ArtistTopAlbum)
            .where(ArtistTopAlbum.artist_name == artist_name)
            .where(ArtistTopAlbum.album_name == album_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_tag(self, artist_name: str, tag: str) -> Any:
        query = (
            select(ArtistTag)
            .where(ArtistTag.artist_name == artist_name)
            .where(ArtistTag.tag == tag)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_album_tag(self, album_name: str, tag: str, artist_name: str) -> Any:
        query = (
            select(AlbumTag)
            .where(AlbumTag.album_name == album_name)
            .where(AlbumTag.tag == tag)
            .where(AlbumTag.artist_name == artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_album_track(self, album_name: str, track_name: str) -> Any:
        query = (
            select(AlbumTrack)
            .where(AlbumTrack.album_name == album_name)
            .where(AlbumTrack.track_name == track_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_similar_track(
            self,
            track_name: str,
            artist_name: str,
            similar_track_name: str,
            similar_track_artist_name: str
    ) -> Any:
        query = (
            select(SimilarTrack)
            .where(SimilarTrack.track_name == track_name)
            .where(SimilarTrack.artist_name == artist_name)
            .where(SimilarTrack.similar_track_name == similar_track_name)
            .where(SimilarTrack.similar_track_artist_name == similar_track_artist_name)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_artists_with_no_ref_data(self) -> Any:
        query = (
            select(Scrobble.artist_name)
            .outerjoin(Artist, Scrobble.artist_name == Artist.name)
            .where(Artist.name.is_(None))
            .distinct()
            .order_by(Scrobble.artist_name)
        )
        result = await self.db.execute(query)
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
        result = await self.db.execute(query)
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
        result = await self.db.execute(query)
        return result.all()


    async def get_top_tracks_by_artist(self, artist_name: str, limit: int = None) -> Any:
        query = (
            select(
                Scrobble.track_name,
                Scrobble.album_name,
                func.count(Scrobble.id).label('play_count')
            )
            .where(Scrobble.artist_name == artist_name)
            .group_by(Scrobble.track_name, Scrobble.album_name)
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.all()

    async def get_top_albums_by_artist(self, artist_name: str, limit: int = None) -> Any:
        query = (
            select(
                Scrobble.album_name,
                func.count(Scrobble.id).label('play_count')
            )
            .where(Scrobble.artist_name == artist_name)
            .group_by(Scrobble.album_name)
            .order_by(desc('play_count'))
            .limit(limit)
        )
        result = await self.db.execute(query)
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
        result = await self.db.execute(query)
        return result.all()


@asynccontextmanager
async def get_scrobble_repository():
    async with get_db() as session:
        yield ScrobbleRepository(db=session)
