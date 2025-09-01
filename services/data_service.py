from datetime import datetime
from typing import Tuple, Sequence, Any

from loguru import logger
from sqlalchemy import select, Select, Row

from db.tables import (
    Scrobble,
    Track,
    Album,
    Artist,
    SimilarArtist,
    ArtistTopTrack,
    ArtistTag,
    AlbumTag,
    AlbumTrack,
    SimilarTrack,
    ArtistTopAlbum
)
from services.base_db_service import BaseDbService


class ScrobbleFilter:
    def __init__(
        self,
        track_name: str = None,
        artist_name: str = None,
        album_name: str = None,
        scrobbled_after: str = None,
        scrobbled_before: str = None
    ):
        self.track_name = track_name
        self.artist_name = artist_name
        self.album_name = album_name
        self.scrobbled_after = scrobbled_after
        self.scrobbled_before = scrobbled_before


async def build_query(filter: ScrobbleFilter) -> Select[Tuple[Scrobble]]:
    query = select(Scrobble)

    if filter is None:
        return query

    if filter.track_name:
        query = query.where(Scrobble.track_name == filter.track_name)

    if filter.artist_name:
        query = query.where(Scrobble.artist_name == filter.artist_name)

    if filter.album_name:
        query = query.where(Scrobble.album_name == filter.album_name)

    if filter.scrobbled_after:
        after_date = datetime.strptime(filter.scrobbled_after, "%Y-%m-%d")
        query = query.where(Scrobble.scrobbled_at >= after_date)

    if filter.scrobbled_before:
        before_date = datetime.strptime(filter.scrobbled_before, "%Y-%m-%d")
        query = query.where(Scrobble.scrobbled_at <= before_date)

    query = query.order_by(Scrobble.scrobbled_at.desc())

    return query


distinct_albums = Sequence[Row[tuple[Scrobble.album_name, Scrobble.artist_name]]]
distinct_tracks = Sequence[Row[tuple[Scrobble.track_name, Scrobble.artist_name]]]


class DataService(BaseDbService):
    """
    Service for interacting with data in the database.
    Last.fm's API is limited when it comes to querying a user's library.
    By syncing the user's scrobbles to a database, we can run sql against it.
    """
    async def get_scrobbles(self, filter: ScrobbleFilter = None) -> Sequence[Scrobble]:
        query = await build_query(filter)
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

    async def get_albums_from_scrobbles(self) -> distinct_albums:
        query = (
            select(Scrobble.album_name, Scrobble.artist_name)
            .distinct()
            .order_by(Scrobble.album_name)
        )
        result = await self.db.execute(query)
        return result.all()

    async def get_tracks_from_scrobbles(self) -> distinct_tracks:
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
        logger.info(f"Looking up album '{album_name}' by artist '{artist_name}'")
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
