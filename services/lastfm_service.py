import time
from collections import defaultdict
from datetime import datetime, timedelta

import httpx
import pylast
import requests
from loguru import logger

from core import config
from library.utils import clean_up_title, lastfm_friendly
from models.schemas import LastFmUser, LastFmTrack, TopItem, Artist, Album, Track, SimilarTrack
from services.base_async_client import BaseAsyncClient

LASTFM_API_URL = config.LASTFM_API_URL
LASTFM_API_KEY = config.LASTFM_API_KEY
LASTFM_API_SECRET = config.LASTFM_API_SECRET
LASTFM_USERNAME = config.LASTFM_USERNAME
LASTFM_PASSWORD_HASH = pylast.md5(config.LASTFM_PASSWORD)


user_params = {
    'method': 'user.getInfo',
    'user': LASTFM_USERNAME,
    'api_key': LASTFM_API_KEY,
    'format': 'json'
}


def format_user_response(user_info: dict) -> LastFmUser:
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


# https://www.last.fm/api/show/user.getInfo
# Manual API call
async def get_lastfm_user() -> LastFmUser:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(LASTFM_API_URL, params=user_params)
            response.raise_for_status()
            user_info = response.json()['user']
    except httpx.TimeoutException:
        raise Exception("Last.fm API request timed out")
    except httpx.HTTPError as e:
        raise Exception(f"Last.fm API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching user info: {str(e)}")

    return format_user_response(user_info)


def get_lastfm_account_details() -> LastFmUser:
    """Deprecated: Use async version `get_lastfm_user` instead."""
    try:
        response = requests.get(LASTFM_API_URL, params=user_params)
        user_info = response.json()['user']
    except requests.RequestException as e:
        raise Exception(f"Last.fm API error: {str(e)}")

    return format_user_response(user_info)


