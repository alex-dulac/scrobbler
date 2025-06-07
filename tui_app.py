from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container
from textual import work
from textual.reactive import reactive
from rich.text import Text
from rich.console import RenderableType
from rich.progress import Progress, BarColumn, TextColumn

from models.integrations import Integration
from models.track import Track
from service.apple_music_service import poll_apple_music
from service.spotify_service import SpotifyService
from service.lastfm_service import LastFmService
from utils import poll_comparison, internet

css = """
    #song-info {
        height: 3;
        content-align: center middle;
        margin: 1 0;
    }
    #progress {
        height: 1;
        margin: 1 0;
    }
    #controls {
        layout: horizontal;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
    }
    .active-button {
        background: $accent;
    }
    """

class SongInfoWidget(Static):
    """Custom widget to display song information with rich formatting."""

    def render(self) -> RenderableType:
        return self.renderable


class ScrobbleProgressBar(Static):
    def __init__(self, id=None):
        super().__init__(id=id)
        self.progress = 0.0
        self.progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            TextColumn("{task.description}"),
            expand=True
        )
        self.task_id = self.progress_bar.add_task("", total=100, completed=0)

    def update_progress(self, value, description=""):
        """Update progress value (0-1) and description."""
        percentage = min(100, max(0, int(value * 100)))
        self.progress = value
        self.progress_bar.update(self.task_id, completed=percentage, description=description)
        self.update(self.progress_bar)


class ScrobblerApp(App):
    CSS = css
    active_service = reactive("Apple Music")

    def __init__(self):
        super().__init__()
        self.active_integration = Integration.APPLE_MUSIC
        self.lastfm = LastFmService()
        self.spotify = SpotifyService()
        self.current_song = None
        self.scrobble_count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield SongInfoWidget(id="song-info")
        yield ScrobbleProgressBar(id="scrobble-progress")
        yield Container(
            Button("Apple Music", id="apple-music", classes="active-button"),
            Button("Spotify", id="spotify"),
            id="controls"
        )
        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.update_display)
        self.query_one("#song-info").update("Waiting for music...")
        self.query_one(ScrobbleProgressBar).update_progress(0, "Waiting for music...")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apple-music":
            self.active_integration = Integration.APPLE_MUSIC
            self.active_service = "Apple Music"
            self.query_one("#apple-music").add_class("active-button")
            self.query_one("#spotify").remove_class("active-button")
        elif event.button.id == "spotify":
            self.active_integration = Integration.SPOTIFY
            self.active_service = "Spotify"
            self.query_one("#spotify").add_class("active-button")
            self.query_one("#apple-music").remove_class("active-button")

    def format_song_info(self, song, status=""):
        """Format song information with rich styling."""
        text = Text()

        text.append(f"{song.name}\n", style="bold white")
        text.append(f"by ", style="dim")
        text.append(f"{song.artist}", style="italic cyan")
        if song.album:
            text.append(f" • ", style="dim")
            text.append(f"{song.album}", style="italic green")
        if status:
            text.append(f"\n{status}", style="yellow" if "Scrobbled" in status else "blue")

        return text

    def format_progress_info(self, current_time, threshold):
        """Format the progress information text."""
        percentage = min(100, int((current_time / threshold) * 100))
        return f"{current_time}s / {threshold}s ({percentage}%)"

    @work
    async def update_display(self):
        poll_service = poll_apple_music if self.active_integration == Integration.APPLE_MUSIC else self.spotify.poll_spotify
        poll: Track = await poll_service()
        compare = await poll_comparison(poll, self.current_song, None)

        # Update the subtitle to show active service and scrobble count
        self.sub_title = f"{self.active_service} | Scrobbles: {self.scrobble_count}"

        if compare.no_song_playing:
            if self.current_song:
                self.current_song = None
            self.query_one("#song-info").update("No song playing")
            self.query_one(ScrobbleProgressBar).update_progress(0, "No song playing")
            return

        if compare.update_song:
            self.current_song = poll
            self.current_song.time_played = 0
            if compare.update_lastfm_now_playing and await internet():
                self.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.current_song)

        if compare.update_song_playing_status:
            self.current_song.playing = poll.playing

        threshold = self.current_song.get_scrobbled_threshold()
        progress_value = min(1.0, self.current_song.time_played / threshold)
        progress_text = f"{self.current_song.time_played}s / {threshold}s"

        if self.current_song.playing is False:
            status = "Paused"
            self.query_one("#song-info").update(self.format_song_info(self.current_song, status))
            self.query_one(ScrobbleProgressBar).update_progress(progress_value, f"{progress_text} (Paused)")
        elif self.current_song.scrobbled:
            status = "✓ Scrobbled to Last.fm"
            self.query_one("#song-info").update(self.format_song_info(self.current_song, status))
            self.query_one(ScrobbleProgressBar).update_progress(1.0, f"{progress_text} (Scrobbled)")
        else:
            self.current_song.time_played += 1
            self.query_one("#song-info").update(self.format_song_info(self.current_song))
            self.query_one(ScrobbleProgressBar).update_progress(progress_value, progress_text)

            if self.current_song.is_ready_to_be_scrobbled() and await internet():
                scrobbled_track = await self.lastfm.scrobble(self.current_song)
                if scrobbled_track:
                    self.current_song.scrobbled = True
                    self.scrobble_count += 1
                    self.query_one("#song-info").update(self.format_song_info(self.current_song, "✓ Scrobbled to Last.fm"))
                    self.query_one(ScrobbleProgressBar).update_progress(1.0, f"{progress_text} (Scrobbled)")



if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()