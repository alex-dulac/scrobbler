from fastapi import APIRouter, Depends

from api.scrobble_router import scrobble_router
from api.state import get_app_state
from api.user_router import user_router
from config.security import verify_token
from service.apple_music_service import poll_apple_music
from service.lastfm_service import update_lastfm_now_playing, get_lastfm_album, get_user_minimal

router = APIRouter(dependencies=[
    Depends(get_app_state),
    Depends(verify_token)
])

router.include_router(scrobble_router)
router.include_router(user_router)


@router.get("/poll-song/")
async def get_current_song():
    app_state = get_app_state()
    result = poll_apple_music()

    update_song = result and (app_state.current_song is None or result.id != app_state.current_song.id)
    update_playing_status = result and app_state.current_song and (result.id == app_state.current_song.id)
    update_now_playing = app_state.current_song and app_state.current_song.playing
    update_lastfm_album = result and (app_state.lastfm_album is None or app_state.current_song.album != app_state.lastfm_album.title)

    if update_song:
        app_state.current_song = result
    elif update_playing_status:
        app_state.current_song.playing = result.playing

    if update_now_playing:
        update_lastfm_now_playing(app_state.current_song)

    if update_lastfm_album:
        app_state.lastfm_album = get_lastfm_album(app_state.current_song.album, app_state.current_song.artist)

    return {"current_song": app_state.current_song, "lastfm_album": app_state.lastfm_album}


@router.get("/state/")
async def sync():
    app_state = get_app_state()
    return {
        "current_song": app_state.current_song,
        "lastfm_album": app_state.lastfm_album,
        "is_scrobbling": app_state.is_scrobbling,
        "user": get_user_minimal()
    }
