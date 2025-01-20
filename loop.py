import argparse
import asyncio
import signal
import sys

from loguru import logger

from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack, LastFmTrack
from service.apple_music_service import poll_apple_music
from service.lastfm_service import LastFmService
from service.spotify_service import SpotifyService
from utils import poll_comparison, song_has_changed, Comparison

bar = "=" * 110
loop = True
active_integration = Integration.APPLE_MUSIC
lastfm = LastFmService()
spotify = SpotifyService()
scrobble_count = 0
session_scrobbles: [LastFmTrack] = []


def new_line() -> None:
    print("\n")


def spacer() -> None:
    print(bar)


def clear_line() -> None:
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()


async def stop() -> None:
    global loop
    global session_scrobbles
    new_line()

    if len(session_scrobbles) > 0:
        print("Scrobbles during this session:")
        new_line()

        for scrobble in session_scrobbles:
            print(scrobble.name)
            print(scrobble.artist)
            print(scrobble.album)
            print(scrobble.scrobbled_at)
            new_line()

    spacer()
    print("Thank you for scrobbling. Bye.")
    spacer()
    new_line()
    loop = False


def handle_arguments() -> None:
    global active_integration

    parser = argparse.ArgumentParser()
    parser.add_argument("--integration", type=str, required=False)

    args = parser.parse_args()
    if args.integration:
        match args.integration.upper():
            case Integration.APPLE_MUSIC.name:
                active_integration = Integration.APPLE_MUSIC
            case Integration.SPOTIFY.name:
                active_integration = Integration.SPOTIFY
            case _:
                raise ValueError(f"Invalid integration: {args.integration.upper()}")

    logger.info(f"Active Integration: {active_integration.name}")


def signal_handler(signal, frame) -> None:
    clear_line()
    asyncio.create_task(stop())


async def log_current_song(compare: Comparison, current_song) -> None:
    logger.info(f"Scrobble Count: {scrobble_count}")

    if compare.no_song_playing:
        return logger.info("No song is currently playing.")

    logger.info(f"Current song: {current_song.display_name()}")
    logger.info("Scrobbled" if current_song.scrobbled else f"Scrobble threshold: {current_song.get_scrobbled_threshold()}")

    scrobbles = await lastfm.current_track_user_scrobbles(current_song)
    logger.info(f"Count of scrobbles for current track: {len(scrobbles)}")


async def monitor_song_playback(current_song, poll_service) -> None:
    """
    Monitors the current playing song, updates its status,
    and handles scrobbling to Last.fm when appropriate.
    It provides real-time updates on the console about the current song's status.
    """
    global scrobble_count

    while loop:
        new_poll = await poll_service()
        if not new_poll:
            print(" No song is currently playing...", end="\r")
            await asyncio.sleep(1)
            continue

        if song_has_changed(new_poll, current_song):
            break

        if not current_song:
            await asyncio.sleep(1)
            continue

        if current_song.playing != new_poll.playing:
            current_song.playing = new_poll.playing

        if current_song.scrobbled:
            status = f" Song: {current_song.display_name()} | Scrobbled"

        elif current_song.playing:
            current_song.time_played += 1
            status = f" Song: {current_song.display_name()} | Time played: {current_song.time_played}s"

            if current_song.is_ready_to_be_scrobbled():
                scrobbled_track = await lastfm.scrobble_to_lastfm(current_song)
                session_scrobbles.append(scrobbled_track)
                current_song.scrobbled = True
                scrobble_count += 1
                status = f" Song: {current_song.display_name()} | Scrobbled"

        else:
            status = f" Song: {current_song.display_name()} | Time played: {current_song.time_played}s | Paused"

        clear_line()
        print(status, end="\r")
        await asyncio.sleep(1)


async def run() -> None:
    """
    Creates a continuous loop that polls for the current playing song, updates its status,
    manages Last.fm integration, and monitors playback.
    It's designed to keep track of what's playing and handle scrobbling to Last.fm when appropriate.
    """
    current_song = None
    poll_service = None

    if active_integration == Integration.APPLE_MUSIC:
        current_song: AppleMusicTrack | None
        poll_service = poll_apple_music
    elif active_integration == Integration.SPOTIFY:
        current_song: SpotifyTrack | None
        poll_service = spotify.poll_spotify

    while loop:
        poll = await poll_service()
        compare = await poll_comparison(poll, current_song, None)

        if compare.update_song:
            current_song = poll
            current_song.time_played = 0

        if compare.update_song_playing_status:
            current_song.playing = poll.playing

        await log_current_song(compare, current_song)

        if compare.update_lastfm_now_playing:
            current_song.lastfm_updated_now_playing = await lastfm.update_lastfm_now_playing(current_song)

        spacer()

        await monitor_song_playback(current_song, poll_service)

        clear_line()


if __name__ == "__main__":
    handle_arguments()
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    signal.signal(signal.SIGINT, signal_handler)
    event_loop.run_until_complete(run())
