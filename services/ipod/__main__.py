"""
Inspect a connected iPod without modifying it.

    uv run python -m services.ipod [MOUNT] [--raw]
"""
import argparse
import struct
import sys
from pathlib import Path

from services.ipod.library import ITUNES_DIR, find_ipod_mount, read_library


def format_track(track) -> str:
    return f"{track.artist} - {track.title} [{track.album}]"


def dump_first_mhit(mount: Path) -> None:
    data = (mount / ITUNES_DIR / "iTunesDB").read_bytes()
    offset = data.find(b"mhit")
    header_len = struct.unpack_from("<I", data, offset + 4)[0]
    print(f"\nFirst mhit at offset {offset}, header length {header_len}:")
    for i in range(0, header_len, 16):
        row = data[offset + i:offset + min(i + 16, header_len)]
        print(f"  +{i:3d}: {row.hex(' ')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mount", nargs="?", type=Path, help="iPod mount point (auto-detected under /Volumes)")
    parser.add_argument("--raw", action="store_true", help="hex dump the first track header")
    args = parser.parse_args()

    mount = args.mount or find_ipod_mount()
    if not mount:
        print("No iPod found under /Volumes")
        return 1

    tracks = read_library(mount).tracks
    print(f"iPod at {mount}: {len(tracks)} tracks")

    pending = sorted(
        (t for t in tracks if t.pending_play_count),
        key=lambda t: t.pending_last_played,
    )
    print(f"\nPlayed since last sync: {len(pending)} tracks")
    for track in pending:
        print(f"  {track.pending_last_played:%Y-%m-%d %H:%M}  x{track.pending_play_count}  {format_track(track)}")

    recent = sorted((t for t in tracks if t.last_played), key=lambda t: t.last_played, reverse=True)[:10]
    print("\nMost recent plays already synced to iTunesDB:")
    for track in recent:
        print(f"  {track.last_played:%Y-%m-%d %H:%M}  {track.play_count:4d} plays  {format_track(track)}")

    if args.raw:
        dump_first_mhit(mount)

    return 0


if __name__ == "__main__":
    sys.exit(main())
