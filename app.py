from fastapi import FastAPI
import uvicorn

from script import poll_apple_music, most_recent_scrobble, scrobble_to_lastfm, current_song

app = FastAPI()
app.state.current_song = None


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/current-song")
def get_current_song():
    result = poll_apple_music()
    app.state.current_song = result

    return {"current_song": app.state.current_song}


@app.get("/recent-scrobble")
def get_recent_scrobble():
    most_recent_scrobble()
    return {"message": "Check the console for the most recent scrobble"}


@app.post("/scrobble")
def scrobble_song():
    result = scrobble_to_lastfm(app.state.current_song)
    return {"result": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
