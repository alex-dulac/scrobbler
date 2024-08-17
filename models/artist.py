class Artist:
    def __init__(
            self,
            name: str = None,
    ):
        self.name = name


class LastFmArtist(Artist):
    def __init__(self, name: str = None, playcount: int = None, url: str = None):
        super().__init__(name=name)
        self.playcount = playcount,
        self.url = url


class SpotifyArtist(Artist):
    def __init__(self, name: str = None, id: str = None, image_url: str = None, url: str = None):
        super().__init__(name=name)
        self.id = id,
        self.image_url = image_url,
        self.url = url
