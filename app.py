from types import SimpleNamespace

from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

import settings
from service import (
    get_user,
    get_most_recent_scrobble,
    poll_apple_music,
    scrobble_to_lastfm
)


class ScrobblerAPI(FastAPI):
    state: SimpleNamespace


app = ScrobblerAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.current_song = None
app.state.is_scrobbling = False


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/username")
def username():
    return {"username": settings.USERNAME}


@app.get("/user")
def username():
    user = get_user()
    return {"user": user}


@app.get("/poll-song")
def get_current_song():
    result = poll_apple_music()

    if result and (app.state.current_song is None or result.track != app.state.current_song.track or result.artist != app.state.current_song.artist):
        app.state.current_song = result

    return {"current_song": app.state.current_song}


@app.get("/current-song")
def get_current_song():
    return {"current_song": app.state.current_song}


@app.get("/recent-scrobble")
def get_recent_scrobble():
    result = get_most_recent_scrobble()
    return {"played_track": result}


@app.get("/scrobble-status")
def scrobble_status():
    result = app.state.is_scrobbling
    return {"is_scrobbling": result}


@app.get("/scrobble-toggle")
def scrobble_toggle():
    is_scrobbling = app.state.is_scrobbling
    app.state.is_scrobbling = not is_scrobbling
    return {"is_scrobbling": app.state.is_scrobbling}


@app.post("/scrobble-song")
def scrobble_song():
    if not app.state.is_scrobbling:
        return {"result": "Scrobbling is not enabled. Please turn on scrobbling and try again."}

    if not app.state.current_song:
        return {"result": "No current song to scrobble."}

    if app.state.current_song.scrobbled:
        return {"result": "This song has already been scrobbled."}

    result = scrobble_to_lastfm(app.state.current_song)
    app.state.current_song.scrobbled = result
    return {"result": result}


@app.get("/sync")
def sync():
    return {
        "current_song": app.state.current_song,
        "is_scrobbling": app.state.is_scrobbling,
        "user": get_user()
    }


if __name__ == "__main__":
    uvicorn.run(app="__main__:app", host="0.0.0.0", port=8000, reload=True)
