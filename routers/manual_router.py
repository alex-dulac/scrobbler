from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from library.dependencies import get_lastfm_service, get_scrobbler_runtime
from models.manual_schemas import AlbumPreview, ManualSubmitRequest, ManualSubmitResponse
from services.lastfm_service import LastFmService
from services.manual_scrobble_service import ManualScrobbleService
from services.scrobbler_runtime import ScrobblerRuntime

manual_router = APIRouter(prefix="/manual", tags=["manual"])
manual_service = ManualScrobbleService()


@manual_router.get("/album/", response_model=AlbumPreview)
async def preview_album(artist: str = Query(min_length=1, max_length=300),
                        album: str = Query(min_length=1, max_length=300),
                        finished_at: datetime = Query(),
                        lastfm: LastFmService = Depends(get_lastfm_service)):
    try:
        return await manual_service.preview(lastfm, artist=artist, album=album, finished_at=finished_at)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Could not retrieve the album from Last.fm") from error


@manual_router.post("/submit/", response_model=ManualSubmitResponse)
async def submit_album(request: ManualSubmitRequest,
                       runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime)):
    try:
        return await manual_service.submit(runtime, request.preview_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (RuntimeError, OSError) as error:
        raise HTTPException(status_code=503, detail="Could not save the album; retry this preview") from error
