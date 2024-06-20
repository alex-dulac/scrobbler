class Track:
    def __init__(self, track: str, artist: str, album: str):
        self.track = track
        self.artist = artist
        self.album = album


class AppleMusicTrack(Track):
    def __init__(self, track: str, artist: str, album: str, scrobbled: bool = False):
        super().__init__(track, artist, album)
        self.scrobbled = scrobbled


class LastFmTrack(Track):
    def __init__(self, track: str, artist: str, album: str, scrobbled_at: str):
        super().__init__(track, artist, album)
        self.scrobbled_at = scrobbled_at
