import struct
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from services.ipod import ITunesDBError, parse_itunesdb, parse_play_counts, read_library
from services.ipod.itunesdb import mac_timestamp_to_datetime
from services.ipod.library import ITUNES_DIR

# 1970-01-01 expressed in seconds since 1904-01-01
UNIX_EPOCH_IN_MAC = 2082844800


def mac_time(dt: datetime) -> int:
    return UNIX_EPOCH_IN_MAC + int((dt - datetime(1970, 1, 1)).total_seconds())


def build_mhod(mhod_type: int, text: str) -> bytes:
    encoded = text.encode("utf-16-le")
    body = struct.pack("<IIII", 1, len(encoded), 1, 0) + encoded
    return b"mhod" + struct.pack("<IIIII", 24, 24 + len(body), mhod_type, 0, 0) + body


def build_mhit(
    track_id: int,
    dbid: int,
    title: str,
    artist: str,
    album: str,
    play_count: int = 0,
    last_played: int = 0,
    duration_ms: int = 0,
    skip_count: int = 0,
    header_len: int = 0x184,
) -> bytes:
    mhods = build_mhod(1, title) + build_mhod(4, artist) + build_mhod(3, album)
    header = bytearray(header_len)
    header[0:4] = b"mhit"
    struct.pack_into("<IIII", header, 4, header_len, header_len + len(mhods), 3, track_id)
    struct.pack_into("<I", header, 40, duration_ms)
    struct.pack_into("<I", header, 80, play_count)
    struct.pack_into("<I", header, 88, last_played)
    struct.pack_into("<Q", header, 112, dbid)
    if header_len >= 164:
        struct.pack_into("<I", header, 156, skip_count)
    return bytes(header) + mhods


def build_mhsd(dataset_type: int, child: bytes) -> bytes:
    return b"mhsd" + struct.pack("<III", 96, 96 + len(child), dataset_type) + bytes(80) + child


def build_itunesdb(tracks: list[bytes]) -> bytes:
    track_list = b"mhlt" + struct.pack("<II", 92, len(tracks)) + bytes(80) + b"".join(tracks)
    # Real databases often put the album list (type 4) before the tracks
    body = build_mhsd(4, b"mhla" + bytes(8)) + build_mhsd(1, track_list)
    header = bytearray(104)
    header[0:4] = b"mhbd"
    struct.pack_into("<IIIII", header, 4, 104, 104 + len(body), 1, 0x75, 2)
    return bytes(header) + body


def build_play_counts(entries: list[tuple[int, int, int]], entry_len: int = 0x1c) -> bytes:
    header_len = 0x60
    data = bytearray(b"mhdp" + struct.pack("<III", header_len, entry_len, len(entries)))
    data += bytes(header_len - len(data))
    for play_count, last_played, skip_count in entries:
        entry = bytearray(entry_len)
        struct.pack_into("<III", entry, 0, play_count, last_played, 0)
        if entry_len >= 0x1c:
            struct.pack_into("<I", entry, 20, skip_count)
        data += entry
    return bytes(data)


PLAYED_AT = datetime(2026, 10, 12, 18, 30)

SAMPLE_DB = build_itunesdb([
    build_mhit(1455, 0xAABBCCDD11223344, "I Hate Children", "Adolescents", "The Adolescents",
               play_count=3, last_played=mac_time(PLAYED_AT), duration_ms=95000, skip_count=1),
    build_mhit(1460, 0x0102030405060708, "Wrecking Crew", "Adolescents", "The Adolescents"),
])


class MacTimestampTest(unittest.TestCase):
    def test_converts_from_1904_epoch_as_local_time(self):
        result = mac_timestamp_to_datetime(mac_time(PLAYED_AT))
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(result.replace(tzinfo=None), PLAYED_AT)

    def test_zero_means_never(self):
        self.assertIsNone(mac_timestamp_to_datetime(0))


