from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import (
    Track,
    Album,
    Artist,
    SimilarArtist,
    ArtistTopTrack,
    ArtistTopAlbum,
    ArtistTag,
    AlbumTag,
    AlbumTrack,
    SimilarTrack
)
from repositories.base import BaseRepository


class ReferenceDataRepository(BaseRepository):
    """
    Repository for managing reference data related database operations.
    """
    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)

    async def get_track(self, track_name: str, artist_name: str) -> Any:
        query = (
            select(Track)
            .where(Track.title == track_name)
            .where(Track.artist_name == artist_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def get_album(self, album_name: str, artist_name: str) -> Any:
        query = (
            select(Album)
            .where(Album.title == album_name)
            .where(Album.artist_name == artist_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def get_artist(self, artist_name: str) -> Any:
        query = (
            select(Artist)
            .where(Artist.name == artist_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_similar_artist(self, artist_name: str, similar_artist_name: str) -> Any:
        query = (
            select(SimilarArtist)
            .where(SimilarArtist.artist_name == artist_name)
            .where(SimilarArtist.similar_artist_name == similar_artist_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_top_track(self, artist_name: str, track_name: str) -> Any:
        query = (
            select(ArtistTopTrack)
            .where(ArtistTopTrack.artist_name == artist_name)
            .where(ArtistTopTrack.track_name == track_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_top_album(self, artist_name: str, album_name: str) -> Any:
        query = (
            select(ArtistTopAlbum)
            .where(ArtistTopAlbum.artist_name == artist_name)
            .where(ArtistTopAlbum.album_name == album_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_artist_tag(self, artist_name: str, tag: str) -> Any:
        query = (
            select(ArtistTag)
            .where(ArtistTag.artist_name == artist_name)
            .where(ArtistTag.tag == tag)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_album_tag(self, album_name: str, tag: str, artist_name: str) -> Any:
        query = (
            select(AlbumTag)
            .where(AlbumTag.album_name == album_name)
            .where(AlbumTag.tag == tag)
            .where(AlbumTag.artist_name == artist_name)
        )
        result = await self.execute(query)
        return result.scalar_one_or_none()

    async def check_album_track(self, album_name: str, track_name: str) -> Any:
        query = (
            select(AlbumTrack)
            .where(AlbumTrack.album_name == album_name)
            .where(AlbumTrack.track_name == track_name)
        )
        result = await self.execute(query)
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
        result = await self.execute(query)
        return result.scalar_one_or_none()
