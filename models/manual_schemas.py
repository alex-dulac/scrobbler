from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManualTrack(BaseModel):
    name: str
    artist: str
    album: str
    duration_seconds: float
    started_at: datetime
    eligible: bool = True


class AlbumPreview(BaseModel):
    preview_id: str
    artist: str
    album: str
    artwork_url: str | None = None
    tracks: list[ManualTrack]
    expires_at: datetime


class ManualSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=64)


class ManualSubmitResponse(BaseModel):
    queued: bool
    count: int
    message: str
