import argparse
import asyncio
import signal
import sys

from loguru import logger

from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack, LastFmTrack
from service.apple_music_service import poll_apple_music
from service.lastfm_service import scrobble_to_lastfm, update_lastfm_now_playing
from utils import poll_comparison, song_has_changed, is_same_song, Comparison

bar = "=" * 110
loop = True
active_integration = Integration.APPLE_MUSIC
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


def signal_handler(signal, frame) -> None:
    clear_line()
    asyncio.create_task(stop())


def log_current_song_status(compare: Comparison, poll, current_song) -> None:
    if compare.no_song_playing:
        logger.info("No song is currently playing.")
    else:
        logger.info(f"Apple Music current song: '{poll.clean_name}' by {poll.artist}")
        logger.info("Playing" if poll.playing else "Paused")
        logger.info("Scrobbled" if current_song and current_song.scrobbled else f"Scrobble threshold: {poll.get_scrobbled_threshold()}")


async def monitor_song_playback(current_song) -> None:
    global scrobble_count

    for _ in range(30):
        if not loop:
            break

        new_poll = await poll_apple_music()
        if not new_poll:
            print(f" No song is currently playing...", end="\r")
            await asyncio.sleep(1)
            continue

        if song_has_changed(new_poll, current_song):
            break

        if has_playing_status_changed(new_poll, current_song):
            # Add a small delay to prevent immediate re-entry into the same state
            await asyncio.sleep(2)
            continue

        if current_song and current_song.playing and not current_song.scrobbled:
            current_song.time_played += 1
            print(f" Song: {current_song.name} | Time played: {current_song.time_played}s", end="\r")

            if current_song.is_ready_to_be_scrobbled():
                scrobbled_track = await scrobble_to_lastfm(current_song)
                session_scrobbles.append(scrobbled_track)
                current_song.scrobbled = True
                scrobble_count += 1
                break

        await asyncio.sleep(1)


def has_playing_status_changed(new_poll, current_song) -> bool:
    playing_started = not current_song.playing and new_poll.playing
    playing_stopped = current_song.playing and not new_poll.playing
    return playing_started or playing_stopped


async def run() -> None:
    current_song = None

    if active_integration == Integration.APPLE_MUSIC:
        current_song: AppleMusicTrack | None
    elif active_integration == Integration.SPOTIFY:
        current_song: SpotifyTrack | None

    while loop:
        logger.info(f"Scrobble Count: {scrobble_count}")

        poll = await poll_apple_music()
        compare: Comparison = await poll_comparison(poll, current_song, None)

        log_current_song_status(compare, poll, current_song)

        if compare.update_song:
            current_song = poll
            current_song.time_played = 0

        if compare.update_song_playing_status:
            current_song.playing = poll.playing

        if compare.update_lastfm_now_playing:
            current_song.lastfm_updated_now_playing = await update_lastfm_now_playing(current_song)

        spacer()

        await monitor_song_playback(current_song)

        clear_line()


if __name__ == "__main__":
    handle_arguments()
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    signal.signal(signal.SIGINT, signal_handler)
    event_loop.run_until_complete(run())
