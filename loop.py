import asyncio
import signal

from loguru import logger

from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack
from service.apple_music_service import poll_apple_music
from service.lastfm_service import scrobble_to_lastfm, update_lastfm_now_playing
from utils import poll_comparison, validate_scrobble_in_loop

bar = "=" * 130
loop = True
wait = 30


async def stop() -> None:
    global loop
    print("\n")
    print(bar)
    print("Exiting...")
    print(bar)
    print("\n")
    loop = False


def signal_handler(signal, frame) -> None:
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

    loop_count = 0
    scrobble_count = 0

    while loop:
        loop_count += 1
        logger.info(f"Loop #{loop_count}")
        logger.info(f"Scrobble Count: {scrobble_count}")

        poll = await poll_apple_music()
        if poll:
            logger.info(f"Apple Music current song: '{poll.name}' by {poll.artist}")
            logger.info(f"Playing" if poll.playing else "Paused")
        else:
            logger.info("No song is currently playing.")

        compare = await poll_comparison(poll, current_song, None)

        if compare["update_song"]:
            current_song = poll

        if compare["update_song_playing_status"]:
            current_song.playing = poll.playing

        if compare["update_lastfm_now_playing"]:
            await update_lastfm_now_playing(current_song)
            current_song.lastfm_updated_now_playing = True

        if await validate_scrobble_in_loop(current_song, previous_song):
            await scrobble_to_lastfm(current_song)
            current_song.scrobbled = True
            previous_song = current_song
            scrobble_count += 1

        print(bar)

        for i in range(wait):
            if not loop:
                break
            print(f"{'.' * (i + 1)}", end="\r")
            await asyncio.sleep(1)

        print(bar) if loop else None


if __name__ == "__main__":
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    signal.signal(signal.SIGINT, signal_handler)
    event_loop.run_until_complete(run())
