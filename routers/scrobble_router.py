from fastapi import APIRouter, Depends
from loguru import logger

from library.state import get_app_state
from services.lastfm_service import get_lastfm_service, LastFmService

scrobble_router = APIRouter()


@scrobble_router.get("/scrobble/status/")
async def scrobble_status():
    app_state = await get_app_state()
    return {"scrobble_enabled": app_state.scrobble_enabled}


@scrobble_router.post("/scrobble/toggle/")
async def scrobble_toggle():
    app_state = await get_app_state()
    app_state.scrobble_enabled = not app_state.scrobble_enabled
    logger.info(f"Scrobbling toggled to: {app_state.scrobble_enabled}")
    return {"scrobble_enabled": app_state.scrobble_enabled}


@scrobble_router.post("/scrobble/")
async def scrobble_song(lastfm: LastFmService = Depends(get_lastfm_service)):
    app_state = await get_app_state()
    result = None

    if await app_state.validate_scrobble_state():
        app_state.is_scrobbling = True
        scrobbled_track = await lastfm.scrobble(app_state.current_song)
        if scrobbled_track:
            app_state.current_song.scrobbled = True
            app_state.is_scrobbling = False
            result = scrobbled_track.model_dump()

    return {"result": result}
