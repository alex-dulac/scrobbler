from fastapi import APIRouter

from service.spotify_service import poll_spotify

spotify_router = APIRouter()


@spotify_router.get("/spotify/current-track/")
async def spotify_now_playing():
    return {"spotify_track": await poll_spotify()}
