from typing import List

from models.album import LastFmAlbum
from models.integrations import Integration
from models.track import AppleMusicTrack, SpotifyTrack, LastFmTrack
from models.user import LastFmUser


class AppState:
    def __init__(self):
        self.artist_image: str | None = None
        self.current_song: AppleMusicTrack | SpotifyTrack | None = None
        self.lastfm_album: LastFmAlbum | None = None
        self.lastfm_artist_image_url: str | None = None
        self.is_scrobbling: bool = False
        self.user: LastFmUser | None = None
        self.active_integration: Integration | None = Integration.APPLE_MUSIC
        self.session_scrobbles: List[LastFmTrack] = []


app_state = AppState()


async def get_app_state() -> AppState:
    return app_state
