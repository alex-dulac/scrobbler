import asyncio
from enum import EnumType

from textual.app import App, ComposeResult
from textual.visual import VisualType
from textual.widgets import Header, Footer, Button
from textual.containers import Container
from textual import work
from rich.text import Text

from models.integrations import Integration, PlaybackAction
from models.session import SessionScrobbles
from models.track import Track
from service.apple_music_service import poll_apple_music, playback_control
from service.spotify_service import SpotifyService
from service.lastfm_service import LastFmService
import widgets
from utils import poll_comparison, Comparison


class ScrobbleStatus(EnumType):
    SCROBBLED = "✓ Scrobbled to Last.fm"
    PAUSED = "Paused"
    PENDING = "⏱ Pending scrobble (no internet)"
    WAITING  = "Waiting for music..."
    NOT_PLAYING = "No song playing"


class ScrobblerApp(App):
    CSS = widgets.css

    def __init__(self):
        super().__init__()
        self.active_integration = Integration.APPLE_MUSIC
        self.lastfm = LastFmService()
        self.spotify = SpotifyService()
        self.current_song = None
        self.session = SessionScrobbles(self.lastfm)
        self.current_view = "history-list"
        self.is_scrobbling = False # mitigate duplicate scrobbles

    def compose(self) -> ComposeResult:
        yield Header()
        # playback controls
        yield Container(
            Button("Apple Music", id="apple-music", classes="active-button"),
            Button("Spotify", id="spotify"),
            Button("⏯ Play/Pause", id="play-pause"),
            Button("⏮ Back", id="previous-track"),
            Button("⏭ Skip", id="next-track"),
            Button("Quit", id="quit", variant="error"),
            classes="controls",
            id="controls"
        )
        # view controls
        yield Container(
            Button("History List", id="show-history-list"),
            Button("History Chart", id="show-history-chart"),
            Button("Session", id="show-session"),
            classes="controls",
            id="view-controls"
        )
        # song info and progress bar
        yield widgets.SongInfoWidget(id="song-info")
        yield widgets.ScrobbleProgressBar(id="scrobble-progress")
        # views
        yield widgets.HistoryListWidget(id="history-list")
        yield widgets.HistoryChartWidget(id="history-chart")
        yield widgets.SessionInfoWidget(self.session, id="session-info")
        yield Footer()

    def update_progress_bar(self, progress_value: float, progress_text: str):
        self.query_one(widgets.ScrobbleProgressBar).update_progress(progress_value, progress_text)

    def update_song_info(self, info: VisualType):
        self.query_one(widgets.SongInfoWidget).update(info)

    def update_session_info(self):
        self.query_one(widgets.SessionInfoWidget).update_session_info()

    def on_mount(self):
        self.set_interval(1, self.update_display)
        self.update_song_info(ScrobbleStatus.WAITING)
        self.update_progress_bar(0, ScrobbleStatus.WAITING)
        self.query_one(widgets.HistoryListWidget).update(ScrobbleStatus.WAITING)
        self.update_view_visibility()

    def update_view_visibility(self):
        history_list = self.query_one("#history-list")
        history_chart = self.query_one("#history-chart")
        session = self.query_one("#session-info")

        if self.current_view == "history-list":
            history_list.display = True
            history_chart.display = False
            session.display = False
        elif self.current_view == "history-chart":
            history_list.display = False
            history_chart.display = True
            session.display = False
        elif self.current_view == "session-info":
            history_list.display = False
            history_chart.display = False
            session.display = True

    @work
    async def action_quit(self) -> None:
        """Quit the application after processing any pending scrobbles."""
        self.notify("Thank you for scrobbling. Goodbye!")

        if self.session.pending:
            count = await self.session.process_pending_scrobbles()
            self.notify(f"Processed {count} pending scrobbles.")

        await asyncio.sleep(2)
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # main
        if event.button.id == "apple-music":
            self.active_integration = Integration.APPLE_MUSIC
            self.query_one("#apple-music").add_class("active-button")
            self.query_one("#spotify").remove_class("active-button")
        elif event.button.id == "spotify":
            self.active_integration = Integration.SPOTIFY
            self.query_one("#spotify").add_class("active-button")
            self.query_one("#apple-music").remove_class("active-button")
        elif event.button.id == "quit":
            self.action_quit()
        # views
        elif event.button.id == "show-history-list":
            self.current_view = "history-list"
            self.update_view_visibility()
        elif event.button.id == "show-history-chart":
            self.current_view = "history-chart"
            self.update_view_visibility()
        elif event.button.id == "show-session":
            self.current_view = "session-info"
            self.update_view_visibility()
        # playback
        elif event.button.id == "play-pause":
            self.playback_control(PlaybackAction.PAUSE)
        elif event.button.id == "previous-track":
            self.playback_control(PlaybackAction.PREVIOUS)
        elif event.button.id == "next-track":
            self.playback_control(PlaybackAction.NEXT)

    @work
    async def playback_control(self, action: PlaybackAction):
        if self.active_integration == Integration.APPLE_MUSIC:
            await playback_control(action)
        elif self.active_integration == Integration.SPOTIFY:
            result = await self.spotify.playback_control(action)
            if result is False:
                self.notify("Failed to control playback. Spotify Premium required.")

    @staticmethod
    def format_song_info(song, status=""):
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

    @work
    async def update_display(self):
        poll_service = poll_apple_music if self.active_integration == Integration.APPLE_MUSIC else self.spotify.poll_spotify
        poll: Track = await poll_service()
        compare: Comparison = await poll_comparison(poll, self.current_song)

        if compare.no_song_playing:
            if self.current_song:
                self.current_song = None
            self.update_song_info(ScrobbleStatus.NOT_PLAYING)
            self.query_one(widgets.HistoryListWidget).update(ScrobbleStatus.NOT_PLAYING)
            self.update_progress_bar(0, ScrobbleStatus.NOT_PLAYING)
            return

        if compare.update_song:
            self.current_song = poll
            self.current_song.time_played = 0
            scrobbles = await self.lastfm.current_track_user_scrobbles(self.current_song)
            self.query_one(widgets.HistoryListWidget).update_list(self.current_song, scrobbles)
            self.query_one(widgets.HistoryChartWidget).update_chart(self.current_song, scrobbles)
            if compare.update_lastfm_now_playing:
                self.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.current_song)

        if compare.update_song_playing_status:
            self.current_song.playing = poll.playing

        threshold = self.current_song.get_scrobbled_threshold()
        progress_value = min(1.0, self.current_song.time_played / threshold)
        progress_text = f"{self.current_song.time_played}s / {threshold}s"

        if self.current_song.playing is False:
            self.update_song_info(self.format_song_info(self.current_song, ScrobbleStatus.PAUSED))
            self.update_progress_bar(progress_value, f"{progress_text} ({ScrobbleStatus.PAUSED})")
        elif self.current_song.scrobbled:
            self.update_song_info(self.format_song_info(self.current_song, ScrobbleStatus.SCROBBLED))
            self.update_progress_bar(1.0, f"{progress_text} (Scrobbled)")
        else:
            self.current_song.time_played += 1
            self.update_song_info(self.format_song_info(self.current_song))
            self.update_progress_bar(progress_value, progress_text)

            if self.current_song.is_ready_to_be_scrobbled() and not self.is_scrobbling:
                self.is_scrobbling = True
                scrobbled_track = await self.lastfm.scrobble(self.current_song)
                if scrobbled_track:
                    self.session.add_scrobble(scrobbled_track)
                    self.session.remove_pending(self.current_song)
                    self.current_song.scrobbled = True
                    self.update_song_info(self.format_song_info(self.current_song, ScrobbleStatus.SCROBBLED))
                    self.update_progress_bar(1.0, f"{progress_text} (Scrobbled)")
                    self.update_session_info()
                else:
                    self.session.add_pending(self.current_song)
                    self.update_song_info(self.format_song_info(self.current_song, ScrobbleStatus.PENDING))
                self.is_scrobbling = False


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