"""
LastFM API related methods using pylast library
"""
class LastFmService(BaseAsyncClient):
    """
    Service for interacting with the Last.fm API using pylast.
    Pylast makes synchronous calls, so requests are run in a thread pool to avoid blocking.
    """
    def __init__(self):
        super().__init__()
        self.network = pylast.LastFMNetwork(
            api_key=LASTFM_API_KEY,
            api_secret=LASTFM_API_SECRET,
            username=LASTFM_USERNAME,
            password_hash=LASTFM_PASSWORD_HASH
        )
        self.user: pylast.User = self.network.get_user(LASTFM_USERNAME)
        logger.info(f"User {LASTFM_USERNAME} successfully authenticated")

    async def get_user_playcount(self) -> str:
        playcount = await self._run_sync(self.user.get_playcount)
        return format(int(playcount), ',')

    async def get_user_recent_tracks(self) -> list[LastFmTrack]:
        recent_tracks = await self._run_sync(
            self.user.get_recent_tracks,
            limit=20
        )
        tracks = []
        for track in recent_tracks:
            try:
                # Note: Using `lambda t=track:` to capture the current track reference properly in the loop
                timestamp = await self._run_sync(lambda t=track: int(t.timestamp))
                scrobbled_at = datetime.fromtimestamp(timestamp)

                album_name = await self._run_sync(lambda t=track: t.album)
                artist_name = await self._run_sync(lambda t=track: t.track.artist.name)
                track_title = await self._run_sync(lambda t=track: t.track.title)

                lft = LastFmTrack(
                    name=track_title,
                    artist=artist_name,
                    album=album_name,
                    scrobbled_at=scrobbled_at
                )
                tracks.append(lft)
            except Exception as e:
                logger.error(f"Failed to process track: {e}")
                continue

        return tracks

    async def get_user_loved_tracks(self) -> list[LastFmTrack]:
        # TODO update to use async calls
        loved_tracks = self.user.get_loved_tracks()
        tracks = []
        for track in loved_tracks:
            loved_at = datetime.fromtimestamp(int(track.timestamp))
            t = LastFmTrack(
                name=track.track.title,
                artist=track.track.artist.name,
                loved_at=loved_at.strftime(config.DATETIME_FORMAT)
            )
            tracks.append(t)

        return tracks

    async def get_user_top_artists(self) -> list[TopItem]:
        # TODO update to use async calls
        top_artists = self.user.get_top_artists(limit=10)
        artists = []
        for artist in top_artists:
            details = artist.item
            model = Artist(
                name=details.name,
                playcount=details.get_playcount(),
                url=details.get_url()
            )
            top_item = TopItem(
                name=artist.item.name,
                weight=artist.weight,
                details=model
            )
            artists.append(top_item)

        return artists

    async def get_user_top_albums(self) -> list[TopItem]:
        # TODO update to use async calls
        top_albums = self.user.get_top_albums(limit=10)
        albums = []
        for album in top_albums:
            details = album.item
            model = Album(
                title=details.title,
                artist_name=details.artist.name,
                cover_image=details.get_cover_image(size=pylast.SIZE_LARGE),
                url=details.get_url()
            )
            top_item = TopItem(
                name=album.item.title,
                weight=album.weight,
                details=model
            )
            albums.append(top_item)

        return albums

    async def update_now_playing(self, current_song: Track) -> bool:
        try:
            await self._run_sync(
                self.network.update_now_playing,
                artist=current_song.artist,
                title=current_song.name,
                album=current_song.album
            )
            # logger.info("Updated Last.fm now playing")
            return True
        except pylast.PyLastError as e:
            # logger.error(f"Failed to update Last.fm now playing: {e}")
            return False

    async def scrobble(self, track: Track, scrobbled_at: datetime = None) -> LastFmTrack | None:
        artist = track.artist
        title = track.clean_name
        album = track.clean_album
        timestamp = int(scrobbled_at.timestamp()) if scrobbled_at else int(time.time())

        try:
            await self._run_sync(
                self.network.scrobble,
                artist=artist,
                title=title,
                timestamp=timestamp,
                album=album
            )
            # logger.info(f"Scrobbled to LastFm: {track.display_name}")
            return LastFmTrack(
                name=title,
                clean_name=title,
                artist=artist,
                album=album,
                clean_album=album,
                scrobbled_at=datetime.fromtimestamp(int(timestamp)),
            )
        except pylast.PyLastError as e:
            logger.error(f"Failed to scrobble to Last.fm: {e}")
            return None

    async def get_album_image_url(self, album: pylast.Album) -> str | None:
        # TODO update to use async calls
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
            image_url = await self._run_sync(album.get_cover_image, size=pylast.SIZE_MEGA)
        except pylast.PyLastError as e:
            logger.error(f"Failed to get album image_url: {e}")

        if image_url is None:
            clean_title = clean_up_title(album.title)
            clean_album = await self._run_sync(self.network.get_album, title=clean_title, artist=album.artist.name)
            try:
                image_url = await self._run_sync(clean_album.get_cover_image, size=pylast.SIZE_MEGA)
            except pylast.PyLastError as e:
                logger.error(f"Failed to get album image_url: {e}")

        return image_url

    async def get_album(
            self,
            title: str,
            artist: str,
            with_tracks: bool = False,
            with_tags: bool = False
    ) -> Album | None:
        def _fetch_album_info():
            album = self.network.get_album(
                title=lastfm_friendly(title),
                artist=lastfm_friendly(artist)
            )
            try:
                return {
                    'album': album,
                    'title': album.get_title(True),
                    'mbid': album.get_mbid() or None,
                    'artist_name': album.get_artist().get_name(True),
                    'url': album.get_url(),
                    'playcount': int(album.get_playcount()),
                    'user_playcount': int(album.get_userplaycount()),
                    'listener_count': int(album.get_listener_count()),
                    'wiki': album.get_wiki_summary()
                }
            except pylast.WSError as e:
                logger.error(f"Failed to get album: {title} by {artist}: {e}")
                return None

        album_data = await self._run_sync(_fetch_album_info)

        if not album_data:
            return None

        tracks = None
        if with_tracks:
            def _fetch_tracks():
                tracks_list = []
                album_tracks = album_data['album'].get_tracks()
                for order, t in enumerate(album_tracks, start=1):
                    tracks_list.append({
                        'title': t.title,
                        'duration': t.get_duration()
                    })
                return tracks_list

            tracks_data = await self._run_sync(_fetch_tracks)
            tracks = []
            for order, track_data in enumerate(tracks_data, start=1):
                obj = Track(
                    name=track_data['title'],
                    clean_name=clean_up_title(track_data['title']),
                    artist=album_data['artist_name'],
                    album=album_data['title'],
                    clean_album=clean_up_title(album_data['title']),
                    order=order,
                    duration=track_data['duration']
                )
                tracks.append(obj)

        tags = None
        if with_tags:
            def _fetch_tags():
                tags_list = []
                album_tags = album_data['album'].get_top_tags()
                for tag in album_tags:
                    tags_list.append({
                        'tag_name': tag.item.name,
                        'weight': int(tag.weight)
                    })
                return tags_list

            tags = await self._run_sync(_fetch_tags)

        return Album(
            title=album_data['title'],
            artist_name=album_data['artist_name'],
            url=album_data['url'],
            tracks=tracks,
            tags=tags,
            mbid=album_data['mbid'],
            playcount=album_data['playcount'],
            user_playcount=album_data['user_playcount'],
            listener_count=album_data['listener_count'],
            wiki=album_data['wiki'],
        )

    async def get_track(
            self,
            track_name: str,
            artist_name: str,
            with_similar: bool = False,
    ) -> LastFmTrack | None:
        # TODO update to use async calls
        track = self.network.get_track(
            artist=lastfm_friendly(artist_name),
            title=lastfm_friendly(track_name)
        )

        try:
            title = track.get_title(True)
        except pylast.WSError as e:
            logger.error(f"Failed to get track: {track_name} by {artist_name}: {e}")
            return None

        similar_tracks = None
        if with_similar:
            similar_tracks = []
            for s in track.get_similar(limit=20):
                s_track = s.item
                st = SimilarTrack(
                    track_name=title,
                    artist_name=artist_name,
                    similar_track_name=s_track.title,
                    similar_track_artist_name=s_track.artist.name,
                    match=s.match
                )
                similar_tracks.append(st)

        return LastFmTrack(
            name=title,
            artist=track.get_artist().get_name(True),
            album=track.get_album().get_title(True) if track.get_album() else None,
            duration=int(track.get_duration()) if track.get_duration() else None,
            url=track.get_url(),
            mbid=track.get_mbid(),
            listener_playcount=int(track.get_playcount()),
            user_playcount=int(track.get_userplaycount()),
            listener_count=int(track.get_listener_count()),
            similar_tracks=similar_tracks,
        )

    async def current_track_user_scrobbles(self, current_song: Track) -> bool | list[LastFmTrack]:
        # TODO update to use async calls
        try:
            tracks = []

            # make multiple calls for "Cool Song", "Cool Song (Remastered 2021)", etc...
            track_scrobbles = self.user.get_track_scrobbles(current_song.artist, current_song.name)
            if current_song.has_clean_name:
                clean_track_scrobbles = self.user.get_track_scrobbles(current_song.artist, current_song.clean_name)
                track_scrobbles.extend(clean_track_scrobbles)

            for t in track_scrobbles:
                timestamp = int(t.timestamp)
                timestamp = datetime.fromtimestamp(timestamp).strftime(config.DATETIME_FORMAT)
                track = LastFmTrack(
                    name=t.track.title,
                    artist=t.track.artist.name,
                    album=t.album,
                    scrobbled_at=timestamp
                )
                tracks.append(track)

            return tracks

        except pylast.PyLastError as e:
            logger.error(f"Failed to get user scrobbles for {current_song.display_name}")
            logger.error(f"Error: {e}")
            return False

    async def user_weekly_chart_dates(self):
        # TODO update to use async calls
        return self.user.get_weekly_chart_dates()

    async def user_weekly_album_charts(self, from_date: str, to_date: str):
        # TODO update to use async calls
        weekly_albums = self.user.get_weekly_album_charts(from_date, to_date)

        results = []
        for album, playcount in weekly_albums:
            album_name = album.title
            artist_name = album.artist.name

            last_fm_album = await self.get_album(album_name, artist_name)
            last_fm_album.playcount = playcount
            results.append(last_fm_album)

        return results

    async def get_user_30_day_stats(self):
        # TODO update to use async calls
        thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
        now = int(datetime.now().timestamp())

        recent_tracks = self.user.get_recent_tracks(limit=None, time_from=thirty_days_ago, time_to=now)
        daily_stats = defaultdict(lambda: {"tracks": set(), "artists": set(), "albums": set()})

        for track in recent_tracks:
            date = datetime.fromtimestamp(int(track.timestamp)).strftime('%Y-%m-%d')
            track_identifier = (track.track.artist.name, track.track.title)
            artist_identifier = track.track.artist.name
            album_identifier = (track.track.artist.name, track.album)

            daily_stats[date]["tracks"].add(track_identifier)
            daily_stats[date]["artists"].add(artist_identifier)
            daily_stats[date]["albums"].add(album_identifier)

        daily_counts = {
            date: {
                "track_count": len(stats["tracks"]),
                "artist_count": len(stats["artists"]),
                "album_count": len(stats["albums"]),
            }
            for date, stats in daily_stats.items()
        }

        return daily_counts


