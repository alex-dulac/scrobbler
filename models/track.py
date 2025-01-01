class Track:
    def __init__(
            self,
            name: str = None,
            artist: str = None,
            album: str = None,
            playing: bool = False,
            time_played: int = 0,
            scrobbled: bool = False,
            lastfm_updated_now_playing: bool = False,
            clean_name: str = None,
            clean_album: str = None
    ):
        self.name = name
        self.artist = artist
        self.album = album
        self.playing = playing
        self.time_played = time_played
        self.scrobbled = scrobbled
        self.lastfm_updated_now_playing = lastfm_updated_now_playing
        self.clean_name = clean_name
        self.clean_album = clean_album


class AppleMusicTrack(Track):
    def __init__(self, track_info, playing):
        super().__init__(playing=playing)
        self.id = None
        self.index = None
        self.persistent_id = None
        self.time = None
        self.duration = None
        self.album_artist = None
        self.composer = None
        self.genre = None
        self.track_number = None
        self.disc_number = None
        self.year = None
        self.release_date = None
        self.loved = None
        self.disliked = None
        self.album_loved = None
        self.album_disliked = None

        ae_type_map = {
            "AEType(b'ID  ')": 'id',
            "AEType(b'pidx')": 'index',
            "AEType(b'pnam')": 'name',
            "AEType(b'pPIS')": 'persistent_id',
            "AEType(b'pTim')": 'time',
            "AEType(b'pDur')": 'duration',
            "AEType(b'pArt')": 'artist',
            "AEType(b'pAlA')": 'album_artist',
            "AEType(b'pCmp')": 'composer',
            "AEType(b'pAlb')": 'album',
            "AEType(b'pGen')": 'genre',
            "AEType(b'pTrN')": 'track_number',
            "AEType(b'pDsN')": 'disc_number',
            "AEType(b'pYr ')": 'year',
            "AEType(b'pRlD')": 'release_date',
            "AEType(b'pLov')": 'loved',
            "AEType(b'pHat')": 'disliked',
            "AEType(b'pALv')": 'album_loved',
            "AEType(b'pAHt')": 'album_disliked'
        }

        for key, value in track_info.items():
            attr_name = ae_type_map.get(str(key))
            if attr_name:
                setattr(self, attr_name, value)

    def get_scrobbled_threshold(self) -> int:
        return min(round(self.duration / 2), 120) if self.duration else 120

    def is_ready_to_be_scrobbled(self) -> bool:
        return self.playing and not self.scrobbled and self.time_played >= self.get_scrobbled_threshold()

    def has_clean_name(self) -> bool:
        return self.name != self.clean_name


class LastFmTrack(Track):
    def __init__(
            self,
            name: str = None,
            artist: str = None,
            album: str = None,
            scrobbled_at: str = None,
            loved_at: str = None
    ):
        super().__init__(name=name, artist=artist, album=album)
        self.scrobbled_at = scrobbled_at
        self.loved_at = loved_at

    def to_dict(self):
        return {
            "name": self.name,
            "artist": self.artist,
            "album": self.album,
            "scrobbled_at": self.scrobbled_at,
            "loved_at": self.loved_at
        }


class SpotifyTrack(Track):
    pass
