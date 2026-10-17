import os
import tempfile
from pathlib import Path
from datetime import UTC, datetime
from collections import Counter
from typing import List, Dict
from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr

from models.schemas import LastFmTrack, Track
from services.lastfm_service import LastFmService
from library.utils import internet


class SessionScrobbles(BaseModel):
    """
    Manages the collection of scrobbled tracks and pending scrobbles during a session.
    Provides methods for adding, retrieving, and analyzing scrobble data.
    """
    scrobbles: List[LastFmTrack] = Field(default_factory=list)
    pending: List[Track] = Field(default_factory=list)
    count: int = 0
    manual_batches: dict[str, int] = Field(default_factory=dict)
    _pending_path: Path | None = PrivateAttr(default=None)

    def attach_pending_store(self, path: Path) -> None:
        """Load durable listens before polling starts; corrupt files fail closed."""
        self._pending_path = path
        if path.exists():
            stored = SessionScrobbles.model_validate_json(path.read_text())
            self.pending = stored.pending
            self.manual_batches = stored.manual_batches

    def _persist_pending(self) -> None:
        if self._pending_path is None:
            return
        path = self._pending_path
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix="pending-")
        try:
            with os.fdopen(descriptor, "w") as output:
                output.write(self.model_dump_json(include={"pending", "manual_batches"}))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


    def add_scrobble(self, track: LastFmTrack) -> None:
        self.scrobbles.append(track)
        self.count += 1
        logger.info(f"Scrobble Count: {self.count}")

    @staticmethod
    def _same_listen(first: Track, second: Track) -> bool:
        return (
            first.listening_started_at == second.listening_started_at
            and first.artist == second.artist
            and first.name == second.name
            and first.album == second.album
        )

    def add_pending(self, track: Track) -> None:
        if track.listening_started_at is None:
            track.listening_started_at = datetime.now(UTC)
        if not any(self._same_listen(track, pending) for pending in self.pending):
            self.pending.append(track)
            try:
                self._persist_pending()
            except Exception:
                self.pending.remove(track)
                raise
            logger.info(f"Added track to pending scrobbles: {track.display_name}")

    def add_pending_batch(self, batch_id: str, tracks: list[Track]) -> int:
        """Commit the batch and idempotency receipt in a single atomic file replacement."""
        if batch_id in self.manual_batches:
            return self.manual_batches[batch_id]
        copies = [track.model_copy(deep=True) for track in tracks]
        previous = self.pending.copy()
        self.pending.extend(copies)
        self.manual_batches[batch_id] = len(tracks)
        try:
            self._persist_pending()
        except Exception:
            self.pending = previous
            self.manual_batches.pop(batch_id, None)
            raise
        return len(tracks)

    def remove_pending(self, track: Track) -> None:
        for pending in self.pending:
            if self._same_listen(track, pending):
                self.pending.remove(pending)
                self._persist_pending()
                break

    async def process_pending_scrobbles(self, lastfm_service: LastFmService) -> int:
        """
        Process all pending scrobbles if internet is available.
        Returns the number of successfully processed scrobbles.
        """
        internet_available = await internet()

        if not internet_available or not self.pending:
            if not internet_available:
                logger.info(f"No internet connection. Skipping {len(self.pending)} pending scrobble(s)...")
            elif not self.pending:
                logger.info("No pending scrobbles.")
            return 0

        processed_count = 0
        pending_copy = self.pending.copy()

        for track in pending_copy:
            scrobbled_track = await lastfm_service.scrobble(track, scrobbled_at=track.listening_started_at)
            if scrobbled_track:
                self.add_scrobble(scrobbled_track)
                self.remove_pending(track)
                processed_count += 1

        logger.info(f"Scrobbled {processed_count} pending track(s)...")
        return processed_count

    def get_artist_counts(self) -> Dict[str, int]:
        return Counter(scrobble.artist for scrobble in self.scrobbles)

    def get_song_counts(self) -> Dict[str, int]:
        return Counter(scrobble.name for scrobble in self.scrobbles)

    def get_multiple_scrobbles(self) -> Dict[str, int]:
        song_counts = self.get_song_counts()
        return {song: count for song, count in song_counts.items() if count > 1}

    def get_session_summary(self) -> str:
        if not self.scrobbles:
            return "No scrobbles during this session."

        summary = ["Scrobbles during this session:"]

        for scrobble in self.scrobbles:
            summary.append(f"  {scrobble.display_name}")

        summary.append("")

        # Artist counts
        summary.append("Artist scrobble counts:")
        for artist, count in self.get_artist_counts().items():
            summary.append(f"  {artist}: {count}")

        summary.append("")

        # Multiple scrobbles
        multiple = self.get_multiple_scrobbles()
        if multiple:
            summary.append("Double dippers!:")
            for song, count in multiple.items():
                summary.append(f"  {song}: {count} times")

        return "\n".join(summary)

    def __len__(self) -> int:
        """Return the number of scrobbles in the session."""
        return len(self.scrobbles)

    def __bool__(self) -> bool:
        """Return True if there are any scrobbles in the session."""
        return bool(self.scrobbles)