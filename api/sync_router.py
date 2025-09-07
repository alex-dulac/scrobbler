from fastapi import APIRouter, Depends

from api.dependencies import get_sync_service
from services.sync_service import SyncService

sync_router = APIRouter()


@sync_router.get('/sync/scrobbles/')
async def sync_scrobbles(
        time_from: str = None,
        time_to: str = None,
        sync_service: SyncService = Depends(get_sync_service)
):
    data = await sync_service.sync_scrobbles(
        time_from=time_from,
        time_to=time_to,
        clean=True
    )

    return {"data": data}


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
