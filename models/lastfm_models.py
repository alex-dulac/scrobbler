from enum import Enum

from models.album import LastFmAlbum
from models.artist import LastFmArtist
from models.track import LastFmTrack


class TopItemType(Enum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"


class LastFmTopItem:
    def __init__(
            self,
            name: str,
            weight: int = None,
            item_type: TopItemType = None,
            details: LastFmTrack | LastFmAlbum | LastFmArtist = None
    ):
        self.name = name,
        self.weight = weight,
        self.item_type = item_type,
        self.details = details
