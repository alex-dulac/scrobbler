from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container
from textual import work
from textual.reactive import reactive
from rich.text import Text

from models.integrations import Integration
from models.session import SessionScrobbles
from models.track import Track
from service.apple_music_service import poll_apple_music
from service.spotify_service import SpotifyService
from service.lastfm_service import LastFmService
from widgets import SongInfoWidget, ScrobbleProgressBar, SessionInfoWidget, ScrobbleHistoryWidget, css
from utils import poll_comparison, internet


class ScrobblerApp(App):
    CSS = css
    active_service = reactive("Apple Music")

    def __init__(self):
        super().__init__()
        self.active_integration = Integration.APPLE_MUSIC
        self.lastfm = LastFmService()
        self.spotify = SpotifyService()
        self.current_song = None
        self.session = SessionScrobbles(self.lastfm)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Button("Apple Music", id="apple-music", classes="active-button"),
            Button("Spotify", id="spotify"),
            Button("Process Pending", id="process-pending"),
            Button("Quit", id="quit", variant="error"),
            id="controls"
        )
        yield SongInfoWidget(id="song-info")
        yield ScrobbleProgressBar(id="scrobble-progress")
        yield ScrobbleHistoryWidget(id="scrobble-history")
        yield SessionInfoWidget(self.session, id="session-info")
        yield Static(id="scrobble-stats")
        yield Footer()

    def on_mount(self):
        self.set_interval(1, self.update_display)
        self.query_one(SongInfoWidget).update("Waiting for music...")
        self.query_one(ScrobbleProgressBar).update_progress(0, "Waiting for music...")
        self.query_one("#scrobble-stats").update(f"Pending scrobbles: {len(self.session.pending)}")
        self.query_one(ScrobbleHistoryWidget).update("Waiting for music...")

    @work
    async def action_quit(self) -> None:
        """Quit the application after processing any pending scrobbles."""
        self.notify("Thank you for scrobbling. Goodbye!")
        if self.session.pending:
            await self.session.process_pending_scrobbles()
        self.exit()

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
        elif event.button.id == "process-pending":
            self.process_pending_scrobbles()
        elif event.button.id == "quit":
            self.action_quit()

    @work
    async def process_pending_scrobbles(self):
        """Process any pending scrobbles."""
        if not self.session.pending:
            self.notify("No pending scrobbles to process")
            return

        count = await self.session.process_pending_scrobbles()
        if count > 0:
            self.notify(f"Processed {count} pending scrobbles")
            self.query_one(SessionInfoWidget).update_session_info()
        else:
            self.notify("Failed to process pending scrobbles")

        self.query_one("#scrobble-stats").update(f"Pending scrobbles: {len(self.session.pending)}")

    @staticmethod
    def format_song_info(song, status=""):
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

    @staticmethod
    def format_progress_info(self, current_time, threshold):
        """Format the progress information text."""
        percentage = min(100, int((current_time / threshold) * 100))
        return f"{current_time}s / {threshold}s ({percentage}%)"

    @work
    async def update_display(self):
        poll_service = poll_apple_music if self.active_integration == Integration.APPLE_MUSIC else self.spotify.poll_spotify
        poll: Track = await poll_service()
        compare = await poll_comparison(poll, self.current_song, None)

        self.sub_title = f"{self.active_service} | Scrobbles: {self.session.count}"
        self.query_one("#scrobble-stats").update(f"Pending scrobbles: {len(self.session.pending)}")

        if compare.no_song_playing:
            if self.current_song:
                self.current_song = None
            self.query_one(SongInfoWidget).update("No song playing")
            self.query_one(ScrobbleProgressBar).update_progress(0, "No song playing")
            self.query_one(ScrobbleHistoryWidget).update("No song playing")
            return

        if compare.update_song:
            self.current_song = poll
            self.current_song.time_played = 0
            if await internet():
                await self.query_one(ScrobbleHistoryWidget).update_history(self.lastfm, self.current_song)
                if compare.update_lastfm_now_playing:
                    self.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.current_song)

        if compare.update_song_playing_status:
            self.current_song.playing = poll.playing

        threshold = self.current_song.get_scrobbled_threshold()
        progress_value = min(1.0, self.current_song.time_played / threshold)
        progress_text = f"{self.current_song.time_played}s / {threshold}s"

        if self.current_song.playing is False:
            status = "Paused"
            self.query_one(SongInfoWidget).update(self.format_song_info(self.current_song, status))
            self.query_one(ScrobbleProgressBar).update_progress(progress_value, f"{progress_text} (Paused)")
        elif self.current_song.scrobbled:
            status = "✓ Scrobbled to Last.fm"
            self.query_one(SongInfoWidget).update(self.format_song_info(self.current_song, status))
            self.query_one(ScrobbleProgressBar).update_progress(1.0, f"{progress_text} (Scrobbled)")
        else:
            self.current_song.time_played += 1
            self.query_one(SongInfoWidget).update(self.format_song_info(self.current_song))
            self.query_one(ScrobbleProgressBar).update_progress(progress_value, progress_text)

            if self.current_song.is_ready_to_be_scrobbled():
                if not await internet():
                    self.session.add_pending(self.current_song)
                    self.query_one(SongInfoWidget).update(
                        self.format_song_info(self.current_song, "⏱ Pending scrobble (no internet)")
                    )
                else:
                    scrobbled_track = await self.lastfm.scrobble(self.current_song)
                    if scrobbled_track:
                        self.session.add_scrobble(scrobbled_track)
                        self.session.remove_pending(self.current_song)
                        self.current_song.scrobbled = True
                        self.query_one(SongInfoWidget).update(
                            self.format_song_info(self.current_song, "✓ Scrobbled to Last.fm")
                        )
                        self.query_one(ScrobbleProgressBar).update_progress(1.0, f"{progress_text} (Scrobbled)")
                        self.query_one(SessionInfoWidget).update_session_info()


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
