from fastapi import APIRouter, Depends

from api.state import get_app_state
from config.security import verify_token
from service import (
    get_most_recent_scrobble,
    poll_apple_music,
    scrobble_to_lastfm,
    get_user_details,
    update_lastfm_now_playing,
    get_user_minimal
)

router = APIRouter(dependencies=[Depends(get_app_state), Depends(verify_token)])


@router.get("/user")
async def user():
    return {"user": get_user_details()}


@router.get("/poll-song")
async def get_current_song():
    app_state = get_app_state()
    result = poll_apple_music()

    update_song = result and (app_state.current_song is None or result.id != app_state.current_song.id)
    update_playing_status = result and app_state.current_song and (result.id == app_state.current_song.id)
    update_now_playing = app_state.current_song and app_state.current_song.playing

    if update_song:
        app_state.current_song = result
    elif update_playing_status:
        app_state.current_song.playing = result.playing

    if update_now_playing:
        update_lastfm_now_playing(app_state.current_song)

    return {"current_song": app_state.current_song}


@router.get("/recent-scrobble")
async def get_recent_scrobble():
    result = get_most_recent_scrobble()
    return {"played_track": result}


@router.get("/scrobble-status")
async def scrobble_status():
    app_state = get_app_state()
    return {"is_scrobbling": app_state.is_scrobbling}


@router.post("/scrobble-toggle")
async def scrobble_toggle():
    app_state = get_app_state()
    is_scrobbling = app_state.is_scrobbling
    app_state.is_scrobbling = not is_scrobbling
    return {"is_scrobbling": app_state.is_scrobbling}


@router.post("/scrobble-song")
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


@router.get("/sync")
async def sync():
    app_state = get_app_state()
    return {
        "current_song": app_state.current_song,
        "is_scrobbling": app_state.is_scrobbling,
        "user": get_user_minimal()
    }
