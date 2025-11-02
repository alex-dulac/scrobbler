from fastapi import APIRouter, Depends
from loguru import logger

from core import config
from core.security import token_auth
from library.comparison import Comparison
from library.dependencies import get_lastfm_service, get_spotify_service
from routers.spotify_router import spotify_router
from routers.scrobble_router import scrobble_router
from library.state import get_app_state
from routers.sync_router import sync_router
from routers.user_router import user_router
from services.apple_music_service import poll_apple_music, get_current_track_artwork_data
from services.lastfm_service import LastFmService
from services.spotify_service import SpotifyService

router = APIRouter(dependencies=[
    Depends(get_app_state),
    Depends(token_auth)
])

router.include_router(scrobble_router)
router.include_router(spotify_router)
router.include_router(sync_router)
router.include_router(user_router)


@router.get("/poll-song/")
async def get_current_song(
        lastfm: LastFmService = Depends(get_lastfm_service),
        spotify: SpotifyService = Depends(get_spotify_service),
):
    app_state = await get_app_state()
    active_integration = app_state.active_integration
    poll = None

    match active_integration:
        case active_integration.APPLE_MUSIC:
            poll = await poll_apple_music()
        case active_integration.SPOTIFY:
            poll = await spotify.poll_spotify()
        case _:
            raise ValueError("Invalid active integration")

    compare = Comparison(
        poll=poll,
        current_song=app_state.current_song,
        lastfm_album=app_state.lastfm_album
    )

    if compare.is_same_song:
        if compare.update_song_playing_status:
            app_state.current_song.playing = poll.playing
            logger.info(f"Updated '{poll.name}' playing status: {poll.playing}")

        data = {
            "current_song": app_state.current_song,
            "lastfm_album": app_state.lastfm_album,
            "spotify_artist_image": app_state.spotify_artist_image,
        }

        return {"data": data}

    if compare.song_has_changed:
        app_state.current_song = poll
        logger.info(f"Updated current song: {poll.name}")
        if config.SPOTIFY_CLIENT_ID and app_state.current_song is not None:
            spotify_artist = await spotify.get_artist_from_name(app_state.current_song.artist)
            app_state.spotify_artist_image = spotify_artist.image_url if spotify_artist else None

    if compare.update_lastfm_now_playing:
        app_state.current_song.lastfm_updated_now_playing = await lastfm.update_now_playing(app_state.current_song)
        logger.info(f"Updated Last.fm now playing status for '{app_state.current_song.name}'")

    if compare.update_lastfm_album:
        app_state.lastfm_album = await lastfm.get_album(app_state.current_song.album, app_state.current_song.artist)
        logger.info(f"Updated Last.fm album info: {app_state.lastfm_album.title if app_state.lastfm_album else 'None'}")

    data = {
        "current_song": app_state.current_song,
        "lastfm_album": app_state.lastfm_album,
        "spotify_artist_image": app_state.spotify_artist_image,
    }

    return {"data": data}


@router.get("/poll-song/artwork")
async def get_current_song_artwork():
    app_state = await get_app_state()
    active_integration = app_state.active_integration
    artwork = None

    match active_integration:
        case active_integration.APPLE_MUSIC:
            artwork = await get_current_track_artwork_data()
        case active_integration.SPOTIFY:
            pass
        case _:
            raise ValueError("Invalid active integration")

    return {"artwork": artwork}


@router.get("/state/")
async def state():
    app_state = await get_app_state()
    return {
        "current_song": app_state.current_song,
        "lastfm_album": app_state.lastfm_album,
        "scrobble_enabled": app_state.scrobble_enabled,
        "active_integration": app_state.active_integration.normalized_name(),
        "user": app_state.user,
    }
