"""
usage: python -m scripts.sandbox_db

Simple script to test/debug the DataService class.
"""
import asyncio

from services.data_service import DataService, ScrobbleFilter
from db.db_session import session_manager

async def main():
    await session_manager.init_db()
    async with session_manager.session_factory() as db:
        try:
            data_service = DataService(db=db)
            filter = ScrobbleFilter(scrobbled_after="2025-01-01")
            result = await data_service.get_scrobbles(filter)

            for scrobble in result:
                print(scrobble.track_name)

            albums = await data_service.get_albums_from_scrobbles()
            for album in albums:
                print(album)

            test = await data_service.get_artists_with_no_ref_data()
            for t in test:
                print(t)

        finally:
            await db.close()
            await session_manager.close_db()
            print("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())

