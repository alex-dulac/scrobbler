import time
from datetime import datetime

import pylast

from config import settings
from model import AppleMusicTrack, LastFmTrack, LastFmUser, LastFmAlbum, LastFmTopItem, LastFmArtist

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


"""
LastFM API related methods
"""


def get_user() -> pylast.User:
    return network.get_user(settings.USERNAME)


def get_user_minimal() -> LastFmUser:
    user = get_user()
    return LastFmUser(
        name=user.get_name(),
        image_url=user.get_image(),
        url=user.get_url()
    )


def get_user_playcount() -> str:
    user = get_user()
    playcount = user.get_playcount()
    playcount = format(playcount, ',')
    return playcount


def get_user_recent_tracks() -> list[LastFmTrack]:
    user = get_user()

    recent_tracks = user.get_recent_tracks(limit=20)
    tracks = []
    for track in recent_tracks:
        scrobbled_at = datetime.fromtimestamp(int(track.timestamp))
        tracks.append(
            LastFmTrack(
                name=track.track.title,
                artist=track.track.artist.name,
                album=track.album,
                scrobbled_at=scrobbled_at.strftime('%Y-%m-%d %H:%M:%S')
            )
        )

    return tracks


def get_user_loved_tracks() -> list[LastFmTrack]:
    user = get_user()

    loved_tracks = user.get_loved_tracks()
    tracks = []
    for track in loved_tracks:
        loved_at = datetime.fromtimestamp(int(track.timestamp))
        tracks.append(
            LastFmTrack(
                name=track.track.title,
                artist=track.track.artist.name,
                loved_at=loved_at.strftime('%Y-%m-%d %H:%M:%S')
            )
        )

    return tracks


def get_user_top_artists() -> list[LastFmTopItem]:
    user = get_user()

    top_artists = user.get_top_artists(limit=10)
    artists = []
    for artist in top_artists:
        details: pylast.Artist = artist.item
        model = LastFmArtist(
            name=details.name,
            playcount=details.get_playcount(),
            url=details.get_url()
        )

        artists.append(
            LastFmTopItem(
                name=artist.item.name,
                weight=artist.weight,
                details=model
            )
        )

    return artists


def get_user_top_albums() -> list[LastFmTopItem]:
    user = get_user()

    top_albums = user.get_top_albums(limit=10)
    albums = []
    for album in top_albums:
        details: pylast.Album = album.item
        model = LastFmAlbum(
            title=details.title,
            artist=details.artist.name,
            image_url=details.get_cover_image(size=pylast.SIZE_LARGE),
            url=details.get_url()
        )

        albums.append(
            LastFmTopItem(
                name=album.item.title,
                weight=album.weight,
                details=model
            )
        )

    return albums


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


def get_most_recent_scrobble() -> LastFmTrack | None:
    user_lastfm = get_user()
    user_recent_tracks = user_lastfm.get_recent_tracks()
    most_recent_scrobble = user_recent_tracks[0]
    timestamp = int(most_recent_scrobble.timestamp)
    scrobbled_at = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    return LastFmTrack(
        name=most_recent_scrobble.track.title,
        artist=most_recent_scrobble.track.artist.name,
        album=most_recent_scrobble.album,
        scrobbled_at=scrobbled_at
    )


def get_lastfm_album(title: str, artist: str) -> LastFmAlbum | None:
    album = network.get_album(title=title, artist=artist)
    if album:
        return LastFmAlbum(
            title=album.title,
            artist=album.artist.name,
            image_url=album.get_cover_image(),
            url=album.get_url()
        )
    else:
        return None


def print_most_recent_scrobble() -> None:
    most_recent_scrobble = get_most_recent_scrobble()
    print("Most recent scrobble: '", most_recent_scrobble.name,
          "' by ", most_recent_scrobble.artist,
          " from '", most_recent_scrobble.album,
          "' at ", most_recent_scrobble.scrobbled_at)

