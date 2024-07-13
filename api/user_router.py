from fastapi import APIRouter

from service.lastfm_service import (
    get_user_recent_tracks,
    get_most_recent_scrobble,
    get_user_playcount,
    get_user_minimal,
    get_user_loved_tracks,
    get_user_top_artists,
    get_user_top_albums
)

user_router = APIRouter()


@user_router.get("/user")
async def user():
    return {"user": get_user_minimal()}


@user_router.get("/user/recent-tracks")
async def recent_tracks():
    return {"recent_tracks": get_user_recent_tracks()}


@user_router.get("/user/loved-tracks")
async def loved_tracks():
    return {"loved_tracks": get_user_loved_tracks()}


@user_router.get("/user/top-artists")
async def top_artists():
    return {"top_artists": get_user_top_artists()}


@user_router.get("/user/top-albums")
async def top_artists():
    return {"top_albums": get_user_top_albums()}


@user_router.get("/user/playcount")
async def playcount():
    return {"playcount": get_user_playcount()}


@user_router.get("/user/recent-scrobble")
async def get_recent_scrobble():
    return {"recent_scrobble": get_most_recent_scrobble()}
