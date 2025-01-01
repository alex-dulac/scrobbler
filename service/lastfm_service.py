import time
from collections import defaultdict
from datetime import datetime, timedelta

import pylast
import requests
from loguru import logger

from config import settings
from models.album import LastFmAlbum
from models.artist import LastFmArtist
from models.lastfm_models import LastFmTopItem
from models.track import AppleMusicTrack, LastFmTrack, Track
from models.user import LastFmUser
from utils import clean_up_title

LASTFM_API_URL = settings.LASTFM_API_URL
LASTFM_API_KEY = settings.LASTFM_API_KEY
LASTFM_API_SECRET = settings.LASTFM_API_SECRET
LASTFM_USERNAME = settings.LASTFM_USERNAME
LASTFM_PASSWORD_HASH = pylast.md5(settings.LASTFM_PASSWORD)

network = pylast.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET,
    username=LASTFM_USERNAME,
    password_hash=LASTFM_PASSWORD_HASH
)


"""
LastFM API related methods
"""


async def get_user() -> pylast.User:
    return network.get_user(settings.LASTFM_USERNAME)


# https://www.last.fm/api/show/user.getInfo
# Manual API call
async def get_lastfm_account_details() -> LastFmUser:
    params = {
        'method': 'user.getInfo',
        'user': LASTFM_USERNAME,
        'api_key': LASTFM_API_KEY,
        'format': 'json'
    }

    response = requests.get(LASTFM_API_URL, params=params)
    user_info = response.json()['user']

    registered_at = None
    if 'unixtime' in user_info['registered']:
        registered_at = datetime.fromtimestamp(int(user_info['registered']['unixtime']))

    playcount = format(int(user_info['playcount']), ',')
    track_count = format(int(user_info['track_count']), ',')
    album_count = format(int(user_info['album_count']), ',')
    artist_count = format(int(user_info['artist_count']), ',')
    image_url = user_info['image'][3]['#text']

    return LastFmUser(
        album_count=album_count,
        artist_count=artist_count,
        country=user_info['country'],
        image_url=image_url,
        name=user_info['name'],
        playcount=playcount,
        realname=user_info['realname'],
        registered=registered_at,
        subscriber=user_info['subscriber'],
        track_count=track_count,
        url=user_info['url']
    )


async def get_user_playcount() -> str:
    user = await get_user()
    playcount = user.get_playcount()
    playcount = format(playcount, ',')
    return playcount


async def get_user_recent_tracks() -> list[list[LastFmTrack | LastFmAlbum | None]]:
    user = await get_user()

    recent_tracks = user.get_recent_tracks(limit=20)
    tracks = []
    for track in recent_tracks:
        scrobbled_at = datetime.fromtimestamp(int(track.timestamp))
        album_name = track.album
        artist_name = track.track.artist.name

        t = LastFmTrack(
            name=track.track.title,
            artist=artist_name,
            album=album_name,
            scrobbled_at=scrobbled_at.strftime(settings.DATETIME_FORMAT)
        )
        a = await get_lastfm_album(album_name, artist_name)

        tracks.append([t, a])

    return tracks


async def get_user_loved_tracks() -> list[LastFmTrack]:
    user = await get_user()

    loved_tracks = user.get_loved_tracks()
    tracks = []
    for track in loved_tracks:
        loved_at = datetime.fromtimestamp(int(track.timestamp))
        t = LastFmTrack(
            name=track.track.title,
            artist=track.track.artist.name,
            loved_at=loved_at.strftime(settings.DATETIME_FORMAT)
        )
        tracks.append(t)

    return tracks


async def get_user_top_artists() -> list[LastFmTopItem]:
    user = await get_user()

    top_artists = user.get_top_artists(limit=10)
    artists = []
    for artist in top_artists:
        details = artist.item
        model = LastFmArtist(
            name=details.name,
            playcount=details.get_playcount(),
            url=details.get_url()
        )
        top_item = LastFmTopItem(
            name=artist.item.name,
            weight=artist.weight,
            details=model
        )
        artists.append(top_item)

    return artists


