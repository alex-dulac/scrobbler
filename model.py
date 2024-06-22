class Track:
    def __init__(self, track: str, artist: str, album: str):
        self.track = track
        self.artist = artist
        self.album = album


class AppleMusicTrack(Track):
    def __init__(
            self,
            track: str,
            artist: str,
            album: str,
            duration: int,
            track_id: str,
            track_persistent_id: str,
            share_link: str,
            scrobbled: bool = False
    ):
        super().__init__(track, artist, album)
        self.duration = duration
        self.track_id = track_id
        self.track_persistent_id = track_persistent_id
        self.share_link = share_link
        self.scrobbled = scrobbled


class LastFmTrack(Track):
    def __init__(
            self,
            track: str,
            artist: str,
            album: str,
            scrobbled_at: str
    ):
        super().__init__(track, artist, album)
        self.scrobbled_at = scrobbled_at
