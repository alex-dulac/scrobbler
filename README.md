# py-scrobbler

py-scrobbler is a tool for tracking and logging your music listening activity to Last.fm from Apple Music and Spotify. It is built using Python and leverages several modern technologies to provide a seamless experience.


## Features

- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.
- **Uvicorn**: An ASGI server for running the FastAPI application.
- **pylast**: A Python interface to Last.fm's API.
- **applescript**: A Python library to run AppleScript commands, used to interact with the Apple Music application.
- **spotipy**: A Python interface to Spotify's API.
- **Loguru**: A library for logging, providing an easy and powerful logging experience.
- **Textual**: A TUI (Text User Interface) framework for Python, used to create an interactive terminal interface.

## Getting Started

### Prerequisites

- Python 3.10+
- Apple Music application installed on your macOS (if you want to scrobble from Apple Music)
- Spotify account (if you want to scrobble from Spotify)
- Last.fm account

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

## Running the Application

You can run py-scrobbler in three different ways:

### FastAPI Web Application

The FastAPI application provides a web API that can be consumed by frontend applications (see [scrobbler-web](https://github.com/alex-dulac/scrobbler-web) for accompanying React app).

1. **Start the FastAPI server:**
   ```sh
    python app.py
    ```
   or
    ```sh
    uvicorn app:app --reload
    ```
This starts the FastAPI server on http://localhost:8000. 
<br>
API documentation is built-in at http://localhost:8000/docs.

### Text User Interface (TUI)

The TUI application provides an interactive terminal interface with visual elements like progress bars and formatted text.

1. **Start the TUI:**
   ```sh
    python tui_app.py
    ```
   
Features of the TUI:
- Switch between Apple Music and Spotify with a button click
- Visual progress bar showing scrobble progress
- Session statistics showing top artists and repeat scrobbles
- Process pending scrobbles that couldn't be sent due to connectivity issues
- Rich text formatting for better readability

### Command Line Interface

The loop script provides a simple command-line interface that displays the currently playing track and scrobble status.

1. **Run the loop script:**
    ```sh
    python loop.py
    ```
   Defaults to Apple Music. You can specify which music service to use:
    ```sh
    python loop.py --integration spotify
    ```

   Sample output:
   ```
   2025-05-08 09:36:17.790 | INFO     | __main__:log_current_song:35 - Apple Music currently playing:
   2025-05-08 09:36:17.790 | INFO     | __main__:log_current_song:36 -   `The Freaks, Nerds, & Romantics` by The Bouncing Souls from `Maniacal Laughter`
   2025-05-08 09:36:17.791 | INFO     | __main__:log_current_song:37 - Scrobble threshold: 76
   2025-05-08 09:36:18.224 | INFO     | __main__:log_current_song:48 - Count of scrobbles for current track: 41
   2025-05-08 09:36:18.224 | INFO     | __main__:log_current_song:49 - First scrobble: 2008-08-20 19:32:01
   2025-05-08 09:36:18.224 | INFO     | __main__:log_current_song:50 - Most recent scrobble: 2024-10-29 10:19:09
   2025-05-08 09:36:18.427 | INFO     | service.lastfm_service:update_now_playing:177 - Updated Last.fm now playing
   `The Freaks, Nerds, & Romantics` by The Bouncing Souls from `Maniacal Laughter` | Time played: 28s
   ```

### Key Files

- **app.py**: The main entry point for the FastAPI application.
- **tui_app.py**: A Text User Interface application with interactive elements.
- **loop.py**: A script to run the application in a loop, continuously polling music services for the current track.
- **config/settings.py**: Configuration settings for the application, including environment variables.
- **api/**: Contains the API routes and endpoints.
- **models/**: Contains the data models used in the application.
- **service/**: Contains the service modules for interacting with Apple Music, Last.fm, and Spotify.

## Contributing

Contributions are welcome and encouraged! Please open an issue or submit a pull request for any changes.

