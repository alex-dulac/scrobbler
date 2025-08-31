"""
usage: python -m scripts.sync_scrobbles

This script will fetch user recent tracks backwards and save them to the database.

Be mindful of API usage.
For 120k total scrobbles, this script will make 600 API calls to fetch all the data.
120000/200 = 600 API calls, or about 10 minutes.
"""

from datetime import datetime
import time
import asyncio

from loguru import logger

from services.lastfm_service import LastFmService
from db.db_session import session_manager
from db.tables import Scrobble

async def main():
    await session_manager.init_db()
    async with session_manager.session_factory() as db:
        try:
            limit = 200  # max allowed by the API
            time_to = None   # start with the most recent
            fetched = 0
            lastfm_service = LastFmService()

            while True:
                tracks = lastfm_service.user.get_recent_tracks(limit=limit, time_to=time_to)

                if not tracks:
                    break

                batch_scrobbles = []
                for t in tracks:
                    scrobble = Scrobble(
                        track_name=t.track.title,
                        artist_name=t.track.artist.name if t.track.artist else "Unknown Artist",
                        album_name=t.album if t.album else None,
                        scrobbled_at=datetime.fromtimestamp(int(t.timestamp)),
                        created_at=datetime.now()
                    )
                    batch_scrobbles.append(scrobble)

                db.add_all(batch_scrobbles)
                await db.commit()

                fetched += len(tracks)
                logger.info(f"Fetched and saved {fetched} scrobbles...")

                # update time_to to the oldest timestamp from this batch - 1
                oldest = int(tracks[-1].timestamp)
                time_to = oldest - 1

                time.sleep(0.5)  # respect Lastfm's API

            logger.info(f"Done. Total fetched and saved: {fetched}")

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            await db.rollback()

        finally:
            await db.close()
            await session_manager.close_db()


if __name__ == "__main__":
    asyncio.run(main())

