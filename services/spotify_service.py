import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core import config
from library.integrations import PlaybackAction
from library.utils import clean_up_title
from models.schemas import SpotifyUser, SpotifyTrack, Artist

scope = [
    'user-read-playback-state',
    'user-modify-playback-state',
    'user-read-currently-playing',
    'user-read-private',
    'app-remote-control',
]


class SpotifyService:
    def __init__(self):
        auth = SpotifyOAuth(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=config.SPOTIFY_REDIRECT_URI,
            scope=scope
        )
        self.spotify = spotipy.Spotify(auth_manager=auth)


    async def get_spotify_account_information(self) -> SpotifyUser | None:
        result: dict = self.spotify.current_user()
        if result:
            url = result['external_urls']['spotify']
            return SpotifyUser(
                name=result['display_name'],
                url=url,
                images=result['images'],
                product=result['product'],
            )
        else:
            return None


    async def poll_spotify(self) -> SpotifyTrack | None:
        result = self.spotify.current_user_playing_track()
        track_data = result['item'] if result else None

        if track_data:
            clean_name = await clean_up_title(track_data['name'])
            clean_album = await clean_up_title(track_data['album']['name'])
            duration = track_data['duration_ms'] / 1000  # convert ms to seconds

            return SpotifyTrack(
                artist=track_data['artists'][0]['name'],
                album=track_data['album']['name'],
                name=track_data['name'],
                clean_name=clean_name,
                clean_album=clean_album,
                duration=duration,
                playing=result['is_playing']
            )
        else:
            return None


    async def playback_control(self, action: PlaybackAction, position_ms: int | None = None):
        user = await self.get_spotify_account_information()
        if user.is_free():
            return False  # Free accounts cannot control playback

        match action:
            case PlaybackAction.PAUSE:
                return self.spotify.pause_playback()
            case PlaybackAction.NEXT:
                return self.spotify.next_track()
            case PlaybackAction.PREVIOUS:
                return self.spotify.previous_track()
            case PlaybackAction.SEEK:
                return self.spotify.seek_track(position_ms=position_ms)
            case _:
                raise ValueError(f"Invalid playback action: {action}")


    async def get_artist_from_name(self, artist_name: str) -> Artist:
        spotify_artist = self.spotify.search(q=artist_name, type='artist')
        artist_id = spotify_artist['artists']['items'][0]['id']
        result = self.spotify.artist(artist_id)
        artist = Artist(
            id=result['id'],
            name=result['name'],
            image_url=result['images'][0]['url']
        )
        return artist


spotify = SpotifyService()

async def get_spotify_service() -> SpotifyService:
    return spotify
