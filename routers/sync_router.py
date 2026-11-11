from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from library.dependencies import get_scrobbler_runtime, get_sync_service
from services.scrobbler_runtime import ScrobblerRuntime
from services.sync_service import SyncBusyError, SyncService

sync_router = APIRouter()


class ScrobbleSyncRequest(BaseModel):
    # Both days are included; leave time_from empty for all history, time_to for today
    time_from: date | None = None
    time_to: date | None = None


@sync_router.post('/sync/scrobbles/')
async def sync_scrobbles(
        request: ScrobbleSyncRequest,
        sync_service: SyncService = Depends(get_sync_service),
        runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
):
    """Start a background sync; /state/ reports its progress under "sync"."""
    if not runtime.engine.database_available:
        raise HTTPException(503, "Syncing scrobbles needs your history database.")
    if request.time_from and request.time_to and request.time_from > request.time_to:
        raise HTTPException(422, "The start date must be on or before the end date.")
    try:
        sync_service.start_scrobble_sync(
            time_from=request.time_from.isoformat() if request.time_from else None,
            time_to=request.time_to.isoformat() if request.time_to else None,
        )
    except SyncBusyError as error:
        raise HTTPException(409, str(error)) from error

    return {"message": "Syncing scrobbles from Last.fm…"}


@sync_router.get('/sync/artists/')
async def sync_artists(
        only_missing: bool = True,
        sync_service: SyncService = Depends(get_sync_service)
):
    data = await sync_service.sync_artists(only_missing)

    return {"data": data}


@sync_router.get('/sync/albums/')
async def sync_albums(
        only_missing: bool = True,
        sync_service: SyncService = Depends(get_sync_service)
):
    data = await sync_service.sync_albums(only_missing)

    return {"data": data}


@sync_router.get('/sync/tracks/')
async def sync_tracks(
        only_missing: bool = True,
        sync_service: SyncService = Depends(get_sync_service)
):
    data = await sync_service.sync_tracks(only_missing)

    return {"data": data}