async def get_user_top_albums() -> list[LastFmTopItem]:
    user = await get_user()

    top_albums = user.get_top_albums(limit=10)
    albums = []
    for album in top_albums:
        details = album.item
        model = LastFmAlbum(
            title=details.title,
            artist=details.artist.name,
            image_url=details.get_cover_image(size=pylast.SIZE_LARGE),
            url=details.get_url()
        )
        top_item = LastFmTopItem(
            name=album.item.title,
            weight=album.weight,
            details=model
        )
        albums.append(top_item)

    return albums


async def update_lastfm_now_playing(current_song: Track) -> bool:
    try:
        network.update_now_playing(
            artist=current_song.artist,
            title=current_song.clean_name,
            album=current_song.clean_album
        )
        logger.info("Updated Last.fm now playing")
        return True
    except pylast.WSError as e:
        logger.error(f"Failed to update Last.fm now playing: {e}")
        return False


async def scrobble_to_lastfm(current_song: Track) -> LastFmTrack | None:
    artist = current_song.artist
    track = current_song.clean_name
    album = current_song.clean_album
    timestamp = int(time.time())

    if artist and track and album:
        try:
            network.scrobble(
                artist=artist,
                title=track,
                timestamp=timestamp,
                album=album
            )
            logger.info(f"Scrobbled to LastFm: {artist} - '{track}'")
            return LastFmTrack(
                name=track,
                artist=artist,
                album=album,
                scrobbled_at=datetime.fromtimestamp(timestamp).strftime(settings.DATETIME_FORMAT)
            )

        except pylast.WSError as e:
            logger.error(f"Failed to scrobble to Last.fm: {e}")
            return None


async def get_album_image_url(album: pylast.Album) -> str | None:
    """
    Retrieves the cover image URL for a given album.

    Attempts to fetch the album's cover image using the provided album object.
    If the initial attempt fails, it tries to clean the album title and fetch
    the cover image again.

    Parameters:
    album (pylast.Album): The album object for which the cover image URL is to be retrieved.

    Returns:
    str | None: The URL of the album's cover image if available, otherwise None.
    """
    image_url = None

    try:
        image_url = album.get_cover_image(size=pylast.SIZE_MEGA)
    except pylast.WSError as e:
        logger.error(f"Failed to get album image_url: {e}")

    if image_url is None:
        clean_title = clean_up_title(album.title)
        clean_album = network.get_album(title=clean_title, artist=album.artist.name)
        try:
            image_url = clean_album.get_cover_image(size=pylast.SIZE_MEGA)
        except pylast.WSError as e:
            logger.error(f"Failed to get album image_url: {e}")

    return image_url


async def get_lastfm_album(title: str, artist: str) -> LastFmAlbum | None:
    album = network.get_album(title=title, artist=artist)

    image_url = await get_album_image_url(album)

    if album:
        return LastFmAlbum(
            title=album.title,
            artist=album.artist.name,
            image_url=image_url,
            url=album.get_url()
        )
    else:
        return None


async def current_track_user_scrobbles(current_song: AppleMusicTrack) -> list[LastFmTrack]:
    user = await get_user()

    # make multiple calls for "Cool Song", "Cool Song (Remastered 2021)", etc...
    track_scrobbles = user.get_track_scrobbles(current_song.artist, current_song.name)
    if current_song.has_clean_name():
        clean_track_scrobbles = user.get_track_scrobbles(current_song.artist, current_song.clean_name)
        track_scrobbles.extend(clean_track_scrobbles)

    tracks = []
    for t in track_scrobbles:
        timestamp = int(t.timestamp)
        timestamp = datetime.fromtimestamp(timestamp).strftime(settings.DATETIME_FORMAT)
        track = LastFmTrack(
            name=t.track.title,
            artist=t.track.artist.name,
            album=t.album,
            scrobbled_at=timestamp
        )
        tracks.append(track)

    return tracks


async def user_weekly_chart_dates():
    user = await get_user()
    return user.get_weekly_chart_dates()


async def user_weekly_album_charts(from_date: str, to_date: str):
    user = await get_user()
    weekly_albums = user.get_weekly_album_charts(from_date, to_date)

    results = []
    for album, playcount in weekly_albums:
        album_name = album.title
        artist_name = album.artist.name

        last_fm_album = await get_lastfm_album(album_name, artist_name)
        last_fm_album.playcount = playcount
        results.append(last_fm_album)

    return results
