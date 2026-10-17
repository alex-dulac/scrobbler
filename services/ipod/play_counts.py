"""
Reader for the Play Counts file on an iPod Classic (iPod_Control/iTunes/Play Counts).

The iPod never rewrites iTunesDB itself. Plays, skips and rating changes made on the
device are recorded here instead, and Finder/iTunes merges them into iTunesDB and
deletes this file on the next sync.

Layout reference: libgpod (src/itdb_itunesdb.c). The mhdp header holds the header
length (+4), entry length (+8) and entry count (+12). Entries carry no track id: entry N
belongs to the Nth mhit in iTunesDB's track list.
"""
import struct
from dataclasses import dataclass
from datetime import datetime

from services.ipod.itunesdb import ITunesDBError, mac_timestamp_to_datetime


@dataclass(frozen=True, slots=True)
class PlayCountEntry:
    # plays since the last sync, not the lifetime total
    play_count: int
    # only the most recent play is timestamped
    last_played: datetime | None
    bookmark_ms: int
    rating: int | None = None
    skip_count: int = 0
    last_skipped: datetime | None = None


def parse_play_counts(data: bytes) -> list[PlayCountEntry]:
    try:
        return _parse_entries(data)
    except struct.error as e:
        raise ITunesDBError(f"Truncated Play Counts file: {e}") from e


def _parse_entries(data: bytes) -> list[PlayCountEntry]:
    if data[:4] != b"mhdp":
        raise ITunesDBError(f"Expected b'mhdp' at offset 0, found {data[:4]!r}")

    header_len, entry_len, entry_count = struct.unpack_from("<III", data, 4)

    entries = []
    for i in range(entry_count):
        offset = header_len + i * entry_len
        play_count, last_played, bookmark_ms = struct.unpack_from("<III", data, offset)

        # Entry length grew across firmware versions: 0x0c, 0x10, 0x14, 0x1c
        rating = None
        skip_count = 0
        last_skipped = None
        if entry_len >= 0x10:
            rating = struct.unpack_from("<I", data, offset + 12)[0]
        if entry_len >= 0x1c:
            skip_count, raw_last_skipped = struct.unpack_from("<II", data, offset + 20)
            last_skipped = mac_timestamp_to_datetime(raw_last_skipped)

        entries.append(PlayCountEntry(
            play_count=play_count,
            last_played=mac_timestamp_to_datetime(last_played),
            bookmark_ms=bookmark_ms,
            rating=rating,
            skip_count=skip_count,
            last_skipped=last_skipped,
        ))

    return entries
