"""Album-keyed artwork lookup, kept separate from the playback polling path."""
import asyncio
import time
from collections import OrderedDict

import pylast
from fastapi import APIRouter, Depends, Query

from library.dependencies import get_lastfm_service
from services.lastfm_service import LastFmService

artwork_router = APIRouter(prefix="/artwork", tags=["artwork"])
_cache: OrderedDict[tuple[str, str], tuple[float, str | None]] = OrderedDict()
_lock = asyncio.Lock()


@artwork_router.get("/")
async def album_artwork(
    artist: str = Query(min_length=1, max_length=300),
    album: str = Query(min_length=1, max_length=300),
    lastfm: LastFmService = Depends(get_lastfm_service),
):
    key = (artist.strip().casefold(), album.strip().casefold())
    async with _lock:
        cached = _cache.get(key)
        if cached and cached[0] > time.monotonic():
            _cache.move_to_end(key)
            return {"url": cached[1]}
    try:
        def fetch():
            return lastfm.network.get_album(artist, album).get_cover_image(size=pylast.SIZE_MEGA)
        url = await asyncio.wait_for(asyncio.to_thread(fetch), timeout=6)
        if not isinstance(url, str) or not url.startswith("https://"):
            url = None
    except Exception:
        url = None
    async with _lock:
        _cache[key] = (time.monotonic() + (3600 if url else 60), url)
        _cache.move_to_end(key)
        while len(_cache) > 128:
            _cache.popitem(last=False)
    return {"url": url}
