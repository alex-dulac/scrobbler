import time

from fastapi import APIRouter, Query, Depends

from library.state import get_app_state
from library.dependencies import get_lastfm_service, get_spotify_service
from services.lastfm_service import LastFmService, get_lastfm_account_details
from services.apple_music_service import get_macos_information
from services.spotify_service import SpotifyService

user_router = APIRouter()

@user_router.get("/user/")
async def user():
    return {"user": get_lastfm_account_details()}


@user_router.get("/user/accounts/lastfm")
async def user_lastfm():
    return {"user": get_lastfm_account_details()}


@user_router.get("/user/accounts/apple/")
async def user_mac_os():
    return {"mac_os": await get_macos_information()}


@user_router.get("/user/accounts/spotify/")
async def user_spotify(spotify: SpotifyService = Depends(get_spotify_service)):
    return {"spotify_account": await spotify.get_spotify_account_information()}


@user_router.get("/user/recent-tracks/")
async def recent_tracks(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"recent_tracks": await lastfm.get_user_recent_tracks()}


@user_router.get("/user/loved-tracks/")
async def loved_tracks(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"loved_tracks": await lastfm.get_user_loved_tracks()}


@user_router.get("/user/top-artists/")
async def top_artists(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"top_artists": await lastfm.get_user_top_artists()}


@user_router.get("/user/top-albums/")
async def top_artists(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"top_albums": await lastfm.get_user_top_albums()}


@user_router.get("/user/playcount/")
async def playcount(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"playcount": await lastfm.get_user_playcount()}


@user_router.get("/user/current-track-scrobbles/")
async def get_track_scrobbles(lastfm: LastFmService = Depends(get_lastfm_service)):
    app_state = await get_app_state()

    result = await lastfm.current_track_user_scrobbles(app_state.current_song) if app_state.current_song else None

    return {"scrobbles": result}


@user_router.get("/user/charts/albums/weekly/")
async def get_weekly_album_charts(
        from_date: str | None = Query(None, description="Start date for the weekly album charts"),
        to_date: str | None = Query(None, description="End date for the weekly album charts"),
        lastfm: LastFmService = Depends(get_lastfm_service)
):
    """
    Get the weekly album charts for the given date range.
    If no date range is provided, it defaults to the current week.
    """
    if to_date is None and from_date is None:
        to_date = int(time.time())
        from_date = to_date - (7 * 86400)

    results = await lastfm.user_weekly_album_charts(from_date, to_date)

    return {"data": results}


@user_router.get("/user/weekly-chart-dates/")
async def get_weekly_chart_dates(lastfm: LastFmService = Depends(get_lastfm_service)):
    results = await lastfm.user_weekly_chart_dates()

    return {"data": results}


@user_router.get("/user/30-day-stats/")
async def overview_stats(lastfm: LastFmService = Depends(get_lastfm_service)):
    return {"data": await lastfm.get_user_30_day_stats()}
