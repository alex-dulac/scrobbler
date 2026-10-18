import asyncio
import os
from contextlib import suppress
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

from core import config
from core.database import session_manager
from library.dependencies import get_ipod_watcher, get_scrobbler_runtime
from routers.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_connected = False
    runtime = None
    profile_task = None
    ipod_watcher = None

    try:
        try:
            await asyncio.wait_for(session_manager.init_db(), timeout=5)
            db_connected = True
            logger.info("Database connection successful.")
        except Exception as error:
            logger.warning(f"Could not connect to database: {error}")
            logger.warning("Some API features might not work as expected.")
            try:
                await session_manager.close_db()
            except Exception as close_error:
                logger.warning(
                    "Could not clean up the failed database connection: "
                    f"{close_error}"
                )

        runtime = await get_scrobbler_runtime()
        from core.desktop_storage import state_directory
        runtime.engine.state.session.attach_pending_store(state_directory() / "pending.json")

        async def load_profile():
            from services.lastfm_service import get_lastfm_user
            try:
                runtime.engine.state.user = await get_lastfm_user()
            except Exception as error:
                logger.warning(f"Last.fm profile is unavailable: {error}")

        profile_task = asyncio.create_task(load_profile())
        runtime.engine.set_database_available(db_connected)
        await runtime.start()
        logger.info("Scrobbler runtime started.")

        ipod_watcher = await get_ipod_watcher()
        ipod_watcher.start()

        yield
    finally:
        if ipod_watcher is not None:
            await ipod_watcher.stop()
        if profile_task is not None:
            profile_task.cancel()
            with suppress(asyncio.CancelledError):
                await profile_task
        try:
            if runtime is not None:
                try:
                    result = await runtime.stop(process_pending=os.environ.get("SCROBBLER_MANAGED") != "1")
                    logger.info(
                        "Scrobbler runtime stopped. "
                        f"Processed {result.pending_processed} pending scrobble(s); "
                        f"{result.pending_remaining} remain."
                    )
                except asyncio.CancelledError:
                    await runtime.stop(process_pending=os.environ.get("SCROBBLER_MANAGED") != "1")
                    raise
                except Exception as error:
                    logger.exception(
                        f"Could not stop scrobbler runtime cleanly: {error}"
                    )
        finally:
            if db_connected:
                try:
                    await session_manager.close_db()
                    logger.info("Database connection closed.")
                except Exception as error:
                    logger.exception(f"Could not close database connection: {error}")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.WEB_APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get('/')
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app="__main__:app", host="0.0.0.0", port=8000, reload=True)
