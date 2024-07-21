# py-scrobbler

Apple Music Scrobbler is a tool for tracking and logging your music listening activity from Apple Music. It is built using Python and leverages several modern technologies to provide a seamless experience.



## Features

- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.
- **Uvicorn**: An ASGI server for running the FastAPI application.
- **pylast**: A Python interface to Last.fm's API.
- **applescript**: A Python library to run AppleScript commands, used to interact with the Apple Music application.
- **Loguru**: A library for logging, providing an easy and powerful logging experience.

## Getting Started

### Prerequisites

- Python 3.8+
- Apple Music application installed on your macOS
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
   Copy the `.env.example` file to `.env` and fill in your Last.fm API credentials and other necessary environment variables.
    ```sh
    cp .env.example .env
    ```

### Configuration

The `.env` file should contain the environment variables found in `.env.example`.

### Running the Application

1. **Start the FastAPI server:**
    ```sh
    uvicorn app:app --reload
    ```

2. **Run the loop script:**
    ```sh
    python run_as_loop.py
    ```

### Key Files

- **app.py**: The main entry point for the FastAPI application.
- **model.py**: Contains the data models used in the application.
- **loop.py**: A script to run the application in a loop, continuously polling Apple Music for the current track.
- **config/settings.py**: Configuration settings for the application, including environment variables.
- **api/**: Contains the API routes and endpoints.
- **service/**: Contains the service modules for interacting with Apple Music and Last.fm.

## Frontend Integration

This API is used with the following React project: [apple-music-scrobbler-web](https://github.com/alex-dulac/apple-music-scrobbler-web). 
The React project provides a web interface to interact with this API, allowing users to view their scrobbled tracks, recent activity, and more.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

See the [LICENSE](LICENSE.txt) file for details.