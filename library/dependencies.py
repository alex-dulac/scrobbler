from services.lastfm_service import LastFmService
from services.spotify_service import SpotifyService
from services.sync_service import SyncService

lastfm: LastFmService | None = None
spotify: SpotifyService | None = None
sync_service: SyncService | None = None


async def get_lastfm_service() -> LastFmService:
    global lastfm
    if lastfm is None:
        lastfm = LastFmService()
    return lastfm


async def get_spotify_service() -> SpotifyService:
    global spotify
    if spotify is None:
        spotify = SpotifyService()
    return spotify


async def get_sync_service() -> SyncService:
    global sync_service
    if sync_service is None:
        sync_service = SyncService()
    return sync_service
