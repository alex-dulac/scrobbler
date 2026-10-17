from dataclasses import dataclass
from datetime import datetime, timedelta

from services.ipod.itunesdb import IpodTrack


@dataclass(frozen=True, slots=True)
class PendingPlay:
    track: IpodTrack
    # 1-based and chronological within the current Play Counts generation, so the same
    # play keeps its number when the file is read again on a later connection
    play_number: int
    # when the play started, which is what Last.fm expects
    played_at: datetime
    estimated: bool


def expand_plays(track: IpodTrack) -> list[PendingPlay]:
    """
    Split a track's pending play count into individual plays.

    The iPod only records when the most recent play finished, so earlier plays are
    assumed to have run back-to-back before it.
    """
    count = track.pending_play_count
    if not count or not track.pending_last_played:
        return []

    duration = timedelta(milliseconds=track.duration_ms)
    return [
        PendingPlay(
            track=track,
            play_number=n,
            played_at=track.pending_last_played - (count - n + 1) * duration,
            estimated=n != count,
        )
        for n in range(1, count + 1)
    ]
