"""
usage: python -m scripts.sync_ref_data

Gets the distinct tracks, artists, and albums from the user
scrobble history, and updates applicable database reference tables
with data from Last.fm's API.

"""

import asyncio

from loguru import logger

from db.db_session import session_manager, get_db
from services.sync_service import SyncService


async def main():
    await session_manager.init_db()
    async with session_manager.session_factory() as db:
        try:
            sync_service = SyncService(db=db)
            await sync_service.sync_all()

            # Alternatively, sync individual entities:

            # await sync_service.sync_artists()
            # await sync_service.sync_albums()
            # await sync_service.sync_tracks()

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            await db.rollback()

        finally:
            await db.close()
            await session_manager.close_db()


if __name__ == "__main__":
    asyncio.run(main())

