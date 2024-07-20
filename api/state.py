from model import AppleMusicTrack, LastFmAlbum, LastFmUser


class AppState:
    def __init__(self):
        self.current_song: AppleMusicTrack | None = None
        self.lastfm_album: LastFmAlbum | None = None
        self.is_scrobbling: bool = False
        self.user: LastFmUser | None = None


app_state = AppState()


async def get_app_state() -> AppState:
    return app_state
