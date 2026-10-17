"""Reviewable album listens; submissions reference immutable, short-lived previews."""
import asyncio

from datetime import UTC, datetime, timedelta
import math
from uuid import uuid4

from models.manual_schemas import AlbumPreview, ManualTrack, ManualSubmitResponse
from models.schemas import Track


class ManualScrobbleService:
    PREVIEW_LIFETIME = timedelta(minutes=30)

    def __init__(self):
        self._previews: dict[str, AlbumPreview] = {}

    @classmethod
    def validate_time(cls, value: datetime, now: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Listening time must include a timezone")
        if value > now:
            raise ValueError("Listening time cannot be in the future")

    async def preview(self, lastfm, *, artist: str, album: str, finished_at: datetime) -> AlbumPreview:
        now = datetime.now(UTC)
        self.validate_time(finished_at, now)
        async with asyncio.timeout(35):
            result = await lastfm.get_album(album, artist, with_tracks=True)
        if result is None or not result.tracks:
            raise ValueError("No album track list was found")
        durations = [track.duration / 1000 for track in result.tracks]
        if any(not math.isfinite(duration) or duration <= 0 for duration in durations):
            raise ValueError("Last.fm is missing track durations; an accurate listening timeline cannot be created")
        if not any(duration > 30 for duration in durations):
            raise ValueError("This album has no tracks longer than 30 seconds eligible for scrobbling")
        started = finished_at.astimezone(UTC) - timedelta(seconds=sum(durations))
        self.validate_time(started, datetime.now(UTC))
        tracks = []
        for track, duration in zip(result.tracks, durations):
            if not track.name or not (track.artist or result.artist_name):
                raise ValueError("The album track list has incomplete metadata")
            tracks.append(ManualTrack(name=track.name, artist=track.artist or result.artist_name,
                                      album=result.title or album, duration_seconds=duration, started_at=started,
                                      eligible=duration > 30))
            started += timedelta(seconds=duration)
        self._previews = {key: value for key, value in self._previews.items() if value.expires_at > now}
        if len(self._previews) >= 100:
            raise ValueError("Too many active previews; wait for an earlier preview to expire")
        preview = AlbumPreview(preview_id=uuid4().hex, artist=result.artist_name or artist,
                               album=result.title or album, artwork_url=result.cover_image,
                               tracks=tracks, expires_at=now + self.PREVIEW_LIFETIME)
        self._previews[preview.preview_id] = preview.model_copy(deep=True)
        return preview

    async def submit(self, runtime, preview_id: str) -> ManualSubmitResponse:
        receipt = runtime.snapshot().session.manual_batches.get(preview_id)
        if receipt is not None:
            return ManualSubmitResponse(queued=True, count=receipt, message="This reviewed album was already queued")
        preview = self._previews.get(preview_id)
        now = datetime.now(UTC)
        if preview is None or preview.expires_at <= now:
            raise ValueError("Preview expired or is unavailable; review the album again")
        self.validate_time(preview.tracks[0].started_at, now)
        tracks = [Track(name=track.name, clean_name=track.name, artist=track.artist,
                        album=track.album, clean_album=track.album, duration=track.duration_seconds,
                        listening_started_at=track.started_at) for track in preview.tracks if track.eligible]
        count = await runtime.enqueue_manual(preview_id, tracks)
        paused = not runtime.snapshot().scrobble_enabled
        return ManualSubmitResponse(queued=True, count=count,
            message="Album queued; enable scrobbling to submit" if paused else "Album queued for submission")
