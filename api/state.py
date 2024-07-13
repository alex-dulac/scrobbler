from model import AppleMusicTrack, LastFmAlbum


class AppState:
    def __init__(self):
        self.current_song: AppleMusicTrack | None = None
        self.lastfm_album: LastFmAlbum | None = None
        self.is_scrobbling: bool = False


app_state = AppState()


def get_app_state() -> AppState:
    return app_state
