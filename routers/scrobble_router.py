import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from library.dependencies import get_scrobbler_runtime
from services.scrobbler_runtime import ScrobblerRuntime


class ScrobblingStatusRequest(BaseModel):
    enabled: bool


scrobble_router = APIRouter()
_scrobble_status_lock = asyncio.Lock()


@scrobble_router.get("/scrobble/status/")
async def scrobble_status(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    snapshot = runtime.snapshot()
    return {"scrobble_enabled": snapshot.scrobble_enabled}


@scrobble_router.put("/scrobble/status/")
async def set_scrobble_status(
    request: ScrobblingStatusRequest,
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    async with _scrobble_status_lock:
        update = await runtime.set_scrobbling_enabled(request.enabled)
        return {
            "scrobble_enabled": request.enabled,
            "message": update.message,
        }


@scrobble_router.post("/scrobble/toggle/", deprecated=True)
async def scrobble_toggle(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    async with _scrobble_status_lock:
        snapshot = runtime.snapshot()
        enabled = not snapshot.scrobble_enabled
        update = await runtime.set_scrobbling_enabled(enabled)
        return {
            "scrobble_enabled": enabled,
            "message": update.message,
        }


@scrobble_router.post("/scrobble/")
async def scrobble_song(
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    command = await runtime.scrobble_current()
    return {
        "result": (
            command.scrobble.model_dump(mode="json")
            if command.scrobble is not None
            else None
        ),
        "accepted": command.accepted,
        "message": command.message,
    }
