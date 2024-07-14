from fastapi import APIRouter

from api.state import get_app_state
from service.lastfm_service import scrobble_to_lastfm

scrobble_router = APIRouter()


@scrobble_router.get("/scrobble/status/")
async def scrobble_status():
    app_state = get_app_state()
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/toggle/")
async def scrobble_toggle():
    app_state = get_app_state()
    is_scrobbling = app_state.is_scrobbling
    app_state.is_scrobbling = not is_scrobbling
    return {"is_scrobbling": app_state.is_scrobbling}


@scrobble_router.post("/scrobble/")
async def scrobble_song():
    app_state = get_app_state()

    if not app_state.is_scrobbling:
        return {"result": "Scrobbling is not enabled. Please turn on scrobbling and try again."}

    if not app_state.current_song:
        return {"result": "No current song to scrobble."}

    if app_state.current_song.scrobbled:
        return {"result": "This song has already been scrobbled."}

    if not app_state.current_song.playing:
        return {"result": "Current song is not playing."}

    result = scrobble_to_lastfm(app_state.current_song)
    app_state.current_song.scrobbled = result
    return {"result": result}
