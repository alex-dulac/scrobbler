# py-scrobbler

py-scrobbler is a tool for tracking and logging your music listening activity from Apple Music and Spotify. It is built using Python and leverages several modern technologies to provide a seamless experience.



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
- Spotify account
- Last.fm account

### Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/alex-dulac/apple-music-scrobbler.git
    cd apple-music-scrobbler
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
   2025-01-18 10:29:02.425 | INFO     | __main__:handle_arguments:74 - Active Integration: APPLE_MUSIC
   2025-01-18 10:29:02.554 | INFO     | __main__:log_current_song:83 - Scrobble Count: 0
   2025-01-18 10:29:02.554 | INFO     | __main__:log_current_song:88 - Current song: '`Women` by Def Leppard from `Hysteria`'
   2025-01-18 10:29:02.554 | INFO     | __main__:log_current_song:89 - Scrobble threshold: 120
   2025-01-18 10:29:03.998 | INFO     | __main__:log_current_song:92 - Count of scrobbles for current track: 80
   2025-01-18 10:29:04.168 | INFO     | service.lastfm_service:update_lastfm_now_playing:177 - Updated Last.fm now playing
   ==============================================================================================================
   2025-01-18 10:31:09.242 | INFO     | service.lastfm_service:scrobble_to_lastfm:198 - Scrobbled to LastFm: `Women` by Def Leppard from `Hysteria`
   2025-01-18 10:31:21.622 | INFO     | __main__:log_current_song:83 - Scrobble Count: 1                         
   2025-01-18 10:31:21.623 | INFO     | __main__:log_current_song:88 - Current song: '`Rocket` by Def Leppard from `Hysteria`'
   2025-01-18 10:31:21.623 | INFO     | __main__:log_current_song:89 - Scrobble threshold: 120
   2025-01-18 10:31:22.975 | INFO     | __main__:log_current_song:92 - Count of scrobbles for current track: 76
   2025-01-18 10:31:23.123 | INFO     | service.lastfm_service:update_lastfm_now_playing:177 - Updated Last.fm now playing
   ==============================================================================================================
   Song: `Rocket` by Def Leppard from `Hysteria` | Time played: 105s
   ```

### Key Files

- **app.py**: The main entry point for the FastAPI application.
- **model.py**: Contains the data models used in the application.
- **loop.py**: A script to run the application in a loop, continuously polling Apple Music for the current track.
- **config/settings.py**: Configuration settings for the application, including environment variables.
- **api/**: Contains the API routes and endpoints.
- **service/**: Contains the service modules for interacting with Apple Music and Last.fm.

## Frontend Integration

This API is used with the following React project: [scrobbler-web](https://github.com/alex-dulac/scrobbler-web). 
The React project provides a web interface to interact with this API, allowing users to view their scrobbled tracks, recent activity, and more.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

