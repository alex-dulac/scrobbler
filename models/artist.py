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