class ITunesDBParserTest(unittest.TestCase):
    def test_parses_track_fields(self):
        tracks = parse_itunesdb(SAMPLE_DB)

        self.assertEqual(len(tracks), 2)
        track = tracks[0]
        self.assertEqual(track.index, 0)
        self.assertEqual(track.track_id, 1455)
        self.assertEqual(track.dbid, 0xAABBCCDD11223344)
        self.assertEqual(track.title, "I Hate Children")
        self.assertEqual(track.artist, "Adolescents")
        self.assertEqual(track.album, "The Adolescents")
        self.assertEqual(track.duration_ms, 95000)
        self.assertEqual(track.play_count, 3)
        self.assertEqual(track.skip_count, 1)
        self.assertEqual(track.last_played.replace(tzinfo=None), PLAYED_AT)

        self.assertEqual(tracks[1].index, 1)
        self.assertIsNone(tracks[1].last_played)

    def test_short_header_skips_newer_fields(self):
        db = build_itunesdb([build_mhit(1, 2, "Title", "Artist", "Album", skip_count=5, header_len=0x9c)])
        track = parse_itunesdb(db)[0]
        self.assertEqual(track.title, "Title")
        self.assertEqual(track.skip_count, 0)
        self.assertIsNone(track.media_type)

    def test_rejects_non_itunesdb(self):
        with self.assertRaises(ITunesDBError):
            parse_itunesdb(b"not an itunes database")

    def test_rejects_truncated_db(self):
        with self.assertRaises(ITunesDBError):
            parse_itunesdb(SAMPLE_DB[:300])


class PlayCountsParserTest(unittest.TestCase):
    def test_parses_entries(self):
        entries = parse_play_counts(build_play_counts([(2, mac_time(PLAYED_AT), 1), (0, 0, 0)]))

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].play_count, 2)
        self.assertEqual(entries[0].last_played.replace(tzinfo=None), PLAYED_AT)
        self.assertEqual(entries[0].skip_count, 1)
        self.assertIsNone(entries[1].last_played)

    def test_short_entries_have_no_skip_data(self):
        entries = parse_play_counts(build_play_counts([(1, mac_time(PLAYED_AT), 4)], entry_len=0x10))
        self.assertEqual(entries[0].play_count, 1)
        self.assertEqual(entries[0].skip_count, 0)


class ReadLibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mount = Path(self.tmp.name)
        self.itunes_dir = self.mount / ITUNES_DIR
        self.itunes_dir.mkdir(parents=True)
        (self.itunes_dir / "iTunesDB").write_bytes(SAMPLE_DB)

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_play_counts_file(self):
        tracks = read_library(self.mount).tracks
        self.assertEqual([t.pending_play_count for t in tracks], [0, 0])

    def test_generation_changes_only_when_itunesdb_changes(self):
        generation = read_library(self.mount).generation

        (self.itunes_dir / "Play Counts").write_bytes(build_play_counts([(1, mac_time(PLAYED_AT), 0), (0, 0, 0)]))
        self.assertEqual(read_library(self.mount).generation, generation)

        (self.itunes_dir / "iTunesDB").write_bytes(build_itunesdb([build_mhit(1, 2, "Title", "Artist", "Album")]))
        (self.itunes_dir / "Play Counts").unlink()
        self.assertNotEqual(read_library(self.mount).generation, generation)

    def test_attaches_play_counts_by_position(self):
        played_at = mac_time(PLAYED_AT + timedelta(days=1))
        (self.itunes_dir / "Play Counts").write_bytes(build_play_counts([(0, 0, 0), (4, played_at, 2)]))

        tracks = read_library(self.mount).tracks

        self.assertEqual(tracks[0].pending_play_count, 0)
        self.assertEqual(tracks[1].title, "Wrecking Crew")
        self.assertEqual(tracks[1].pending_play_count, 4)
        self.assertEqual(tracks[1].pending_skip_count, 2)
        self.assertEqual(tracks[1].pending_last_played.replace(tzinfo=None), PLAYED_AT + timedelta(days=1))

    def test_rejects_mismatched_play_counts(self):
        (self.itunes_dir / "Play Counts").write_bytes(build_play_counts([(1, 0, 0)]))
        with self.assertRaises(ITunesDBError):
            read_library(self.mount)


if __name__ == "__main__":
    unittest.main()
