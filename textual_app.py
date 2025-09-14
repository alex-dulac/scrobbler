import asyncio

from textual.app import App, ComposeResult
from textual.visual import VisualType
from textual.widgets import Header, Footer, Button
from textual import work
from rich.text import Text

from core.database import session_manager
from library.comparison import Comparison
from library.integrations import Integration, PlaybackAction
from library.state import AppState
from models.schemas import Track
from services.apple_music_service import poll_apple_music, playback_control
from services.spotify_service import SpotifyService
from services.lastfm_service import LastFmService
import library.textual_widgets as widgets


SCROBBLED = "✓ Scrobbled to Last.fm"
PAUSED = "Paused"
PENDING = "⏱ Pending scrobble (no internet)"
WAITING  = "Waiting for music..."
NOT_PLAYING = "No song playing"


def format_song_info(song: Track, status="") -> Text:
    text = Text()
    text.append(f"{song.clean_name}\n", style="bold white")
    text.append(f"by ", style="dim")
    text.append(f"{song.artist}", style="italic cyan")
    if song.album:
        text.append(f" • ", style="dim")
        text.append(f"{song.album}", style="italic green")
    if status:
        text.append(f"\n{status}", style="yellow" if "Scrobbled" in status else "blue")
    return text


class ScrobblerApp(App):
    CSS = widgets.css

    def __init__(self):
        super().__init__()
        self.state: AppState = AppState()
        self.lastfm: LastFmService = LastFmService()
        self.spotify: SpotifyService = SpotifyService()
        self.poll_service = poll_apple_music
        self.current_view = widgets.TuiViews.HISTORY_CHART
        self.db_connected: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield widgets.playback_controls
        yield widgets.view_controls
        yield widgets.SongInfoWidget(id="song-info")
        yield widgets.ScrobbleProgressBar(id="scrobble-progress")
        yield widgets.HistoryListWidget(id=widgets.TuiViews.HISTORY_LIST)
        yield widgets.HistoryChartWidget(id=widgets.TuiViews.HISTORY_CHART)
        yield widgets.SessionInfoWidget(self.state.session, id=widgets.TuiViews.SESSION)
        yield Footer()

    def get_history_list(self) -> widgets.HistoryListWidget:
        return self.query_one(widgets.HistoryListWidget)

    def get_history_chart(self) -> widgets.HistoryChartWidget:
        return self.query_one(widgets.HistoryChartWidget)

    def get_session_info(self) -> widgets.SessionInfoWidget:
        return self.query_one(widgets.SessionInfoWidget)

    def update_progress_bar(self, progress_value: float, progress_text: str) -> None:
        self.query_one(widgets.ScrobbleProgressBar).update_progress(progress_value, progress_text)

    def update_song_info(self, info: VisualType) -> None:
        self.query_one(widgets.SongInfoWidget).update(info)

    async def on_mount(self) -> None:
        try:
            await session_manager.init_db()
            self.db_connected = True
            self.notify("Database connected successfully.")
        except Exception as e:
            self.notify("Database connection failed. Some features might not work as expected.", severity="warning")

        self.get_history_chart().set_years(self.state.user.registered.year)
        self.set_interval(1, self.update_display)
        self.update_song_info(WAITING)
        self.update_progress_bar(0, WAITING)
        self.get_history_list().update(WAITING)
        self.update_view_visibility()

    def update_view_visibility(self) -> None:
        history_list = self.get_history_list()
        history_chart = self.get_history_chart()
        session = self.get_session_info()

        match self.current_view:
            case widgets.TuiViews.HISTORY_LIST:
                history_list.display = True
                history_chart.display = False
                session.display = False
            case widgets.TuiViews.HISTORY_CHART:
                history_list.display = False
                history_chart.display = True
                session.display = False
            case widgets.TuiViews.SESSION:
                history_list.display = False
                history_chart.display = False
                session.display = True

    @work
    async def action_quit(self) -> None:
        """Quit the application after processing any pending scrobbles."""
        self.notify("Thank you for scrobbling. Goodbye!")

        if self.state.session.pending:
            count = await self.state.session.process_pending_scrobbles()
            self.notify(f"Processed {count} pending scrobbles.")

        if self.db_connected:
            await session_manager.close_db()

        await asyncio.sleep(1)
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # main
        if event.button.id == "apple-music":
            self.state.active_integration = Integration.APPLE_MUSIC
            self.poll_service = poll_apple_music
            self.query_one("#apple-music").add_class("active-button")
            self.query_one("#spotify").remove_class("active-button")
        elif event.button.id == "spotify":
            self.state.active_integration = Integration.SPOTIFY
            self.poll_service = self.spotify.poll_spotify
            self.query_one("#spotify").add_class("active-button")
            self.query_one("#apple-music").remove_class("active-button")
        elif event.button.id == "quit":
            self.action_quit()
        # views
        elif event.button.id == "show-history-list":
            self.current_view = widgets.TuiViews.HISTORY_LIST
            self.update_view_visibility()
        elif event.button.id == "show-history-chart":
            self.current_view = widgets.TuiViews.HISTORY_CHART
            self.update_view_visibility()
        elif event.button.id == "show-session":
            self.current_view = widgets.TuiViews.SESSION
            self.update_view_visibility()
        # playback
        elif event.button.id == "play-pause":
            self.playback_control(PlaybackAction.PAUSE)
        elif event.button.id == "previous-track":
            self.playback_control(PlaybackAction.PREVIOUS)
        elif event.button.id == "next-track":
            self.playback_control(PlaybackAction.NEXT)

    @work
    async def playback_control(self, action: PlaybackAction) -> None:
        if self.state.active_integration == Integration.APPLE_MUSIC:
            await playback_control(action)
        elif self.state.active_integration == Integration.SPOTIFY:
            result = await self.spotify.playback_control(action)
            if result is False:
                self.notify("Failed to control playback. Spotify Premium required.")

    @work
    async def update_display(self) -> None:
        poll: Track = await self.poll_service()
        compare = Comparison(poll=poll, current_song=self.state.current_song)

        if compare.no_song_playing:
            self.state.current_song = None
            self.update_song_info(NOT_PLAYING)
            self.get_history_list().update(NOT_PLAYING)
            self.update_progress_bar(0, NOT_PLAYING)
            return

        if compare.song_has_changed:
            self.state.current_song = poll
            self.state.current_song.time_played = 0
            scrobbles = await self.lastfm.current_track_user_scrobbles(self.state.current_song)
            self.get_history_list().update_list(self.state.current_song, scrobbles)
            self.get_history_chart().update_chart(self.state.current_song, scrobbles)
            if compare.update_lastfm_now_playing:
                self.state.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.state.current_song)

        if compare.update_song_playing_status:
            self.state.current_song.playing = poll.playing

        threshold = self.state.current_song.scrobble_threshold
        progress_value = min(1.0, self.state.current_song.time_played / threshold)
        progress_text = f"{self.state.current_song.time_played}s / {threshold}s"

        if not self.state.current_song.playing:
            self.update_song_info(format_song_info(self.state.current_song, PAUSED))
            self.update_progress_bar(progress_value, f"{progress_text} ({PAUSED})")
        elif self.state.current_song.scrobbled:
            self.update_song_info(format_song_info(self.state.current_song, SCROBBLED))
            self.update_progress_bar(1.0, f"{progress_text} (Scrobbled)")
        else:
            self.state.current_song.time_played += 1
            self.update_song_info(format_song_info(self.state.current_song))
            self.update_progress_bar(progress_value, progress_text)
            if self.state.current_song.is_ready_to_be_scrobbled and not self.state.is_scrobbling:
                self.state.is_scrobbling = True
                scrobbled_track = await self.lastfm.scrobble(self.state.current_song)
                if scrobbled_track:
                    self.state.session.add_scrobble(scrobbled_track)
                    self.state.session.remove_pending(self.state.current_song)
                    self.state.current_song.scrobbled = True
                    self.get_session_info().update_session_info()
                else:
                    self.state.session.add_pending(self.state.current_song)
                    self.update_song_info(format_song_info(self.state.current_song, PENDING))
                self.state.is_scrobbling = False


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
