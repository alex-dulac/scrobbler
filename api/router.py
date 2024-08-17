from fastapi import APIRouter, Depends
from loguru import logger

from api.spotify_router import spotify_router
from api.data_router import data_router
from api.scrobble_router import scrobble_router
from api.state import get_app_state
from api.user_router import user_router
from config.security import verify_token
from service.apple_music_service import poll_apple_music
from service.lastfm_service import update_lastfm_now_playing, get_lastfm_album, get_user_minimal
from service.spotify_service import poll_spotify
from helpers.utils import poll_comparison
from service.spotify_service import poll_spotify, get_artist_from_name

router = APIRouter(dependencies=[
    Depends(get_app_state),
    Depends(verify_token)
])

router.include_router(data_router)
router.include_router(scrobble_router)
router.include_router(spotify_router)
router.include_router(user_router)


@router.get("/poll-song/")
async def get_current_song():
    app_state = await get_app_state()
    active_integration = app_state.active_integration

    match active_integration:
        case active_integration.APPLE_MUSIC:
            poll = await poll_apple_music()
        case active_integration.SPOTIFY:
            poll = await poll_spotify()
        case _:
            raise ValueError("Invalid active integration")

    compare = await poll_comparison(poll, app_state.current_song, app_state.lastfm_album)

    if compare["update_song"]:
        app_state.current_song = poll
        logger.info(f"Updated current song: {poll.name}")

    if compare["update_song_playing_status"]:
        app_state.current_song.playing = poll.playing
        logger.info(f"Updated '{poll.name}' playing status: {poll.playing}")

    if compare["update_lastfm_now_playing"]:
        await update_lastfm_now_playing(app_state.current_song)
        app_state.current_song.lastfm_updated_now_playing = True

    if compare["update_lastfm_album"]:
        app_state.lastfm_album = await get_lastfm_album(app_state.current_song.album, app_state.current_song.artist)

    spotify_artist = await get_artist_from_name(app_state.current_song.artist)

    return {
        "current_song": app_state.current_song,
        "lastfm_album": app_state.lastfm_album
        "artist_image": spotify_artist.image_url,
    }


@router.get("/state/")
async def sync():
    app_state = await get_app_state()
    return {
        "current_song": app_state.current_song,
        "lastfm_album": app_state.lastfm_album,
        "is_scrobbling": app_state.is_scrobbling,
        "active_integration": app_state.active_integration,
        "user": await get_user_minimal()
    }
