from collections import Counter
from typing import List, Dict
from loguru import logger

from models.track import Track, LastFmTrack
from service.lastfm_service import LastFmService
from utils import internet


class SessionScrobbles:
    """
    Manages the collection of scrobbled tracks and pending scrobbles during a session.
    Provides methods for adding, retrieving, and analyzing scrobble data.
    """
    def __init__(self, lastfm_service: LastFmService):
        self.scrobbles: List[LastFmTrack] = []
        self.pending: List[Track] = []
        self.lastfm = lastfm_service
        self.count = 0

    def add_scrobble(self, track: LastFmTrack) -> None:
        self.scrobbles.append(track)
        self.count += 1
        logger.info(f"Scrobble Count: {self.count}")

    def add_pending(self, track: Track) -> None:
        if track not in self.pending:
            self.pending.append(track)
            logger.info(f"Added track to pending scrobbles: {track.display_name()}")

    def remove_pending(self, track: Track) -> None:
        if track in self.pending:
            self.pending.remove(track)

    async def process_pending_scrobbles(self) -> int:
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
            scrobbled_track = await self.lastfm.scrobble(track)
            if scrobbled_track:
                self.add_scrobble(scrobbled_track)
                self.remove_pending(track)
                processed_count += 1

        logger.info(f"Scrobbled {processed_count} pending track(s)...")
        return processed_count

    def get_artist_counts(self) -> Dict[str, int]:
        """Return a dictionary of artist names and their scrobble counts."""
        return Counter(scrobble.artist for scrobble in self.scrobbles)

    def get_song_counts(self) -> Dict[str, int]:
        """Return a dictionary of song names and their scrobble counts."""
        return Counter(scrobble.name for scrobble in self.scrobbles)

    def get_multiple_scrobbles(self) -> Dict[str, int]:
        """Return songs that have been scrobbled more than once."""
        song_counts = self.get_song_counts()
        return {song: count for song, count in song_counts.items() if count > 1}

    def get_session_summary(self) -> str:
        """Generate a formatted summary of the session's scrobbles."""
        if not self.scrobbles:
            return "No scrobbles during this session."

        summary = ["Scrobbles during this session:"]

        # List all scrobbles
        for scrobble in self.scrobbles:
            summary.append(f"  {scrobble.display_name()}")

        summary.append("")  # Empty line

        # Artist counts
        summary.append("Artist scrobble counts:")
        for artist, count in self.get_artist_counts().items():
            summary.append(f"  {artist}: {count}")

        summary.append("")  # Empty line

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