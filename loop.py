import argparse
import asyncio
import signal
import sys

from loguru import logger

from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack, LastFmTrack
from service.apple_music_service import poll_apple_music
from service.lastfm_service import scrobble_to_lastfm, update_lastfm_now_playing
from utils import poll_comparison, validate_scrobble_in_loop

bar = "=" * 110
loop = True
active_integration = Integration.APPLE_MUSIC
session_scrobbles: [LastFmTrack] = []


def new_line() -> None:
    print("\n")

def spacer() -> None:
    print(bar)


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
    sys.stdout.write("\r" + " " * 110 + "\r")  # Clear the line
    sys.stdout.flush()
    asyncio.create_task(stop())


async def run() -> None:
    current_song = None
    previous_song = None

    if active_integration == Integration.APPLE_MUSIC:
        current_song: AppleMusicTrack | None
        previous_song: AppleMusicTrack | None
    elif active_integration == Integration.SPOTIFY:
        current_song: SpotifyTrack | None
        previous_song: SpotifyTrack | None

    scrobble_count = 0

    while loop:
        logger.info(f"Scrobble Count: {scrobble_count}")

        poll = await poll_apple_music()
        if poll:
            logger.info(f"Apple Music current song: '{poll.name}' by {poll.artist}")
            logger.info(f"Playing" if poll.playing else "Paused")
        else:
            logger.info("No song is currently playing.")

        compare = await poll_comparison(poll, current_song, None)

        if compare.update_song:
            current_song = poll
            current_song.time_played = 0

        if compare.update_song_playing_status:
            current_song.playing = poll.playing

        if compare.update_lastfm_now_playing:
            await update_lastfm_now_playing(current_song)
            current_song.lastfm_updated_now_playing = True

        spacer()

        # Poll every second for 30 seconds, break for certain conditions
        for _ in range(30):
            if not loop:
                break

            new_poll = await poll_apple_music()

            # Check if the song has changed
            if new_poll and (not current_song or new_poll.id != current_song.id):
                logger.info(f"Song changed to: '{new_poll.name}' by {new_poll.artist}")
                current_song = new_poll
                current_song.time_played = 0
                break

            # Break the loop if the song changes from playing to not playing, or vice versa
            playing_started = not current_song.playing and new_poll.playing
            playing_stopped = current_song.playing and not new_poll.playing
            if current_song and new_poll and current_song.id == new_poll.id and (playing_stopped or playing_started):
                logger.info(f"Song '{current_song.name}' changed from playing to paused")
                break

            if current_song and current_song.playing and not current_song.scrobbled:
                scrobble_threshold = min(current_song.duration / 2, 120)  # Half duration or 2 minutes, whichever is less
                current_song.time_played += 1
                print(f"Song: {current_song.name} | Time played: {current_song.time_played}s", end="\r")

                if current_song.time_played >= scrobble_threshold:
                    logger.info(f"Scrobble threshold reached for '{current_song.name}'")
                    if await validate_scrobble_in_loop(current_song, previous_song):
                        scrobbled_track = await scrobble_to_lastfm(current_song)
                        session_scrobbles.append(scrobbled_track)
                        current_song.scrobbled = True
                        previous_song = current_song
                        scrobble_count += 1
                    break

            await asyncio.sleep(1)

        sys.stdout.write("\r" + " " * 110 + "\r")  # Clear the line
        sys.stdout.flush()


if __name__ == "__main__":
    handle_arguments()
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    signal.signal(signal.SIGINT, signal_handler)
    event_loop.run_until_complete(run())
