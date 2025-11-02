from services.lastfm_service import LastFmService
from services.spotify_service import SpotifyService
from services.sync_service import SyncService

lastfm = LastFmService()
spotify = SpotifyService()
sync_service = SyncService()

async def get_lastfm_service():
    return lastfm

async def get_spotify_service():
    return spotify

async def get_sync_service():
    return sync_service
