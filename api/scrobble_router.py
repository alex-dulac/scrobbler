from fastapi import APIRouter

from api.state import get_app_state
from service.lastfm_service import scrobble_to_lastfm
from helpers.utils import validate_scrobble_in_state

scrobble_router = APIRouter()


@scrobble_router.get("/scrobble/status/")
async def scrobble_status():
    app_state = await get_app_state()
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/toggle/")
async def scrobble_toggle():
    app_state = await get_app_state()
    is_scrobbling = app_state.is_scrobbling
    app_state.is_scrobbling = not is_scrobbling
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/")
async def scrobble_song():
    app_state = await get_app_state()
    valid = await validate_scrobble_in_state(app_state)
    if valid:
        scrobble = await scrobble_to_lastfm(app_state.current_song)
        app_state.current_song.scrobbled = scrobble

    return {"result": valid and app_state.current_song.scrobbled}
