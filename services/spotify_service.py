import asyncio

import spotipy
from applescript import AppleScript, ScriptError
from httpcore import ReadTimeout
from loguru import logger
from spotipy.exceptions import SpotifyOauthError
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
        self.authorization_error: str | None = None
        self.web_api_error: str | None = None
        # Local Spotify Desktop polling is the default. It works without Web
        # API access, which Spotify now limits to Premium app owners in
        # Development Mode.
        self.web_api_enabled = False
        self.using_local_desktop = False
        logger.info('Spotify Desktop integration ready.')


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
        if not self.web_api_enabled:
            return await self.poll_spotify_desktop()

        try:
            result = self.spotify.current_user_playing_track()
        except SpotifyOauthError as e:
            # OAuth failures occur before Spotipy makes the playback request and
            # are not subclasses of SpotifyException.  A revoked refresh token
            # should make Spotify appear unavailable, not take down the polling
            # task (and therefore the TUI).
            self.authorization_error = str(e)
            self.web_api_enabled = False
            logger.warning(f'Spotify authorization failed; using Spotify Desktop fallback: {e}')
            return await self.poll_spotify_desktop()
        except spotipy.SpotifyException as e:
            self.web_api_error = str(e)
            if e.http_status in {401, 403}:
                self.web_api_enabled = False
            logger.warning(f'Poll Spotify failed; using Spotify Desktop fallback: {e}')
            return await self.poll_spotify_desktop()
        except ReadTimeout:
            logger.warning('Poll Spotify timed out; using Spotify Desktop fallback.')
            return await self.poll_spotify_desktop()

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


    async def poll_spotify_desktop(self) -> SpotifyTrack | None:
        """Read the locally running Spotify Desktop app via macOS AppleScript.

        This does not use Spotify's Web API, so it works even when a free
        account is blocked from API access. Spotify Desktop must be open.
        """
        script = """
        tell application "Spotify"
            if it is running then
                set currentTrack to current track
                return {name of currentTrack, artist of currentTrack, album of currentTrack, duration of currentTrack, player state is playing}
            else
                return {missing value, missing value, missing value, 0, false}
            end if
        end tell
        """
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(AppleScript(script).run),
                timeout=3,
            )
        except asyncio.TimeoutError:
            logger.warning('Spotify Desktop AppleScript request timed out.')
            return None
        except ScriptError as e:
            # Spotify returns this when it is running but has no selected track.
            if e.number != -1728:
                logger.warning(f'Could not poll Spotify Desktop: {e}')
            return None

        if not isinstance(result, (list, tuple)) or len(result) != 5:
            return None

        name, artist, album, duration_ms, playing = result
        if not name or not artist:
            return None

        self.using_local_desktop = True
        return SpotifyTrack(
            artist=str(artist),
            album=str(album or ''),
            name=str(name),
            clean_name=clean_up_title(str(name)),
            clean_album=clean_up_title(str(album or '')),
            duration=float(duration_ms or 0) / 1000,
            playing=bool(playing),
        )


    async def playback_control(self, action: PlaybackAction, position_ms: int | None = None):
        if not self.web_api_enabled:
            return await self.playback_control_desktop(action, position_ms)

        try:
            user = await self.get_spotify_account_information()
            if user is None or user.is_free():
                return await self.playback_control_desktop(action, position_ms)

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
        except (SpotifyOauthError, spotipy.SpotifyException) as e:
            self.web_api_enabled = False
            self.web_api_error = str(e)
            logger.warning(f'Spotify Web API playback control failed; using Spotify Desktop: {e}')
            return await self.playback_control_desktop(action, position_ms)


    async def playback_control_desktop(
        self, action: PlaybackAction, position_ms: int | None = None
    ) -> bool:
        """Control the locally running Spotify Desktop app via macOS AppleScript."""
        match action:
            case PlaybackAction.PAUSE:
                command = "playpause"
            case PlaybackAction.NEXT:
                command = "next track"
            case PlaybackAction.PREVIOUS:
                command = "previous track"
            case PlaybackAction.SEEK:
                if position_ms is None:
                    raise ValueError("position_ms is required when seeking")
                # Spotify's AppleScript player position is measured in seconds.
                command = f"set player position to {int(position_ms) / 1000}"
            case _:
                raise ValueError(f"Invalid playback action: {action}")

        script = f'''
        tell application "Spotify"
            if it is running then
                {command}
                return true
            else
                return false
            end if
        end tell
        '''
        try:
            return bool(await asyncio.to_thread(AppleScript(script).run))
        except ScriptError as e:
            logger.warning(f'Could not control Spotify Desktop: {e}')
            return False


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
