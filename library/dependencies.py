from services.lastfm_service import LastFmService
from services.spotify_service import SpotifyService
from services.sync_service import SyncService

lastfm: LastFmService | None = None
spotify: SpotifyService | None = None
sync_service: SyncService | None = None

async def get_lastfm_service() -> LastFmService:
    return lastfm

async def get_spotify_service() -> SpotifyService:
    return spotify

async def get_sync_service() -> SyncService:
    return sync_service

async def init_deps() -> tuple[LastFmService, SpotifyService, SyncService]:
    global lastfm, spotify, sync_service
    lastfm = LastFmService()
    spotify = SpotifyService()
    sync_service = SyncService()
    return lastfm, spotify, sync_service
