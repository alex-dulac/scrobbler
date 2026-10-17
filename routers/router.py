from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.security import token_auth
from library.dependencies import get_scrobbler_runtime
from library.integrations import Integration, PlaybackAction
from routers.spotify_router import spotify_router
from routers.scrobble_router import scrobble_router
from routers.runtime_router import runtime_router
from routers.sync_router import sync_router
from routers.user_router import user_router
from routers.library_router import library_router
from routers.manual_router import manual_router
from routers.artwork_router import artwork_router
from services.apple_music_service import get_current_track_artwork_data
from services.scrobbler_runtime import ScrobblerRuntime


class IntegrationName(str, Enum):
    APPLE_MUSIC = "apple_music"
    SPOTIFY = "spotify"


class IntegrationRequest(BaseModel):
    integration: IntegrationName


class PlaybackActionName(str, Enum):
    PAUSE = "pause"
    PREVIOUS = "previous"
    NEXT = "next"


class PlaybackRequest(BaseModel):
    action: PlaybackActionName


_INTEGRATIONS = {
    IntegrationName.APPLE_MUSIC: Integration.APPLE_MUSIC,
    IntegrationName.SPOTIFY: Integration.SPOTIFY,
}

_PLAYBACK_ACTIONS = {
    PlaybackActionName.PAUSE: PlaybackAction.PAUSE,
    PlaybackActionName.PREVIOUS: PlaybackAction.PREVIOUS,
    PlaybackActionName.NEXT: PlaybackAction.NEXT,
}

router = APIRouter(dependencies=[
    Depends(token_auth)
])

router.include_router(scrobble_router)
router.include_router(spotify_router)
router.include_router(runtime_router)
router.include_router(sync_router)
router.include_router(user_router)
router.include_router(library_router)
router.include_router(manual_router)
router.include_router(artwork_router)


@router.get("/poll-song/")
async def get_current_song(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    snapshot = runtime.snapshot()
    return {
        "data": {
            "current_song": snapshot.current_song,
            "lastfm_album": snapshot.lastfm_album,
            "spotify_artist_image": snapshot.spotify_artist_image,
        }
    }


@router.get("/poll-song/artwork")
async def get_current_song_artwork(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    snapshot = runtime.snapshot()
    artwork = None

    if snapshot.active_integration == Integration.APPLE_MUSIC:
        artwork = await get_current_track_artwork_data()

    return {"artwork": artwork}


@router.get("/state/")
async def state(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    snapshot = runtime.snapshot()
    current_song = None
    if snapshot.current_song is not None:
        current_song = snapshot.current_song.model_dump(mode="json")
        current_song["scrobble_threshold"] = snapshot.current_song.scrobble_threshold
    return {
        "current_song": current_song,
        "lastfm_album": snapshot.lastfm_album,
        "scrobble_enabled": snapshot.scrobble_enabled,
        "is_scrobbling": snapshot.is_scrobbling,
        "active_integration": snapshot.active_integration.normalized_name(),
        "active_integration_id": str(snapshot.active_integration),
        "user": snapshot.user,
        "session": snapshot.session,
        "database_available": runtime.engine.database_available,
        "runtime_state": runtime.state.value,
    }


@router.put("/integration/")
async def set_integration(
    request: IntegrationRequest,
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    integration = _INTEGRATIONS[request.integration]
    update = await runtime.set_integration(integration)
    return {
        "active_integration": integration.normalized_name(),
        "active_integration_id": str(integration),
        "message": update.message,
    }


@router.post("/playback/")
async def control_playback(
    request: PlaybackRequest,
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    result = await runtime.control_playback(_PLAYBACK_ACTIONS[request.action])
    return {"accepted": result.accepted, "message": result.message}
