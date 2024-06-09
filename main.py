import os
import time
import pylast

API_KEY = ''
API_SECRET = ''
USERNAME = ''
PASSWORD_HASH = pylast.md5('')

# Create a Last.fm network object
network = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=USERNAME,
    password_hash=PASSWORD_HASH
)


def get_current_song():
    """Use osascript to get the currently playing song from Apple Music."""
    script = """
    tell application "Music"
        if it is running then
            if player state is playing then
                set trackName to name of current track
                set artistName to artist of current track
                set albumName to album of current track
                return trackName & " - " & artistName & " - " & albumName
            end if
        end if
        return ""
    end tell
    """
    result = os.popen("osascript -e '{}'".format(script)).read().strip()
    if result:
        track, artist, album = result.split(' - ')
        return track, artist, album
    return None, None, None


def scrobble_to_lastfm(track, artist, album):
    """Scrobble the song to Last.fm."""
    timestamp = int(time.time())
    try:
        network.scrobble(artist=artist, title=track, timestamp=timestamp, album=album)
        print(f"Scrobbled: {track} - {artist} - {album}")
    except pylast.WSError as e:
        print(f"Error: {e}")


def main():
    last_song = None
    while True:
        track, artist, album = get_current_song()
        if track and artist and (track, artist) != last_song:
            scrobble_to_lastfm(track, artist, album)
            last_song = (track, artist)
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()
