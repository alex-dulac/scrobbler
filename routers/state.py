from typing import List

from loguru import logger

from library.integrations import Integration
from models.schemas import AppleMusicTrack, SpotifyTrack, Album, LastFmUser, LastFmTrack


class AppState:
    def __init__(self):
        self.spotify_artist_image: str | None = None
        self.current_song: AppleMusicTrack | SpotifyTrack | None = None
        self.lastfm_album: Album | None = None
        self.is_scrobbling: bool = False
        self.user: LastFmUser | None = None
        self.active_integration: Integration | None = Integration.APPLE_MUSIC
        self.session_scrobbles: List[LastFmTrack] = []


app_state = AppState()


async def get_app_state() -> AppState:
    return app_state


async def validate_scrobble_in_state(state: AppState) -> bool:
    if not state.is_scrobbling:
        logger.info("Scrobbling is not enabled.")
        return False

    if not state.current_song:
        logger.info("No song playing.")
        return False

    if state.current_song.scrobbled:
        logger.info("This song has already been scrobbled.")
        return False

    if not state.current_song.playing:
        logger.info("Current song is not playing.")
        return False

    return True