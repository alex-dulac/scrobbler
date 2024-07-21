from fastapi import APIRouter

from service.spotify_service import get_user_now_playing

spotify_router = APIRouter()


@spotify_router.get("/spotify/current-track/")
async def spotify_now_playing():
    return {"spotify_track": await get_user_now_playing()}
