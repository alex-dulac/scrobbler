import time
from service import (
    print_current_song,
    poll_apple_music,
    print_most_recent_scrobble,
    scrobble_to_lastfm
)


def main():
    """
    Main function to continuously poll Apple Music for the current song,
    print the most recent scrobble, and scrobble the current song to Last.fm if it hasn't been scrobbled yet.

    This function runs an infinite loop that performs the following steps every 30 seconds:
    1. Prints the most recent scrobble from Last.fm.
    2. Polls Apple Music to get the current song being played.
    3. Prints the current song information.
    4. Checks if the current song has been scrobbled to Last.fm. If not, it scrobbles the song and prints the most recent scrobble again.
    5. Prints a separator line for readability.
    6. Sleeps for 30 seconds before repeating the process.

    Note:
        This function runs indefinitely until manually stopped.
    """
    while True:
        print_most_recent_scrobble()

        poll = poll_apple_music()
        if poll
        print_current_song(current_song)

        if current_song and current_song.scrobbled is False:
            scrobble_to_lastfm(current_song)
            current_song.scrobbled = True
            print_most_recent_scrobble()

        print("------------------")
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
