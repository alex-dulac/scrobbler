import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button
from textual import work

from core.database import session_manager
from library.comparison import Comparison
from library.dependencies import get_lastfm_service, get_spotify_service
from library.integrations import Integration, PlaybackAction
from library.state import AppState
from models.schemas import Track
from repositories.scrobble_repo import ScrobbleRepository
from services.apple_music_service import poll_apple_music, playback_control
from services.spotify_service import SpotifyService
from services.lastfm_service import LastFmService
import library.textual_widgets as widgets


class ScrobblerApp(App):
    CSS = widgets.css
    WAITING = "Waiting for music..."

    def __init__(self):
        super().__init__()
        self.state: AppState = AppState()
        self.lastfm: LastFmService | None = None
        self.spotify: SpotifyService | None = None
        self.poll_service = poll_apple_music
        self.current_view = widgets.TuiViews.LASTFM_USER
        self.db_connected: bool = False
        self.years: range | None = None
        self.now_playing = widgets.NowPlayingWidget()
        self.progress_bar = widgets.ScrobbleProgressBar()
        self.track_history = widgets.TrackHistoryWidget()
        self.artist_stats = widgets.ArtistStatsWidget()
        self.session_info = widgets.SessionInfoWidget(self.state.session)
        self.manual_scrobble = widgets.ManualScrobbleWidget()
        self.lastfm_user = widgets.LastFmUserWidget()
        self.wrapped = widgets.WrappedWidget()

    def compose(self) -> ComposeResult:
        yield Header()
        yield widgets.playback_controls
        yield widgets.view_controls
        yield self.now_playing
        yield self.progress_bar
        yield self.track_history
        yield self.artist_stats
        yield self.session_info
        yield self.manual_scrobble
        yield self.lastfm_user
        yield self.wrapped
        yield Footer()

    def update_progress_bar(self) -> None:
        value = 0.0 if not self.state.current_song else self.state.current_song.scrobble_progress_value
        text = self.WAITING if not self.state.current_song else self.state.current_song.scrobble_progress_text
        self.progress_bar.update_progress(value, text)

    async def on_mount(self) -> None:
        # init db
        try:
            await session_manager.init_db()
            self.db_connected = True
            self.track_history.db_connected = True
            self.artist_stats.db_connected = True
            self.manual_scrobble.db_connected = True
            self.wrapped.db_connected = True
            self.notify("Database connected successfully.")
        except Exception as e:
            self.notify("Database connection failed. Some features might not work as expected.", severity="warning")

        # init services
        self.lastfm = await get_lastfm_service()
        self.spotify = await get_spotify_service()

        # widgets etc.
        self.now_playing.update(self.WAITING)
        self.artist_stats.update(self.WAITING)
        self.years = range(self.state.user.registered.year, datetime.today().year + 1)
        self.wrapped.years = self.years
        self.manual_scrobble.lastfm_service = self.lastfm
        self.lastfm_user.lastfm_service = self.lastfm
        self.lastfm_user.refresh_data()
        self.update_progress_bar()
        self.update_view()
        self.set_interval(1, self.update_display) # primary app functionality

    def update_view(self) -> None:
        views = [
            self.track_history,
            self.artist_stats,
            self.session_info,
            self.manual_scrobble,
            self.lastfm_user,
            self.wrapped
        ]

        for view in views:
            view.display = False

        view_buttons = self.query("#view-controls Button")
        for button in view_buttons:
            button.remove_class("active-view")

        for button_id, config in widgets.view_configs.items():
            if config.view == self.current_view:
                self.query_one(f"#{button_id.value}").add_class("active-view")
                break

        match self.current_view:
            case widgets.TuiViews.TRACK_HISTORY:
                self.track_history.display = True
            case widgets.TuiViews.ARTIST_STATS:
                self.artist_stats.display = True
            case widgets.TuiViews.SESSION:
                self.session_info.display = True
            case widgets.TuiViews.MANUAL_SCROBBLE:
                self.manual_scrobble.display = True
            case widgets.TuiViews.LASTFM_USER:
                self.lastfm_user.display = True
            case widgets.TuiViews.WRAPPED:
                self.wrapped.get_wrapped_by_year(2025)
                self.wrapped.display = True

    @work
    async def action_quit(self) -> None:
        """Quit the application after processing any pending scrobbles."""
        self.notify("Thank you for scrobbling. Goodbye!")

        if self.state.session.pending:
            count = await self.state.session.process_pending_scrobbles(self.lastfm)
            self.notify(f"Processed {count} pending scrobbles.")

        if self.db_connected:
            await session_manager.close_db()

        await asyncio.sleep(1)
        self.exit()

    def handle_view_change(self, button_id: str) -> bool:
        config = widgets.view_configs.get(button_id)
        if not config:
            return False

        if config.requires_db and not self.db_connected:
            self.notify("This view requires a database connection.", severity="warning")
            return False

        self.current_view = config.view
        self.update_view()
        return True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        active_button_css = "active-button"

        def get_spotify_button():
            return self.query_one(f"#{widgets.TuiIds.SPOTIFY.value}")

        def get_apple_music_button():
            return self.query_one(f"#{widgets.TuiIds.APPLE_MUSIC.value}")

        button_id = event.button.id

        if button_id in widgets.view_configs:
            self.handle_view_change(button_id)
            return

        match button_id:
            case widgets.TuiIds.APPLE_MUSIC:
                self.state.active_integration = Integration.APPLE_MUSIC
                self.poll_service = poll_apple_music
                get_apple_music_button().add_class(active_button_css)
                get_spotify_button().remove_class(active_button_css)
            case widgets.TuiIds.SPOTIFY:
                self.state.active_integration = Integration.SPOTIFY
                self.poll_service = self.spotify.poll_spotify
                get_spotify_button().add_class(active_button_css)
                get_apple_music_button().remove_class(active_button_css)
            case widgets.TuiIds.QUIT:
                self.action_quit()
            case widgets.TuiIds.PLAY_PAUSE:
                self.playback_control(PlaybackAction.PAUSE)
            case widgets.TuiIds.NEXT_TRACK:
                self.playback_control(PlaybackAction.NEXT)
            case widgets.TuiIds.PREVIOUS_TRACK:
                self.playback_control(PlaybackAction.PREVIOUS)

    @work
    async def playback_control(self, action: PlaybackAction) -> None:
        if self.state.active_integration == Integration.APPLE_MUSIC:
            await playback_control(action)
        elif self.state.active_integration == Integration.SPOTIFY:
            result = await self.spotify.playback_control(action)
            if result is False:
                self.notify("Failed to control playback. Spotify Premium required.")

    @work
    async def handle_scrobble(self):
        if self.state.is_scrobbling:
            return

        self.state.is_scrobbling = True
        scrobbled_track = await self.lastfm.scrobble(self.state.current_song)
        if scrobbled_track:
            self.state.session.add_scrobble(scrobbled_track)
            self.state.session.remove_pending(self.state.current_song)
            self.state.current_song.scrobbled = True
            self.session_info.update_session_info()
            if self.db_connected:
                repo = ScrobbleRepository()
                await repo.add_scrobble(scrobbled_track)
                self.notify(f"Scrobbled and added to database: {scrobbled_track.display_name}")
            await asyncio.sleep(0.5) # brief pause to ensure getting the recent scrobbles from last.fm includes this one
            self.lastfm_user.refresh_data()
        else:
            self.state.session.add_pending(self.state.current_song)
            self.state.current_song.format_textual_song_info()
            self.now_playing.update(self.state.current_song.format_textual_song_info(is_pending=True))
        self.state.is_scrobbling = False

    @work
    async def update_display(self) -> None:
        poll: Track = await self.poll_service()
        compare = Comparison(poll=poll, current_song=self.state.current_song)

        if compare.no_song_playing:
            status = self.WAITING
            self.state.current_song = None
            self.now_playing.update(status)
            self.track_history.update(status)
            self.artist_stats.update(status)
            self.update_progress_bar()
            return

        if compare.song_has_changed:
            self.state.current_song = poll
            self.state.current_song.time_played = 0
            self.track_history.update_chart(self.state.current_song, self.years)
            self.artist_stats.update_artist_stats(self.state.current_song, self.years)
            if compare.update_lastfm_now_playing:
                self.state.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.state.current_song)

        if compare.update_song_playing_status:
            self.state.current_song.playing = poll.playing

        if self.state.current_song.playing and not self.state.current_song.scrobbled:
            self.state.current_song.time_played += 1
            if self.state.current_song.is_ready_to_be_scrobbled:
                self.handle_scrobble()

        self.now_playing.update(self.state.current_song.format_textual_song_info())
        self.update_progress_bar()


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
