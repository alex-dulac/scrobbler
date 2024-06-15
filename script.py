import time
from service import (
    print_current_song,
    poll_apple_music,
    print_most_recent_scrobble,
    scrobble_to_lastfm
)


def main():
    last_song = None

    while True:
        current_song = poll_apple_music()
        print_current_song(current_song)
        print_most_recent_scrobble()

        if current_song != last_song:
            scrobble_to_lastfm(current_song)
            last_song = current_song

        print("------------------")
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()
