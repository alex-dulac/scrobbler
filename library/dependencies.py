from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from services.lastfm_service import LastFmService
from services.spotify_service import SpotifyService
from services.sync_service import SyncService

if TYPE_CHECKING:
    from services.ipod_watcher import IpodWatcher
    from services.scrobbler_engine import ScrobblerEngine
    from services.scrobbler_runtime import ScrobblerRuntime


lastfm: LastFmService | None = None
spotify: SpotifyService | None = None
sync_service: SyncService | None = None
scrobbler_engine: ScrobblerEngine | None = None
scrobbler_runtime: ScrobblerRuntime | None = None
ipod_watcher: IpodWatcher | None = None

_scrobbler_engine_lock = asyncio.Lock()
_scrobbler_runtime_lock = asyncio.Lock()


async def get_lastfm_service() -> LastFmService:
    global lastfm
    if lastfm is None:
        lastfm = LastFmService()
    return lastfm


async def get_spotify_service() -> SpotifyService:
    global spotify
    if spotify is None:
        spotify = SpotifyService()
    return spotify


async def get_sync_service() -> SyncService:
    global sync_service
    if sync_service is None:
        sync_service = SyncService()
    return sync_service


async def get_scrobbler_engine() -> ScrobblerEngine:
    global scrobbler_engine

    if scrobbler_engine is not None:
        return scrobbler_engine

    async with _scrobbler_engine_lock:
        if scrobbler_engine is not None:
            return scrobbler_engine

        from library.integrations import Integration
        from library.state import get_app_state
        from repositories.scrobble_repo import ScrobbleRepository
        from services.apple_music_service import (
            playback_control as apple_music_playback_control,
            poll_apple_music,
        )
        from services.scrobbler_engine import ScrobblerEngine

        state = await get_app_state()
        lastfm_service = await get_lastfm_service()
        spotify_service = await get_spotify_service()

        scrobbler_engine = ScrobblerEngine(
            state=state,
            lastfm=lastfm_service,
            pollers={
                Integration.APPLE_MUSIC: poll_apple_music,
                Integration.SPOTIFY: spotify_service.poll_spotify,
            },
            playback_controllers={
                Integration.APPLE_MUSIC: apple_music_playback_control,
                Integration.SPOTIFY: spotify_service.playback_control,
            },
            repository_factory=ScrobbleRepository,
            database_available=False,
        )
        return scrobbler_engine


async def get_ipod_watcher() -> IpodWatcher:
    global ipod_watcher

    if ipod_watcher is None:
        from services.ipod_watcher import IpodWatcher

        ipod_watcher = IpodWatcher(await get_scrobbler_engine(), await get_lastfm_service())
    return ipod_watcher


async def get_scrobbler_runtime() -> ScrobblerRuntime:
    global scrobbler_runtime

    if scrobbler_runtime is not None:
        return scrobbler_runtime

    async with _scrobbler_runtime_lock:
        if scrobbler_runtime is not None:
            return scrobbler_runtime

        from services.scrobbler_runtime import ScrobblerRuntime

        engine = await get_scrobbler_engine()
        scrobbler_runtime = ScrobblerRuntime(engine)
        return scrobbler_runtime
