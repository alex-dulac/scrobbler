class LastFmTrack:
    def __init__(
            self,
            name: str,
            artist: str,
            album: str,
            scrobbled_at: str
    ):
        self.name = name
        self.artist = artist
        self.album = album
        self.scrobbled_at = scrobbled_at


class AppleMusicTrack:
    def __init__(self, track_info, scrobbled: bool = False):
        self.id = None
        self.index = None
        self.name = None
        self.persistent_id = None
        self.database_id = None
        self.date_added = None
        self.time = None
        self.duration = None
        self.artist = None
        self.album_artist = None
        self.composer = None
        self.album = None
        self.genre = None
        self.track_count = None
        self.track_number = None
        self.disc_count = None
        self.disc_number = None
        self.adjusted_volume = None
        self.year = None
        self.comment = None
        self.eq = None
        self.kind = None
        self.media_kind = None
        self.enabled = None
        self.start = None
        self.stop = None
        self.play_count = None
        self.skip_count = None
        self.compilation = None
        self.rating = None
        self.bpm = None
        self.grouping = None
        self.bookmark = None
        self.bookmark_time = None
        self.sample_rate = None
        self.category = None
        self.description = None
        self.episode_number = None
        self.unplayed = None
        self.sort_name = None
        self.sort_album = None
        self.sort_artist = None
        self.sort_composer = None
        self.sort_album_artist = None
        self.release_date = None
        self.loved = None
        self.disliked = None
        self.album_loved = None
        self.album_disliked = None
        self.work = None
        self.movement_name = None
        self.movement_number = None
        self.movement_count = None
        self.cls = None
        self.scrobbled = scrobbled

        ae_type_map = {
            "AEType(b'ID  ')": 'id',
            "AEType(b'pidx')": 'index',
            "AEType(b'pnam')": 'name',
            "AEType(b'pPIS')": 'persistent_id',
            "AEType(b'pDID')": 'database_id',
            "AEType(b'pAdd')": 'date_added',
            "AEType(b'pTim')": 'time',
            "AEType(b'pDur')": 'duration',
            "AEType(b'pArt')": 'artist',
            "AEType(b'pAlA')": 'album_artist',
            "AEType(b'pCmp')": 'composer',
            "AEType(b'pAlb')": 'album',
            "AEType(b'pGen')": 'genre',
            "AEType(b'pTrC')": 'track_count',
            "AEType(b'pTrN')": 'track_number',
            "AEType(b'pDsC')": 'disc_count',
            "AEType(b'pDsN')": 'disc_number',
            "AEType(b'pAdj')": 'adjusted_volume',
            "AEType(b'pYr ')": 'year',
            "AEType(b'pCmt')": 'comment',
            "AEType(b'pEQp')": 'eq',
            "AEType(b'pKnd')": 'kind',
            "AEType(b'pMdK')": 'media_kind',
            "AEType(b'enbl')": 'enabled',
            "AEType(b'pStr')": 'start',
            "AEType(b'pStp')": 'stop',
            "AEType(b'pPlC')": 'play_count',
            "AEType(b'pSkC')": 'skip_count',
            "AEType(b'pAnt')": 'compilation',
            "AEType(b'pRte')": 'rating',
            "AEType(b'pBPM')": 'bpm',
            "AEType(b'pGrp')": 'grouping',
            "AEType(b'pBkm')": 'bookmark',
            "AEType(b'pBkt')": 'bookmark_time',
            "AEType(b'pSfa')": 'sample_rate',
            "AEType(b'pCat')": 'category',
            "AEType(b'pDes')": 'description',
            "AEType(b'pEpN')": 'episode_number',
            "AEType(b'pUnp')": 'unplayed',
            "AEType(b'pSNm')": 'sort_name',
            "AEType(b'pSAl')": 'sort_album',
            "AEType(b'pSAr')": 'sort_artist',
            "AEType(b'pSCm')": 'sort_composer',
            "AEType(b'pSAA')": 'sort_album_artist',
            "AEType(b'pRlD')": 'release_date',
            "AEType(b'pLov')": 'loved',
            "AEType(b'pHat')": 'disliked',
            "AEType(b'pALv')": 'album_loved',
            "AEType(b'pAHt')": 'album_disliked',
            "AEType(b'pWrk')": 'work',
            "AEType(b'pMNm')": 'movement_name',
            "AEType(b'pMvN')": 'movement_number',
            "AEType(b'pMvC')": 'movement_count',
            "AEType(b'pcls')": 'cls',
        }

        for key, value in track_info.items():
            attr_name = ae_type_map.get(str(key))
            if attr_name:
                setattr(self, attr_name, value)
