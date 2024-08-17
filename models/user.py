from datetime import datetime


class User:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url


class LastFmUser(User):
    def __init__(
            self,
            album_count: str,
            artist_count: str,
            country: str,
            image_url: str,
            name: str,
            playcount: str,
            realname: str,
            registered: datetime,
            subscriber: bool,
            track_count: str,
            url: str,
    ):
        super().__init__(name, url)
        self.album_count = album_count
        self.artist_count = artist_count
        self.country = country
        self.image_url = image_url
        self.playcount = playcount
        self.realname = realname
        self.registered = registered
        self.subscriber = subscriber
        self.track_count = track_count


class SpotifyUser(User):
    def __init__(
            self,
            name: str,
            images: list,
            url: str,
    ):
        super().__init__(name, url)
        self.images = images


class AppleMusicUser(User):
    def __init__(self, name: str):
        super().__init__(name)
        self.account_name: str | None = None
        self.account_kind: str | None = None
        self.account_email: str | None = None
        self.subscription_status = None

