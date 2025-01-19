from fastapi import APIRouter

from service.spotify_service import SpotifyService

spotify_router = APIRouter()
spotify = SpotifyService()

@spotify_router.get("/spotify/current-track/")
async def spotify_now_playing():
    return {"spotify_track": await spotify.poll_spotify()}
