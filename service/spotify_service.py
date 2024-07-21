import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import settings


auth = SpotifyOAuth(
    client_id=settings.SPOTIFY_CLIENT_ID,
    client_secret=settings.SPOTIFY_CLIENT_SECRET,
    redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    scope=['user-read-playback-state', 'user-modify-playback-state', 'user-read-currently-playing']

)
spotify = spotipy.Spotify(auth_manager=auth)


async def poll_spotify():
    result: dict = spotify.current_user_playing_track()
    if result:
        return result['item']['album']['name'], result['item']['artists'][0]['name'], result['item']['name']
    else:
        return None
