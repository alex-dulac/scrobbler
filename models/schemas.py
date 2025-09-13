from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator, HttpUrl


class Artist(BaseModel):
    id: str = None
    name: str = None
    url: HttpUrl = None
    playcount: str = None
    image_url: str = None


class Album(BaseModel):
    title: str = None
    artist_name: str = None
    release_date: str = None
    image_url: str = None
    url: str = None
    tracks: list[str] = None
    playcount: int = None


class Track(BaseModel):
    name: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    playing: bool = False
    time_played: int = 0
    duration: int = 0
    scrobbled: bool = False
    lastfm_updated_now_playing: bool = False
    clean_name: Optional[str] = None
    clean_album: Optional[str] = None

    class Config:
        extra = "allow"
        from_attributes = True

    @field_validator("time_played", "duration", mode="before")
    def _coerce_non_negative_int(cls, v):
        try:
            n = int(v or 0)
        except (TypeError, ValueError):
            n = 0
        return max(n, 0)

    @field_validator("clean_name", mode="after")
    def _default_clean_name(cls, v, info):
        return v if v is not None else info.data.get("name")

    @field_validator("clean_album", mode="after")
    def _default_clean_album(cls, v, info):
        return v if v is not None else info.data.get("album")

    @property
    def has_clean_name(self) -> bool:
        return self.name != self.clean_name

    @property
    def display_name(self) -> str:
        return f"`{self.clean_name}` by {self.artist} from `{self.clean_album}`"

    @property
    def scrobble_threshold(self) -> int:
        return min(round(self.duration / 2), 120) if self.duration else 120

    @property
    def is_ready_to_be_scrobbled(self) -> bool:
        return self.playing and not self.scrobbled and self.time_played >= self.scrobble_threshold

    @property
    def time_remaining(self) -> int:
        return max(self.duration - self.time_played, 0)


class AppleMusicTrack(Track):
    id: Optional[int] = None
    index: Optional[int] = None
    persistent_id: Optional[str] = None
    time: Optional[str] = None
    album_artist: Optional[str] = None
    composer: Optional[str] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    year: Optional[int] = None
    release_date: Optional[datetime] = None
    loved: Optional[bool] = None
    disliked: Optional[bool] = None
    album_loved: Optional[bool] = None
    album_disliked: Optional[bool] = None

    @classmethod
    def from_apple_event(cls, track_info: Dict[Any, Any], playing: bool = False) -> "AppleMusicTrack":
        ae_type_map = {
            "AEType(b'ID  ')": "id",
            "AEType(b'pidx')": "index",
            "AEType(b'pnam')": "name",
            "AEType(b'pPIS')": "persistent_id",
            "AEType(b'pTim')": "time",
            "AEType(b'pDur')": "duration",
            "AEType(b'pArt')": "artist",
            "AEType(b'pAlA')": "album_artist",
            "AEType(b'pCmp')": "composer",
            "AEType(b'pAlb')": "album",
            "AEType(b'pGen')": "genre",
            "AEType(b'pTrN')": "track_number",
            "AEType(b'pDsN')": "disc_number",
            "AEType(b'pYr ')": "year",
            "AEType(b'pRlD')": "release_date",
            "AEType(b'pLov')": "loved",
            "AEType(b'pHat')": "disliked",
            "AEType(b'pALv')": "album_loved",
            "AEType(b'pAHt')": "album_disliked",
        }

        mapped: Dict[str, Any] = {}
        for key, value in track_info.items():
            attr_name = ae_type_map.get(str(key))
            if attr_name:
                mapped[attr_name] = value

        mapped["playing"] = playing
        return cls(**mapped)

class LastFmTrack(Track):
    scrobbled_at: Optional[str] = None
    loved_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "artist": self.artist,
            "album": self.album,
            "scrobbled_at": self.scrobbled_at,
            "loved_at": self.loved_at,
            "clean_name": self.clean_name,
            "clean_album": self.clean_album,
        }


class SpotifyTrack(Track):
    pass


class User(BaseModel):
    name: str
    url: Optional[HttpUrl] = None

    class Config:
        extra = "allow"


class LastFmUser(User):
    album_count: Optional[str] = None
    artist_count: Optional[str] = None
    country: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    playcount: Optional[str] = None
    realname: Optional[str] = None
    registered: Optional[datetime] = None
    subscriber: bool = False
    track_count: Optional[str] = None


class SpotifyUser(User):
    images: Optional[List[dict]] = None
    product: Optional[str] = None

    def is_premium(self) -> bool:
        return self.product == "premium"

    def is_free(self) -> bool:
        return self.product == "free"


class TopItemType(Enum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"


class TopItem(BaseModel):
    name: str = None
    weight: int = None
    item_type: TopItemType = None
    details: Artist | Album | Track = None


class MacOS(BaseModel):
    user_name: str = None
    long_user_name: str = None
    user_id: int = None
    home_dir: str = None
    boot_volume: str = None
    system_version: str = None
    cpu_type: str = None
    physical_memory: int = None
    user_locale: str = None

