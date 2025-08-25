from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.db_session import get_db


class BaseService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db


class DataService(BaseService):
    pass