"""
Reader for the iTunesDB file on an iPod Classic (iPod_Control/iTunes/iTunesDB).

Layout reference: libgpod (src/itdb_itunesdb.c). All integers are little-endian.
Every record starts with a 4-byte tag followed by its header length at +4 and,
for most records, its total length (header + children) at +8.

    mhbd                    database
      mhsd (type 1)         track dataset
        mhlt                track list
          mhit              track
            mhod            string field (title, artist, ...)
      mhsd (other types)    playlists, albums, etc. (skipped)
"""
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta

MAC_EPOCH = datetime(1904, 1, 1)

TRACK_DATASET = 1

# mhod types holding strings we care about
STRING_FIELDS = {
    1: "title",
    2: "location",
    3: "album",
    4: "artist",
    5: "genre",
    6: "file_type",
    12: "composer",
    22: "album_artist",
}

# mhod string encodings (stored in the mhod's sub-header)
UTF8_ENCODING = 2

# mhit media type flags
PODCAST_MEDIA_TYPE = 0x04
AUDIOBOOK_MEDIA_TYPE = 0x08


class ITunesDBError(ValueError):
    pass


def mac_timestamp_to_datetime(value: int) -> datetime | None:
    """iPod timestamps are seconds since 1904-01-01 in the device's local time."""
    if value == 0:
        return None
    return (MAC_EPOCH + timedelta(seconds=value)).astimezone()


@dataclass(slots=True)
class IpodTrack:
    # position in the track list; the Play Counts file is keyed by this
    index: int
    track_id: int
    # 64-bit id that survives syncs, unlike track_id
    dbid: int
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    genre: str | None = None
    composer: str | None = None
    location: str | None = None
    file_type: str | None = None
    duration_ms: int = 0
    track_number: int = 0
    disc_number: int = 0
    year: int = 0
    rating: int = 0
    play_count: int = 0
    last_played: datetime | None = None
    skip_count: int = 0
    last_skipped: datetime | None = None
    date_added: datetime | None = None
    media_type: int | None = None
    # plays recorded on the device since the last sync (from the Play Counts file)
    pending_play_count: int = 0
    pending_last_played: datetime | None = None
    pending_skip_count: int = 0

    @property
    def is_scrobblable(self) -> bool:
        spoken_word = (self.media_type or 0) & (PODCAST_MEDIA_TYPE | AUDIOBOOK_MEDIA_TYPE)
        return bool(self.title and self.artist and not spoken_word)


def _u8(data: bytes, offset: int) -> int:
    return data[offset]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def _expect_tag(data: bytes, offset: int, tag: bytes) -> None:
    found = data[offset:offset + 4]
    if found != tag:
        raise ITunesDBError(f"Expected {tag!r} at offset {offset}, found {found!r}")


def parse_itunesdb(data: bytes) -> list[IpodTrack]:
    try:
        return _parse_database(data)
    except struct.error as e:
        raise ITunesDBError(f"Truncated iTunesDB: {e}") from e


def _parse_database(data: bytes) -> list[IpodTrack]:
    _expect_tag(data, 0, b"mhbd")
    header_len = _u32(data, 4)
    end = min(_u32(data, 8), len(data))

    offset = header_len
    while offset < end:
        _expect_tag(data, offset, b"mhsd")
        dataset_header_len = _u32(data, offset + 4)
        dataset_len = _u32(data, offset + 8)
        dataset_type = _u32(data, offset + 12)

        if dataset_type == TRACK_DATASET:
            return _parse_track_list(data, offset + dataset_header_len)

        offset += dataset_len

    raise ITunesDBError("No track dataset found in iTunesDB")


def _parse_track_list(data: bytes, offset: int) -> list[IpodTrack]:
    _expect_tag(data, offset, b"mhlt")
    header_len = _u32(data, offset + 4)
    track_count = _u32(data, offset + 8)

    tracks = []
    offset += header_len
    for index in range(track_count):
        track, track_len = _parse_track(data, offset, index)
        tracks.append(track)
        offset += track_len

    return tracks


def _parse_track(data: bytes, offset: int, index: int) -> tuple[IpodTrack, int]:
    _expect_tag(data, offset, b"mhit")
    header_len = _u32(data, offset + 4)
    total_len = _u32(data, offset + 8)
    mhod_count = _u32(data, offset + 12)

    track = IpodTrack(
        index=index,
        track_id=_u32(data, offset + 16),
        dbid=_u64(data, offset + 112),
        rating=_u8(data, offset + 31),
        duration_ms=_u32(data, offset + 40),
        track_number=_u32(data, offset + 44),
        year=_u32(data, offset + 52),
        play_count=_u32(data, offset + 80),
        last_played=mac_timestamp_to_datetime(_u32(data, offset + 88)),
        disc_number=_u32(data, offset + 92),
        date_added=mac_timestamp_to_datetime(_u32(data, offset + 104)),
    )

    # Fields added in later database versions; older headers stop short of them
    if header_len >= 164:
        track.skip_count = _u32(data, offset + 156)
        track.last_skipped = mac_timestamp_to_datetime(_u32(data, offset + 160))
    if header_len >= 212:
        track.media_type = _u32(data, offset + 208)

    mhod_offset = offset + header_len
    for _ in range(mhod_count):
        _expect_tag(data, mhod_offset, b"mhod")
        mhod_len = _u32(data, mhod_offset + 8)
        mhod_type = _u32(data, mhod_offset + 12)

        field_name = STRING_FIELDS.get(mhod_type)
        if field_name:
            setattr(track, field_name, _parse_string_mhod(data, mhod_offset))

        mhod_offset += mhod_len

    return track, total_len


def _parse_string_mhod(data: bytes, offset: int) -> str:
    # String mhods have a 16-byte sub-header after the common header:
    # encoding (+0), byte length (+4), two unknowns, then the string itself
    string_header = offset + _u32(data, offset + 4)
    encoding = _u32(data, string_header)
    length = _u32(data, string_header + 4)
    raw = data[string_header + 16:string_header + 16 + length]

    if encoding == UTF8_ENCODING:
        return raw.decode("utf-8", errors="replace")
    return raw.decode("utf-16-le", errors="replace")
