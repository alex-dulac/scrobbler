from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IpodPlayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    track_name: str
    artist_name: str
    album_name: str | None = None
    played_at: datetime
    played_at_estimated: bool


class IpodPlaysResponse(BaseModel):
    plays: list[IpodPlayOut]


class IpodPlaysRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    play_ids: list[int] = Field(min_length=1, max_length=10000)


class IpodCommandResponse(BaseModel):
    message: str
    count: int = 0
