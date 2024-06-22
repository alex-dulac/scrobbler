from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import settings
from api.router import router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.WEB_APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app="__main__:app", host="0.0.0.0", port=8000, reload=True)
