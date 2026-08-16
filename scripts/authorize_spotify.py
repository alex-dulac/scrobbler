"""Authorize Spotify and save a fresh token in Spotipy's local cache.

Run from the project root with: ``uv run python -m scripts.authorize_spotify``.
The redirect URI must exactly match ``SPOTIFY_REDIRECT_URI`` in both ``.env``
and the Spotify developer dashboard.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from secrets import token_urlsafe
from urllib.parse import parse_qs, urlparse
import sys
import webbrowser

from spotipy.oauth2 import SpotifyOAuth

from core import config
from services.spotify_service import scope


class AuthorizationCallbackHandler(BaseHTTPRequestHandler):
    authorization_code: str | None = None
    error: str | None = None
    expected_state: str | None = None

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        if query.get("state", [None])[0] != self.expected_state:
            type(self).error = "Spotify returned an invalid authorization state."
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed. You can close this window.")
            return

        type(self).authorization_code = query.get("code", [None])[0]
        type(self).error = query.get("error", [None])[0]
        self.send_response(200 if type(self).authorization_code else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h1>Spotify authorized</h1><p>You can close this window and return to Scrobbler.</p>"
            if type(self).authorization_code
            else b"<h1>Spotify authorization failed</h1><p>You can close this window and try again.</p>"
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    if not all((config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET, config.SPOTIFY_REDIRECT_URI)):
        sys.exit("Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI in .env first.")

    redirect = urlparse(config.SPOTIFY_REDIRECT_URI)
    if redirect.scheme != "http" or redirect.hostname != "127.0.0.1":
        sys.exit("SPOTIFY_REDIRECT_URI must be a local http URL, such as http://127.0.0.1:8080.")

    oauth = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=scope,
        open_browser=False,
    )
    AuthorizationCallbackHandler.expected_state = token_urlsafe(32)
    server = HTTPServer((redirect.hostname, redirect.port or 80), AuthorizationCallbackHandler)
    authorization_url = oauth.get_authorize_url(state=AuthorizationCallbackHandler.expected_state)

    print("Opening Spotify authorization in your browser...")
    webbrowser.open(authorization_url)
    server.handle_request()
    server.server_close()

    if AuthorizationCallbackHandler.error:
        sys.exit(f"Spotify authorization failed: {AuthorizationCallbackHandler.error}")
    if not AuthorizationCallbackHandler.authorization_code:
        sys.exit("Spotify did not return an authorization code.")

    oauth.get_access_token(AuthorizationCallbackHandler.authorization_code, check_cache=False)
    print("Spotify authorized. Restart Scrobbler to begin polling Spotify.")


if __name__ == "__main__":
    main()
