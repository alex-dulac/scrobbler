"""Response contracts for the desktop's local listening library."""
from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    track: str
    artist: str
    album: str | None
    scrobbled_at: datetime


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    page: int
    page_size: int
    total: int


class LibraryYears(BaseModel):
    years: list[int]


class NameCount(BaseModel):
    name: str
    count: int


class AlbumCount(NameCount):
    artist: str


class TrackCount(AlbumCount):
    album: str | None


class ArtistTrackCount(NameCount):
    album: str | None


class MonthCount(BaseModel):
    month: int
    count: int


class YearCount(BaseModel):
    year: int
    count: int


class WrappedSummary(BaseModel):
    year: int
    total_scrobbles: int
    unique_artists: int
    unique_albums: int
    unique_tracks: int
    monthly: list[MonthCount]
    top_artists: list[NameCount]
    top_albums: list[AlbumCount]
    top_tracks: list[TrackCount]


class ArtistSummary(BaseModel):
    artist: str
    total_scrobbles: int
    years: list[YearCount]
    top_albums: list[NameCount]
    top_tracks: list[ArtistTrackCount]


class TrackContext(BaseModel):
    name: str
    artist: str
    total_scrobbles: int
    first_scrobbled_at: datetime | None
    last_scrobbled_at: datetime | None
    years: list[YearCount]
    recent_scrobbles: list[datetime]


class AlbumContext(BaseModel):
    name: str
    artist: str
    total_scrobbles: int
    unique_tracks: int
    first_scrobbled_at: datetime | None
    last_scrobbled_at: datetime | None
    top_tracks: list[NameCount]
    years: list[YearCount]


class ListeningContext(BaseModel):
    track: TrackContext
    album: AlbumContext | None
    artist: ArtistSummary
