import os
import time
from datetime import datetime

import pylast
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
USERNAME = os.getenv('USERNAME')
PASSWORD_HASH = pylast.md5(os.getenv('PASSWORD'))

# Create a Last.fm network object
network = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=USERNAME,
    password_hash=PASSWORD_HASH
)

current_song = {"track": None, "artist": None, "album": None}


def print_current_song():
    currently_playing = current_song["track"]
    if currently_playing:
        print("Apple Music playing: ", currently_playing)
    else:
        print("Apple Music not playing")


def most_recent_scrobble():
    user_lastfm = network.get_user(USERNAME)
    print("LastFM user: ", user_lastfm.name)
    user_recent_tracks = user_lastfm.get_recent_tracks()
    most_recent_scrobble = user_recent_tracks[0]

    timestamp = int(most_recent_scrobble.timestamp)
    scrobbled_at = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    if most_recent_scrobble:
        print("Most recent scrobble: '", most_recent_scrobble.track.title, "' by ",
              most_recent_scrobble.track.artist, " from '", most_recent_scrobble.album, "'")
        print("Scrobbled at ", scrobbled_at)
    else:
        print("No scrobbles yet")


def poll_apple_music():
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
        song = result.split(" - ")
        current_song["track"] = song[0]
        current_song["artist"] = song[1]
        current_song["album"] = song[2]
    else:
        current_song["track"] = None
        current_song["artist"] = None
        current_song["album"] = None


def scrobble_to_lastfm():
    """Scrobble the current song to Last.fm."""
    artist = current_song["artist"]
    track = current_song["track"]
    album = current_song["album"]
    timestamp = int(time.time())

    if artist and track and album:
        try:
            network.scrobble(artist=artist, title=track, timestamp=timestamp, album=album)
            return True
        except pylast.WSError as e:
            print(f"Error: {e}")
            return False


def main():
    last_song = None

    while True:
        poll_apple_music()
        print_current_song()
        most_recent_scrobble()

        if (current_song["track"], current_song["artist"]) != last_song:
            scrobble_to_lastfm()
            last_song = (current_song["track"], current_song["artist"])

        print("------------------")
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()
