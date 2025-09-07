from datetime import datetime

from sqlalchemy import Select, select

from db.tables import Scrobble


class ScrobbleFilter:
    def __init__(
            self,
            track_name: str = None,
            artist_name: str = None,
            album_name: str = None,
            scrobbled_at: datetime = None,
            scrobbled_after: str = None,
            scrobbled_before: str = None
    ):
        self.track_name = track_name
        self.artist_name = artist_name
        self.album_name = album_name
        self.scrobbled_at = scrobbled_at
        self.scrobbled_after = scrobbled_after
        self.scrobbled_before = scrobbled_before


async def build_query(f: ScrobbleFilter) -> Select[tuple[Scrobble]]:
    query = select(Scrobble)

    if f is None:
        return query

    if f.track_name:
        query = query.where(Scrobble.track_name == f.track_name)

    if f.artist_name:
        query = query.where(Scrobble.artist_name == f.artist_name)

    if f.album_name:
        query = query.where(Scrobble.album_name == f.album_name)

    if f.scrobbled_at:
        query = query.where(Scrobble.scrobbled_at == f.scrobbled_at)

    if f.scrobbled_after:
        after_date = datetime.strptime(f.scrobbled_after, "%Y-%m-%d")
        query = query.where(Scrobble.scrobbled_at >= after_date)

    if f.scrobbled_before:
        before_date = datetime.strptime(f.scrobbled_before, "%Y-%m-%d")
        query = query.where(Scrobble.scrobbled_at <= before_date)

    query = query.order_by(Scrobble.scrobbled_at.desc())

    return query
