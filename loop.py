import argparse
import asyncio
import signal
import sys
from collections import Counter

from loguru import logger

from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack, LastFmTrack, Track
from service.apple_music_service import poll_apple_music
from service.lastfm_service import LastFmService
from service.spotify_service import SpotifyService
from utils import poll_comparison, internet

bar = "=" * 110
loop = True
active_integration = Integration.APPLE_MUSIC
lastfm = LastFmService()
spotify = SpotifyService()
scrobble_count = 0
session_scrobbles: [LastFmTrack] = []
pending_scrobbles: [Track] = []


def new_line() -> None:
    print("\n")


def clear_line() -> None:
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()


async def log_current_song(current_song: Track) -> None:
    logger.info(f"{active_integration.normalized_name()} currently playing:")
    logger.info(f"  {current_song.display_name()}")
    logger.info(f"Scrobble threshold: {current_song.get_scrobbled_threshold()}")

    if not await internet():
        logger.info("No internet connection. Cannot get scrobbles for current track...")
        return

    scrobbles = await lastfm.current_track_user_scrobbles(current_song)
    if scrobbles is False:
        return

    if len(scrobbles) > 0:
        logger.info(f"Count of scrobbles for current track: {len(scrobbles)}")
        logger.info(f"First scrobble: {scrobbles[-1].scrobbled_at if scrobbles else 'None'}")
        logger.info(f"Most recent scrobble: {scrobbles[0].scrobbled_at if scrobbles else 'None'}")
    else:
        logger.info("No scrobbles for current track!")


async def run() -> None:
    """
    Creates a continuous loop that polls for the current playing song, updates its status,
    manages Last.fm integration, and monitors playback.
    It's designed to keep track of what's playing and handle scrobbling to Last.fm when appropriate.
    """
    global scrobble_count
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

        if compare.no_song_playing:
            if current_song:
                current_song = None
                new_line()
            print(" No song is currently playing...", end="\r")
            await asyncio.sleep(1)
            continue

        if compare.update_song:
            current_song = poll
            current_song.time_played = 0
            new_line()
            await log_current_song(current_song)
            if compare.update_lastfm_now_playing:
                if not await internet():
                    logger.info("No internet connection. Cannot update Last.fm status...")
                else:
                    current_song.lastfm_updated_now_playing = await lastfm.update_now_playing(current_song)

        if compare.update_song_playing_status:
            current_song.playing = poll.playing

        display_name = f" {current_song.display_name()}"
        time_played = f"Time played: {current_song.time_played}s"

        scrobbled = f"{display_name} | Scrobbled"
        pending = f"{display_name} | Pending Scrobble"
        playing = f"{display_name} | {time_played}"
        paused = f"{playing} | Paused"

        if current_song.playing is False:
            display_status = paused
        elif current_song.scrobbled:
            display_status = scrobbled
        else:
            current_song.time_played += 1
            display_status = playing
            if current_song.is_ready_to_be_scrobbled():
                if not await internet():
                    display_status = pending
                    pending_scrobbles.append(current_song) if current_song not in pending_scrobbles else None
                else:
                    scrobbled_track = await lastfm.scrobble(current_song)
                    if scrobbled_track:
                        session_scrobbles.append(scrobbled_track)
                        pending_scrobbles.remove(current_song) if current_song in pending_scrobbles else None
                        current_song.scrobbled = True
                        scrobble_count += 1
                        logger.info(f"Scrobble Count: {scrobble_count}")
                        display_status = scrobbled

        clear_line()
        print(display_status, end="\r")
        await asyncio.sleep(1)


async def log_session_scrobbles() -> None:
    if len(session_scrobbles) > 0:
        print("Scrobbles during this session:")
        new_line()

        for scrobble in session_scrobbles:
            print(scrobble.display_name())
        new_line()

        artist_counts = Counter(scrobble.artist for scrobble in session_scrobbles)
        song_counts = Counter(scrobble.name for scrobble in session_scrobbles)
        multiple_scrobbles = {song: count for song, count in song_counts.items() if count > 1}

        print("Artist scrobble counts:")
        for artist, count in artist_counts.items():
            print(f"{artist}: {count}")
        new_line()

        if len(multiple_scrobbles) > 0:
            print("Double dippers!:")
            for song, count in multiple_scrobbles.items():
                print(f"{song}: {count} times")
        new_line()
    else:
        print("No scrobbles during this session.")
        new_line()


async def check_pending_scrobbles() -> None:
    if await internet() and len(pending_scrobbles) > 0:
        count = 0
        for track in pending_scrobbles:
            scrobbled_track = await lastfm.scrobble(track)
            if scrobbled_track:
                session_scrobbles.append(scrobbled_track)
                count += 1
        logger.info(f"Scrobbled {count} pending track(s)...")
    elif len(pending_scrobbles) == 0:
        logger.info("No pending scrobbles.")
    else:
        logger.info(f"No internet connection. Skipping {len(pending_scrobbles)} pending scrobble(s)...")


async def stop() -> None:
    global loop
    new_line()

    await check_pending_scrobbles()
    new_line()

    await log_session_scrobbles()

    print(bar)
    print("Thank you for scrobbling. Bye.")
    print(bar)
    new_line()
    loop = False


def signal_handler(signal, frame) -> None:
    clear_line()
    asyncio.create_task(stop())


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


if __name__ == "__main__":
    handle_arguments()
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    signal.signal(signal.SIGINT, signal_handler)
    event_loop.run_until_complete(run())
