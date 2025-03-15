# py-scrobbler

py-scrobbler is a tool for tracking and logging your music listening activity to Last.fm from Apple Music and Spotify. It is built using Python and leverages several modern technologies to provide a seamless experience.


## Features

- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.
- **Uvicorn**: An ASGI server for running the FastAPI application.
- **pylast**: A Python interface to Last.fm's API.
- **applescript**: A Python library to run AppleScript commands, used to interact with the Apple Music application.
- **spotipy**: A Python interface to Spotify's API.
- **Loguru**: A library for logging, providing an easy and powerful logging experience.

## Getting Started

### Prerequisites

- Python 3.10+
- Apple Music application installed on your macOS
- Last.fm account
- Spotify account (optional)

### Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/alex-dulac/py-scrobbler.git
    cd py-scrobbler
    ```

2. **Set up a virtual environment:**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Create a `.env` file:**
   Copy the `.env.example` file to `.env` and fill in your credentials and other necessary environment variables.
    ```sh
    cp .env.example .env
    ```

### Configuration

The `.env` file should contain the environment variables found in `.env.example`.

### Running the FastAPI Application

1. **Start the FastAPI server:**
   ```sh
    python app.py
    ```
   or
    ```sh
    uvicorn app:app --reload
    ```

### Running the Python Script App
1. **Run the loop script:**
    ```sh
    python loop.py
    ```
   ```
   2025-03-09 11:46:03.747 | INFO     | __main__:log_current_song:109 - Current song: `Ain't Talkin' 'Bout Love` by Van Halen from `Van Halen`
   2025-03-09 11:46:03.748 | INFO     | __main__:log_current_song:110 - Scrobble threshold: 114
   2025-03-09 11:46:06.074 | INFO     | __main__:log_current_song:114 - Count of scrobbles for current track: 29
   2025-03-09 11:46:06.074 | INFO     | __main__:log_current_song:115 - First scrobble: 2011-04-09 16:19:01
   2025-03-09 11:46:06.074 | INFO     | __main__:log_current_song:116 - Most recent scrobble: 2025-02-24 13:34:42
   2025-03-09 11:46:06.823 | INFO     | service.lastfm_service:update_lastfm_now_playing:177 - Updated Last.fm now playing
   2025-03-09 11:48:04.646 | INFO     | service.lastfm_service:scrobble_to_lastfm:201 - Scrobbled to LastFm: `Ain't Talkin' 'Bout Love` by Van Halen from `Van Halen`
   2025-03-09 11:48:04.647 | INFO     | __main__:run:171 - Scrobble Count: 42
   Song: `Ain't Talkin' 'Bout Love` by Van Halen from `Van Halen` | Scrobbled
   
   2025-03-09 11:49:52.605 | INFO     | __main__:log_current_song:109 - Current song: `On Through The Night` by Def Leppard from `High 'N' Dry`
   2025-03-09 11:49:52.605 | INFO     | __main__:log_current_song:110 - Scrobble threshold: 120
   2025-03-09 11:49:53.895 | INFO     | __main__:log_current_song:114 - Count of scrobbles for current track: 30
   2025-03-09 11:49:53.895 | INFO     | __main__:log_current_song:115 - First scrobble: 2024-02-03 14:01:37
   2025-03-09 11:49:53.895 | INFO     | __main__:log_current_song:116 - Most recent scrobble: 2025-02-13 15:15:21
   2025-03-09 11:49:54.656 | INFO     | service.lastfm_service:update_lastfm_now_playing:177 - Updated Last.fm now playing
   2025-03-09 11:51:58.973 | INFO     | service.lastfm_service:scrobble_to_lastfm:201 - Scrobbled to LastFm: `On Through The Night` by Def Leppard from `High 'N' Dry`
   2025-03-09 11:51:58.973 | INFO     | __main__:run:171 - Scrobble Count: 43
   Song: `On Through The Night` by Def Leppard from `High 'N' Dry` | Scrobbled
   ```

### Key Files

- **app.py**: The main entry point for the FastAPI application.
- **loop.py**: A script to run the application in a loop, continuously polling Apple Music for the current track.
- **config/settings.py**: Configuration settings for the application, including environment variables.
- **api/**: Contains the API routes and endpoints.
- **models/**: Contains the data models used in the application.
- **service/**: Contains the service modules for interacting with Apple Music, Last.fm, and Spotify.

## Frontend Integration

This API is used with the following React project: [scrobbler-web](https://github.com/alex-dulac/scrobbler-web). 
The React project provides a web interface to interact with this API, allowing users to view their scrobbled tracks, recent activity, and more.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

