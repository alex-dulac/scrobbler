from models.integrations import Integration
from models.lastfm_models import LastFmAlbum
from models.track import AppleMusicTrack, SpotifyTrack
from models.user import LastFmUser


class AppState:
    def __init__(self):
        self.current_song: AppleMusicTrack | SpotifyTrack | None = None
        self.lastfm_album: LastFmAlbum | None = None
        self.lastfm_artist_image_url: str | None = None
        self.is_scrobbling: bool = False
        self.user: LastFmUser | None = None
        self.active_integration: Integration | None = Integration.APPLE_MUSIC


app_state = AppState()


async def get_app_state() -> AppState:
    return app_state
