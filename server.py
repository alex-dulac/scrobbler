from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

from config import settings
from api.router import router
from db.db_session import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_connected = False

    try:
        await session_manager.init_db()
        db_connected = True
        logger.info("Database connection successful.")
    except Exception as e:
        logger.warning(f"Could not connect to database: {e}")
        logger.warning(f"Some api features might not work as expected.")

    yield

    if db_connected:
        await session_manager.close_db()
        logger.info("Database connection closed.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.WEB_APP_URL],
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
