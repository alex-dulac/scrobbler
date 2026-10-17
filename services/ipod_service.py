import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from library.utils import clean_up_title
from models.db import IpodPlay
from models.schemas import Track
from repositories.ipod_repo import IPodRepository
from repositories.scrobble_repo import ScrobbleRepository
from services.ipod import expand_plays, read_library
from services.lastfm_service import LastFmService

"""
iPod related methods
"""

# Last.fm rejects scrobbles older than this
SCROBBLE_WINDOW = timedelta(days=14)


async def capture_plays(mount: Path, repo: IPodRepository) -> int:
    """Store the plays recorded on the iPod since its last sync. Returns the number of new plays."""
    library = await asyncio.to_thread(read_library, mount)
    plays = [play for track in library.tracks if track.is_scrobblable for play in expand_plays(track)]
    captured = await repo.add_plays(plays, library.generation)
    logger.info(f"Captured {captured} new iPod plays ({len(plays)} pending on device)")
    return captured


async def get_pending_plays(repo: IPodRepository) -> list[IpodPlay]:
    """Stored plays awaiting review that are still recent enough for Last.fm to accept."""
    return await repo.get_pending_plays(datetime.now().astimezone() - SCROBBLE_WINDOW)


async def scrobble_plays(
    lastfm: LastFmService,
    repo: IPodRepository,
    scrobble_repo: ScrobbleRepository,
    plays: list[IpodPlay],
) -> tuple[int, int]:
    """Scrobble the given iPod plays, oldest first. Returns (scrobbled, failed) counts."""
    plays = sorted(plays, key=lambda play: play.played_at)

    scrobbled = 0
    for play in plays:
        track = Track(
            name=play.track_name,
            clean_name=clean_up_title(play.track_name),
            artist=play.artist_name,
            album=play.album_name,
            clean_album=clean_up_title(play.album_name) if play.album_name else None,
        )
        lastfm_track = await lastfm.scrobble(track, scrobbled_at=play.played_at)
        if not lastfm_track:
            continue

        await repo.mark_scrobbled(play.id, datetime.now())
        await scrobble_repo.add_scrobble(lastfm_track)
        scrobbled += 1

    return scrobbled, len(plays) - scrobbled
