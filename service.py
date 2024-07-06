import time
from datetime import datetime

import applescript
import pylast

from config import settings
from model import AppleMusicTrack, LastFmTrack, LastFmUser, LastFmUserStats

LASTFM_API_KEY = settings.LASTFM_API_KEY
LASTFM_API_SECRET = settings.LASTFM_API_SECRET
USERNAME = settings.USERNAME
PASSWORD_HASH = pylast.md5(settings.PASSWORD)

network = pylast.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET,
    username=USERNAME,
    password_hash=PASSWORD_HASH
)


def poll_apple_music() -> AppleMusicTrack | None:
    script = """
    tell application "Music"
        if it is running then
            set currentTrack to the current track
            set trackInfo to (get properties of currentTrack)
            return {trackInfo, player state is playing}
        else
            return {missing value, false}
        end if
    end tell
    """
    try:
        result = applescript.AppleScript(script).run()
        track = result[0]
        playing = result[1]

        if track != applescript.AEType(applescript.kae.cMissingValue):
            return AppleMusicTrack(track_info=track, playing=playing)
        else:
            return None
    except applescript.ScriptError as e:
        if e.number == -1728:
            print("Apple Music is open but no song is selected.")
            return None
        else:
            print("Applescript Error:")
            print(f"{e}")
            return None


def update_lastfm_now_playing(current_song: AppleMusicTrack) -> None:
    try:
        network.update_now_playing(
            artist=current_song.artist,
            title=current_song.name,
            album=current_song.album
        )
        print("Updated Last.fm now playing")
    except pylast.WSError as e:
        print("pylast Error:")
        print(f"{e}")


def scrobble_to_lastfm(current_song: AppleMusicTrack) -> bool:
    artist = current_song.artist
    track = current_song.name
    album = current_song.album
    timestamp = int(time.time())

    if artist and track and album:
        try:
            network.scrobble(artist=artist, title=track, timestamp=timestamp, album=album)
            print("Scrobbled current song to Last.fm")
            return True
        except pylast.WSError as e:
            print("pylast Error:")
            print(f"{e}")
            return False


def get_user() -> pylast.User:
    return network.get_user(settings.USERNAME)


def get_user_minimal() -> LastFmUser:
    user = get_user()
    return LastFmUser(
        name=user.get_name(),
        image_url=user.get_image(),
        url=user.get_url()
    )


def get_user_details() -> LastFmUserStats:
    user = get_user()

    playcount = user.get_playcount()
    playcount = format(playcount, ',')

    recent_tracks = user.get_recent_tracks(limit=20)
    tracks = []
    for track in recent_tracks:
        scrobbled_at = datetime.fromtimestamp(int(track.timestamp))
        tracks.append(LastFmTrack(
            name=track.track.title,
            artist=track.track.artist.name,
            album=track.album,
            scrobbled_at=scrobbled_at.strftime('%Y-%m-%d %H:%M:%S')
        ))

    # loved_tracks = user.get_loved_tracks()
    # top_artists = user.get_top_artists()

    return LastFmUserStats(
        playcount=playcount,
        recent_tracks=tracks,
    )


def get_most_recent_scrobble() -> LastFmTrack | None:
    user_lastfm = get_user()
    user_recent_tracks = user_lastfm.get_recent_tracks()
    most_recent_scrobble = user_recent_tracks[0]
    timestamp = int(most_recent_scrobble.timestamp)
    scrobbled_at = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return LastFmTrack(
        name=most_recent_scrobble.track,
        artist=most_recent_scrobble.track.artist,
        album=most_recent_scrobble.album,
        scrobbled_at=scrobbled_at
    )


"""
PRINT COMMANDS FOR THE LOOP SCRIPT
"""


def print_polled_apple_music_song(current_song: AppleMusicTrack | None) -> None:
    if current_song:
        print("Apple Music current song: ", current_song.name, " by ", current_song.artist)
        print("Song is paused") if not current_song.playing else None
    else:
        print("Apple Music not playing")


def print_most_recent_scrobble() -> None:
    most_recent_scrobble = get_most_recent_scrobble()
    print("Most recent scrobble: '", most_recent_scrobble.name,
          "' by ", most_recent_scrobble.artist,
          " from '", most_recent_scrobble.album,
          "' at ", most_recent_scrobble.scrobbled_at)

