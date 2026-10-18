"""iPod play review for the desktop app, authenticated by the parent router."""
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from library.dependencies import get_ipod_watcher
from models.ipod_schemas import IpodCommandResponse, IpodPlaysRequest, IpodPlaysResponse
from services.ipod_watcher import IpodBusyError, IpodUnavailableError, IpodWatcher

ipod_router = APIRouter(prefix="/ipod", tags=["ipod"])


async def get_watcher(watcher: IpodWatcher = Depends(get_ipod_watcher)) -> AsyncIterator[IpodWatcher]:
    try:
        yield watcher
    except IpodUnavailableError as error:
        raise HTTPException(503, str(error)) from error
    except IpodBusyError as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (SQLAlchemyError, OSError, TimeoutError) as error:
        raise HTTPException(503, "iPod plays are temporarily unavailable.") from error


@ipod_router.get("/plays/", response_model=IpodPlaysResponse)
async def pending_plays(watcher: IpodWatcher = Depends(get_watcher)):
    return {"plays": await watcher.pending_plays()}


@ipod_router.post("/scrobble/", response_model=IpodCommandResponse)
async def scrobble_plays(request: IpodPlaysRequest, watcher: IpodWatcher = Depends(get_watcher)):
    count = await watcher.start_scrobble(request.play_ids)
    return IpodCommandResponse(message=f"Scrobbling {count} iPod plays…", count=count)


@ipod_router.post("/discard/", response_model=IpodCommandResponse)
async def discard_plays(request: IpodPlaysRequest, watcher: IpodWatcher = Depends(get_watcher)):
    await watcher.discard(request.play_ids)
    count = len(request.play_ids)
    return IpodCommandResponse(message=f"Discarded {count} iPod plays.", count=count)


@ipod_router.post("/rescan/", response_model=IpodCommandResponse)
async def rescan(watcher: IpodWatcher = Depends(get_watcher)):
    await watcher.capture()
    if watcher.error:
        raise HTTPException(503, watcher.error)
    return IpodCommandResponse(message=f"Captured {watcher.last_captured} new iPod plays.", count=watcher.last_captured)
