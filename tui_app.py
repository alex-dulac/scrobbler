from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, ProgressBar
from textual.containers import Container
from textual import work

from models.integrations import Integration
from service.apple_music_service import poll_apple_music
from service.spotify_service import SpotifyService
from service.lastfm_service import LastFmService
from utils import poll_comparison, internet

class ScrobblerApp(App):
    CSS = """
    #song-info {
        height: 3;
        content-align: center middle;
    }
    #progress {
        width: 50%;
        height: 1;
    }
    #controls {
        layout: horizontal;
        height: 3;
        align: center middle;
    }
    """

    def __init__(self):
        super().__init__()
        self.active_integration = Integration.APPLE_MUSIC
        self.lastfm = LastFmService()
        self.spotify = SpotifyService()
        self.current_song = None
        self.scrobble_count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="song-info")
        yield ProgressBar(id="progress")
        yield Container(
            Button("Apple Music", id="apple-music"),
            Button("Spotify", id="spotify"),
            id="controls"
        )
        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.update_display)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apple-music":
            self.active_integration = Integration.APPLE_MUSIC
        elif event.button.id == "spotify":
            self.active_integration = Integration.SPOTIFY

    @work
    async def update_display(self):
        poll_service = poll_apple_music if self.active_integration == Integration.APPLE_MUSIC else self.spotify.poll_spotify
        poll = await poll_service()
        compare = await poll_comparison(poll, self.current_song, None)

        if compare.no_song_playing:
            if self.current_song:
                self.current_song = None
            self.query_one("#song-info").update("No song playing")
            self.query_one("#progress").update(progress=0)
            return

        if compare.update_song:
            self.current_song = poll
            self.current_song.time_played = 0
            if compare.update_lastfm_now_playing and await internet():
                self.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.current_song)

        if compare.update_song_playing_status:
            self.current_song.playing = poll.playing

        base_status = f"{self.current_song.display_name()} | Time played: {self.current_song.time_played}s"
        if self.current_song.playing is False:
            self.query_one("#song-info").update(f"{base_status} | Paused")
        elif self.current_song.scrobbled:
            self.query_one("#song-info").update(f"{base_status} | Scrobbled")
        else:
            self.current_song.time_played += 1
            self.query_one("#song-info").update(f"{self.current_song.display_name()} | Time played: {self.current_song.time_played}s")
            self.query_one("#progress").update(progress=self.current_song.time_played / self.current_song.get_scrobbled_threshold())

            if self.current_song.is_ready_to_be_scrobbled() and await internet():
                scrobbled_track = await self.lastfm.scrobble(self.current_song)
                if scrobbled_track:
                    self.current_song.scrobbled = True
                    self.scrobble_count += 1
                    self.sub_title = f"Scrobbles: {self.scrobble_count}"


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()