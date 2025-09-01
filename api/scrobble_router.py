from fastapi import APIRouter
from loguru import logger

from api.state import get_app_state
from services.lastfm_service import LastFmService
from library.utils import validate_scrobble_in_state

scrobble_router = APIRouter()
lastfm = LastFmService()


@scrobble_router.get("/scrobble/status/")
async def scrobble_status():
    app_state = await get_app_state()
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/toggle/")
async def scrobble_toggle():
    app_state = await get_app_state()
    is_scrobbling = app_state.is_scrobbling
    app_state.is_scrobbling = not is_scrobbling
    logger.info(f"Scrobbling toggled to: {app_state.is_scrobbling}")
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/")
async def scrobble_song():
    app_state = await get_app_state()
    if await validate_scrobble_in_state(app_state):
        scrobbled_track = await lastfm.scrobble(app_state.current_song)
        app_state.current_song.scrobbled = True
        return {"result": scrobbled_track.to_dict() if scrobbled_track else None}
    else:
        return {"result": None}
