from fastapi import APIRouter

from api.state import get_app_state
from service.lastfm_service import (
    get_user_recent_tracks,
    get_user_playcount,
    get_user_minimal,
    get_user_loved_tracks,
    get_user_top_artists,
    get_user_top_albums,
    current_track_user_scrobbles,
    user_weekly_album_charts
)

user_router = APIRouter()


@user_router.get("/user/")
async def user():
    return {"user": await get_user_minimal()}


@user_router.get("/user/recent-tracks/")
async def recent_tracks():
    return {"recent_tracks": await get_user_recent_tracks()}


@user_router.get("/user/loved-tracks/")
async def loved_tracks():
    return {"loved_tracks": await get_user_loved_tracks()}


@user_router.get("/user/top-artists/")
async def top_artists():
    return {"top_artists": await get_user_top_artists()}


@user_router.get("/user/top-albums/")
async def top_artists():
    return {"top_albums": await get_user_top_albums()}


@user_router.get("/user/playcount/")
async def playcount():
    return {"playcount": await get_user_playcount()}


@user_router.get("/user/track-scrobbles/")
async def get_track_scrobbles():
    app_state = await get_app_state()

    result = await current_track_user_scrobbles(app_state.current_song) if app_state.current_song else None

    return {"track_scrobbles": result}


@user_router.get("/user/charts/albums/weekly/")
async def get_weekly_album_charts(from_date: str, to_date: str):
    results = await user_weekly_album_charts(from_date, to_date)

    return {"data": results}
