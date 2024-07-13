class LastFmUserStats:
    def __init__(
            self,
            playcount: str,
            recent_tracks: list,
            loved_tracks: list = None,
            top_artists: list = None
    ):
        self.playcount = playcount
        self.recent_tracks = recent_tracks
        self.loved_tracks = loved_tracks
        self.top_artists = top_artists


class LastFmUser:
    def __init__(
            self,
            name: str,
            image_url: str,
            url: str
    ):
        self.name = name
        self.image_url = image_url
        self.url = url


class LastFmTrack:
    def __init__(
            self,
            name: str,
            artist: str,
            album: str = None,
            scrobbled_at: str = None,
            loved_at: str = None
    ):
        self.name = name
        self.artist = artist
        self.album = album
        self.scrobbled_at = scrobbled_at
        self.loved_at = loved_at


class LastFmAlbum:
    def __init__(
            self,
            title: str,
            artist: str,
            release_date: str = None,
            image_url: str = None,
            url: str = None,
            tracks: list = None
    ):
        self.title = title
        self.artist = artist
        self.release_date = release_date
        self.image_url = image_url
        self.url = url
        self.tracks = tracks


class LastFmArtist:
    def __init__(
            self,
            name: str,
            playcount: int = None,
            url: str = None,
    ):
        self.name = name,
        self.playcount = playcount,
        self.url = url


class LastFmTopItem:
    def __init__(
            self,
            name: str,
            weight: int = None,
            details: LastFmTrack | LastFmAlbum | LastFmArtist = None
    ):
        self.name = name,
        self.weight = weight,
        self.details = details


class AppleMusicTrack:
    def __init__(
            self,
            track_info,
            playing: bool = False,
            scrobbled: bool = False
    ):
        self.id = None
        self.index = None
        self.name = None
        self.persistent_id = None
        self.time = None
        self.duration = None
        self.artist = None
        self.album_artist = None
        self.composer = None
        self.album = None
        self.genre = None
        self.track_number = None
        self.disc_number = None
        self.year = None
        self.release_date = None
        self.loved = None
        self.disliked = None
        self.album_loved = None
        self.album_disliked = None
        self.playing = playing
        self.scrobbled = scrobbled

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
