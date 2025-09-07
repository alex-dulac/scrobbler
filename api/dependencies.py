from db.db_session import get_db
from services.sync_service import SyncService


async def get_sync_service():
    async for db in get_db():
        yield SyncService(db=db)
