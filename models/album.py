class Album:
    def __init__(
            self,
            title: str = None,
            artist: str = None,
            release_date: str = None,
    ):
        self.title = title
        self.artist = artist
        self.release_date = release_date


class LastFmAlbum(Album):
    def __init__(self,
                 title: str = None,
                 artist: str = None,
                 release_date: str = None,
                 image_url: str = None,
                 url: str = None,
                 tracks: list[str] = None,
    ):
        super().__init__(title=title, artist=artist, release_date=release_date)
        self.image_url = image_url
        self.url = url
        self.tracks = tracks

