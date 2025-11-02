from fastapi import APIRouter, Depends

from library.dependencies import get_spotify_service
from services.spotify_service import SpotifyService

spotify_router = APIRouter()

@spotify_router.get("/spotify/current-track/")
async def spotify_now_playing(spotify: SpotifyService = Depends(get_spotify_service)):
    return {"spotify_track": await spotify.poll_spotify()}
