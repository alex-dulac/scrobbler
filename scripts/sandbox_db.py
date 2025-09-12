"""
usage: python -m scripts.sandbox_db

Simple script to test/debug the ScrobbleRepository class.
"""
import asyncio

from core.database import session_manager
from db.filters import ScrobbleFilter
from repositories.repository import ScrobbleRepository


async def main():
    await session_manager.init_db()
    async with session_manager.session_factory() as db:
        try:
            repo = ScrobbleRepository(db=db)
            f = ScrobbleFilter(scrobbled_after="2025-01-01")
            result = await repo.get_scrobbles(f)

            for scrobble in result:
                print(scrobble.track_name)

            albums = await repo.get_albums_from_scrobbles()
            for album in albums:
                print(album)

            test = await repo.get_artists_with_no_ref_data()
            for t in test:
                print(t)

        finally:
            await db.close()
            await session_manager.close_db()
            print("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())

