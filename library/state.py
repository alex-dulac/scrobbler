from loguru import logger
from pydantic import HttpUrl, BaseModel

from library.integrations import Integration
from library.session_scrobbles import SessionScrobbles
from models.schemas import Album, LastFmUser, Track
from services.lastfm_service import get_lastfm_account_details


class AppState(BaseModel):
    active_integration: Integration = Integration.APPLE_MUSIC
    scrobble_enabled: bool = True
    is_scrobbling: bool = False
    user: LastFmUser | None = None
    current_song: Track | None = None
    lastfm_album: Album | None = None
    spotify_artist_image: HttpUrl | None = None
    session: SessionScrobbles = SessionScrobbles()

    def __init__(self):
        super().__init__()
        self.user = get_lastfm_account_details()

    async def validate_scrobble_state(self) -> bool:
        if not self.scrobble_enabled:
            logger.info("Scrobbling is not enabled.")
            return False

        if not self.current_song:
            logger.info("No song playing.")
            return False

        if self.current_song.scrobbled:
            logger.info("This song has already been scrobbled.")
            return False

        if not self.current_song.playing:
            logger.info("Current song is not playing.")
            return False

        if self.is_scrobbling:
            logger.info("A scrobble operation is already in progress.")
            return False

        return True


app_state = AppState()


async def get_app_state() -> AppState:
    return app_state
