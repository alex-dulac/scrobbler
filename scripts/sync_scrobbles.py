"""
usage: python -m scripts.sync_scrobbles
with inputs: python -m scripts.sync_scrobbles --time_from 2025-08-29 --time_to 2025-09-01

This script will fetch user recent tracks backwards and save them to the database.

Be mindful of API usage.
For 120k total scrobbles, this script will make 600 API calls to fetch all the data.
120000/200 = 600 API calls, or about 10 minutes.
"""
import argparse
import asyncio

from db.db_session import session_manager
from services.sync_service import SyncService


async def main(time_from: str = None, time_to: str = None):
    await session_manager.init_db()
    async with session_manager.session_factory() as db:
        try:
            sync_service = SyncService(db=db)
            await sync_service.sync_scrobbles(
                time_from=time_from,
                time_to=time_to,
            )

        finally:
            await db.close()
            await session_manager.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync scrobbles from Last.fm")
    parser.add_argument("--time_from", type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--time_to", type=str, help="End date in YYYY-MM-DD format")

    args = parser.parse_args()
    asyncio.run(main(args.time_from, args.time_to))

