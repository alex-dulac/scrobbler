from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class BaseTable(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)

class Scrobble(BaseTable):
    __tablename__ = "scrobbles"

    track_name = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    album_name = Column(String, nullable=True)
    scrobbled_at = Column(DateTime, default=datetime.now(), nullable=False)

    def __repr__(self):
        return f"<Scrobble(track_name='{self.track_name}', artist_name='{self.artist_name}')>"

"""
NOTE: The following tables are designed based on the Last.fm API responses and may not cover all possible fields.
Also, Last.fm is `name` based... therefore we need to join on names which is not ideal.
The MusicBrainz ID (mbid) is not always available in responses, so going with `name` as de facto primary key.
"""

"""
Track based tables:
"""
class Track(BaseTable):
    # note: tags don't seem to return anything for tracks via the Lastfm API
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    album_name = Column(String, nullable=True)
    mbid = Column(String, index=True, nullable=True)
    duration = Column(Integer, nullable=True)  # duration in milliseconds
    url = Column(String, nullable=True)
    wiki = Column(String, nullable=True)
    cover_image = Column(String, nullable=True)
    user_loved = Column(Boolean, default=False, nullable=False)
    user_playcount = Column(Integer, nullable=True)
    listener_count = Column(Integer, nullable=True)
    listener_playcount = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)

    def __repr__(self):
        return f"<Track(title='{self.title}', artist_name='{self.artist_name}')>"


class SimilarTrack(BaseTable):
    __tablename__ = "similar_tracks"

    track_name = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    similar_track_name = Column(String, index=True, nullable=False)
    similar_track_artist_name = Column(String, index=True, nullable=False)
    match = Column(Float, nullable=False)

"""
Artist based tables:
"""
class Artist(BaseTable):
    __tablename__ = "artists"

    name = Column(String, unique=True, index=True, nullable=False)
    mbid = Column(String, index=True, nullable=True)
    url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    user_playcount = Column(Integer, nullable=True)
    listener_count = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Artist(name='{self.name}')>"


class ArtistTopTrack(BaseTable):
    __tablename__ = "artist_top_tracks"

    artist_name = Column(String, index=True, nullable=False)
    track_name = Column(String, index=True, nullable=False)
    weight = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)


class ArtistTopAlbum(BaseTable):
    __tablename__ = "artist_top_albums"

    artist_name = Column(String, index=True, nullable=False)
    album_name = Column(String, index=True, nullable=False)
    weight = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)


class ArtistTag(BaseTable):
    __tablename__ = "artist_tags"

    artist_name = Column(String, index=True, nullable=False)
    tag = Column(String, index=True, nullable=False)
    weight = Column(Integer, nullable=False)


class SimilarArtist(BaseTable):
    __tablename__ = "similar_artists"

    artist_name = Column(String, index=True, nullable=False)
    similar_artist_name = Column(String, index=True, nullable=False)
    match = Column(Float, nullable=False)

"""
Album based tables:
"""
class Album(BaseTable):
    __tablename__ = "albums"

    title = Column(String, nullable=False)
    artist_name = Column(String, nullable=False)
    mbid = Column(String, index=True, nullable=True)
    url = Column(String, nullable=True)
    wiki = Column(String, nullable=True)
    cover_image = Column(String, nullable=True)
    user_playcount = Column(Integer, nullable=True)
    listener_count = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Album(title='{self.title}', artist_name='{self.artist_name}')>"

class AlbumTrack(BaseTable):
    __tablename__ = "album_tracks"

    album_name = Column(String, index=True, nullable=False)
    track_name = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    order = Column(Integer, nullable=False)

class AlbumTag(BaseTable):
    __tablename__ = "album_tags"

    album_name = Column(String, index=True, nullable=False)
    tag = Column(String, index=True, nullable=False)
    artist_name = Column(String, index=True, nullable=False)
    weight = Column(Integer, nullable=False)
