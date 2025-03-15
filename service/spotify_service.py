import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import settings
from models.artist import SpotifyArtist
from models.track import SpotifyTrack
from models.user import SpotifyUser
from utils import clean_up_title


class SpotifyService:
    def __init__(self):
        auth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=['user-read-playback-state', 'user-modify-playback-state', 'user-read-currently-playing']
        )
        self.spotify = spotipy.Spotify(auth_manager=auth)


    async def get_spotify_account_information(self) -> SpotifyUser | None:
        result: dict = self.spotify.current_user()
        if result:
            url = result['external_urls']['spotify']
            return SpotifyUser(
                name=result['display_name'],
                url=url,
                images=result['images']
            )
        else:
            return None


    async def poll_spotify(self) -> SpotifyTrack | None:
        result = self.spotify.current_user_playing_track()
        track_data = result['item'] if result else None

        if track_data:
            clean_name = clean_up_title(track_data['name'])
            clean_album = clean_up_title(track_data['album']['name'])
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


    async def get_artist_from_name(self, artist_name: str) -> SpotifyArtist:
        spotify_artist = self.spotify.search(q=artist_name, type='artist')
        artist_id = spotify_artist['artists']['items'][0]['id']
        result = self.spotify.artist(artist_id)
        artist = SpotifyArtist(
            id=result['id'],
            name=result['name'],
            image_url=result['images'][0]['url']
        )
        return artist


