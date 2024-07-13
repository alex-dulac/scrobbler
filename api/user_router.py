from fastapi import APIRouter

from service.lastfm_service import (
    get_user_recent_tracks,
    get_most_recent_scrobble,
    get_user_playcount,
    get_user_minimal
)

user_router = APIRouter()


@user_router.get("/user")
async def user():
    return {"user": get_user_minimal()}


@user_router.get("/user/recent-tracks")
async def user():
    return {"user": get_user_recent_tracks()}


@user_router.get("/user/playcount")
async def playcount():
    return {"playcount": get_user_playcount()}


@user_router.get("/user/recent-scrobble")
async def get_recent_scrobble():
    return {"recent_scrobble": get_most_recent_scrobble()}
