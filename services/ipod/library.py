import hashlib
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from services.ipod.itunesdb import ITunesDBError, IpodTrack, parse_itunesdb
from services.ipod.play_counts import parse_play_counts

ITUNES_DIR = Path("iPod_Control") / "iTunes"
VOLUMES_DIR = Path("/Volumes")


@dataclass(slots=True)
class IpodLibrary:
    tracks: list[IpodTrack]
    # Hash of iTunesDB. The iPod never writes iTunesDB itself; only a host does, and a
    # host clears Play Counts when it does. So pending play counts keep accumulating
    # for as long as this value stays the same.
    generation: str


def find_ipod_mount(volumes_dir: Path = VOLUMES_DIR) -> Path | None:
    if not volumes_dir.exists():
        return None

    for volume in sorted(volumes_dir.iterdir()):
        if (volume / ITUNES_DIR / "iTunesDB").is_file():
            return volume

    return None


def read_library(mount: Path) -> IpodLibrary:
    """
    Read every track on the iPod, with plays made since the last sync attached
    as pending_* fields when the Play Counts file is present.
    """
    itunes_dir = Path(mount) / ITUNES_DIR

    # Read Play Counts first: Apple Music deletes it as soon as the iPod is opened there
    play_counts_path = itunes_dir / "Play Counts"
    play_counts_data = play_counts_path.read_bytes() if play_counts_path.is_file() else None

    itunesdb_data = (itunes_dir / "iTunesDB").read_bytes()
    library = IpodLibrary(
        tracks=parse_itunesdb(itunesdb_data),
        generation=hashlib.sha1(itunesdb_data).hexdigest(),
    )
    tracks = library.tracks

    if play_counts_data is None:
        logger.info("No Play Counts file on iPod; it has been synced since its last plays.")
        return library

    entries = parse_play_counts(play_counts_data)

    # Entries are matched to tracks by position, so any mismatch would attribute plays
    # to the wrong tracks
    if len(entries) != len(tracks):
        raise ITunesDBError(
            f"Play Counts has {len(entries)} entries but iTunesDB has {len(tracks)} tracks"
        )

    for track, entry in zip(tracks, entries):
        track.pending_play_count = entry.play_count
        track.pending_last_played = entry.last_played
        track.pending_skip_count = entry.skip_count

    return library
