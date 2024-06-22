import time

from model import AppleMusicTrack
from service import (
    print_polled_apple_music_song,
    poll_apple_music,
    print_most_recent_scrobble,
    scrobble_to_lastfm,
)


def main():
    """
    Main function to poll Apple Music for the currently playing song and scrobble it to Last.fm if it hasn't been scrobbled yet.

    This function runs an infinite loop that:
    - Polls the currently playing song from Apple Music.
    - Prints the most recent scrobble from Last.fm.
    - Checks if the currently playing song has changed.
    - Scrobbles the new song to Last.fm if it hasn't been scrobbled yet.
    - Waits for 30 seconds before polling again.

    The loop can be interrupted with a KeyboardInterrupt (Ctrl+C), which will gracefully exit the loop.

    Variables:
    - current_song: Stores the currently playing song.
    - previous_song: Stores the previously scrobbled song.
    - loop_count: Counts the number of iterations of the loop.
    - scrobble_count: Counts the number of songs scrobbled to Last.fm.
    """
    current_song: AppleMusicTrack | None = None
    previous_song: AppleMusicTrack | None = None

    loop_count = 0
    scrobble_count = 0

    bar = "==============================="

    try:
        while True:
            loop_count += 1
            print(f"Loop #{loop_count}")
            print(f"Scrobbles: {scrobble_count}")

            print_most_recent_scrobble()

            poll = poll_apple_music()
            print_polled_apple_music_song(poll)

            if poll and (current_song is None or (current_song.track_id != poll.track_id)):
                current_song = poll

            if current_song and current_song.scrobbled:
                print("Current song has already been scrobbled.")

            if (current_song is not None and not current_song.scrobbled and
                    (not previous_song or (previous_song and current_song.track_id != previous_song.track_id))):
                scrobble_to_lastfm(current_song)
                current_song.scrobbled = True
                previous_song = current_song
                scrobble_count += 1

            print(bar)
            print("\n")

            wait = '.'
            for i in range(30):
                print(f" Waiting{wait}", end="\r")
                wait += "."
                time.sleep(1)

            print("\n\n")
            print(bar)

    except KeyboardInterrupt:
        print("\n\n")
        print(bar)
        print("Exiting...")
        print(bar)
        print("\n\n")


if __name__ == "__main__":
    main()
