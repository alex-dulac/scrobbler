"""Read-only desktop library endpoints, authenticated by the parent router."""
from collections.abc import AsyncIterator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError

from library.dependencies import get_scrobbler_engine
from models.library_schemas import (
    ArtistSummary, HistoryPage, LibraryYears, ListeningContext, OnThisDay, WrappedSummary,
)
from repositories.listening_repo import ListeningRepository
from services.scrobbler_engine import ScrobblerEngine

library_router = APIRouter(prefix='/library', tags=['library'])


async def get_listening_repository(
    engine: ScrobblerEngine = Depends(get_scrobbler_engine),
) -> AsyncIterator[ListeningRepository]:
    if not engine.database_available:
        raise HTTPException(503, 'Listening library is unavailable. Connect the configured database and restart the backend.')
    try:
        yield ListeningRepository()
    except (SQLAlchemyError, OSError, TimeoutError) as error:
        raise HTTPException(503, 'Listening library is temporarily unavailable.') from error


@library_router.get('/history/', response_model=HistoryPage)
async def history(
    query: str = Query('', max_length=200),
    page: int = Query(1, ge=1, le=1000000),
    page_size: int = Query(40, ge=1, le=100),
    repository: ListeningRepository = Depends(get_listening_repository),
):
    return await repository.history(query.strip(), page, page_size)


@library_router.get('/years/', response_model=LibraryYears)
async def years(repository: ListeningRepository = Depends(get_listening_repository)):
    return await repository.years()


@library_router.get('/wrapped/{year}/', response_model=WrappedSummary)
async def wrapped(
    year: int = Path(ge=1, le=9998),
    repository: ListeningRepository = Depends(get_listening_repository),
):
    return await repository.wrapped(year)


@library_router.get('/on-this-day/', response_model=OnThisDay)
async def on_this_day(
    day: date = Query(alias='date'),
    repository: ListeningRepository = Depends(get_listening_repository),
):
    # The client sends its local date; scrobble times are stored as local naive datetimes.
    return await repository.on_this_day(day)


@library_router.get('/artists/', response_model=ArtistSummary)
async def artist(
    artist: str = Query(min_length=1, max_length=300),
    repository: ListeningRepository = Depends(get_listening_repository),
):
    if not artist.strip():
        raise HTTPException(422, 'Artist must not be blank.')
    return await repository.artist(artist)


@library_router.get('/context/', response_model=ListeningContext)
async def listening_context(
    artist: str = Query(min_length=1, max_length=300),
    track: str = Query(min_length=1, max_length=500),
    album: str | None = Query(None, min_length=1, max_length=500),
    repository: ListeningRepository = Depends(get_listening_repository),
):
    if not artist.strip() or not track.strip() or (album is not None and not album.strip()):
        raise HTTPException(422, 'Artist, track, and supplied album must not be blank.')
    return await repository.context(artist, track, album)
