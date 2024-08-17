class User:
    def __init__(self, name: str):
        self.name = name


class LastFmUser(User):
    def __init__(self, image_url: str, url: str, name: str):
        super().__init__(name)
        self.image_url = image_url
        self.url = url
class SpotifyUser(User):
    def __init__(
            self,
            name: str,
            images: list,
            url: str,
    ):
        super().__init__(name, url)
        self.images = images


