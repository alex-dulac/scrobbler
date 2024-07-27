class User:
    def __init__(self, name: str):
        self.name = name


class LastFmUser(User):
    def __init__(self, image_url: str, url: str, name: str):
        super().__init__(name)
        self.image_url = image_url
        self.url = url
