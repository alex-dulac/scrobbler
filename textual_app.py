import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.visual import VisualType
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
        self.current_view = widgets.TuiViews.TRACK_HISTORY
        self.db_connected: bool = False
        self.years: range | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield widgets.playback_controls
        yield widgets.view_controls
        yield widgets.SongInfoWidget(id="song-info")
        yield widgets.ScrobbleProgressBar()
        yield widgets.TrackHistoryWidget()
        yield widgets.ArtistStatsWidget()
        yield widgets.SessionInfoWidget(self.state.session)
        yield widgets.ManualScrobbleWidget()
        yield Footer()

    def get_track_history(self) -> widgets.TrackHistoryWidget:
        return self.query_one(widgets.TrackHistoryWidget)

    def get_artist_stats(self) -> widgets.ArtistStatsWidget:
        return self.query_one(widgets.ArtistStatsWidget)

    def get_session_info(self) -> widgets.SessionInfoWidget:
        return self.query_one(widgets.SessionInfoWidget)

    def get_manual_scrobble(self) -> widgets.ManualScrobbleWidget:
        return self.query_one(widgets.ManualScrobbleWidget)

    def update_progress_bar(self) -> None:
        value = 0.0 if not self.state.current_song else self.state.current_song.scrobble_progress_value
        text = self.WAITING if not self.state.current_song else self.state.current_song.scrobble_progress_text
        self.query_one(widgets.ScrobbleProgressBar).update_progress(value, text)

    def update_song_info(self, info: VisualType) -> None:
        self.query_one(widgets.SongInfoWidget).update(info)

    async def on_mount(self) -> None:
        try:
            await session_manager.init_db()
            self.db_connected = True
            self.get_artist_stats().db_connected = True
            self.get_manual_scrobble().db_connected = True
            self.notify("Database connected successfully.")
        except Exception as e:
            self.notify("Database connection failed. Some features might not work as expected.", severity="warning")

        self.lastfm = await get_lastfm_service()
        self.spotify = await get_spotify_service()

        self.update_song_info(self.WAITING)
        self.get_artist_stats().update(self.WAITING)
        self.years = range(self.state.user.registered.year, datetime.today().year + 1)
        self.get_manual_scrobble().lastfm = self.lastfm

        self.set_interval(1, self.update_display) # primary app functionality
        self.update_progress_bar()
        self.update_view()

    def update_view(self) -> None:
        history_chart = self.get_track_history()
        artist_stats = self.get_artist_stats()
        session = self.get_session_info()
        manual_scrobble = self.get_manual_scrobble()

        views = [history_chart, artist_stats, session, manual_scrobble]
        for view in views:
            view.display = False

        match self.current_view:
            case widgets.TuiViews.TRACK_HISTORY:
                history_chart.display = True
            case widgets.TuiViews.ARTIST_STATS:
                artist_stats.display = True
            case widgets.TuiViews.SESSION:
                session.display = True
            case widgets.TuiViews.MANUAL_SCROBBLE:
                manual_scrobble.display = True

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        active_css = "active-button"

        def get_spotify_button():
            return self.query_one(f"#{widgets.TuiIds.SPOTIFY.value}")

        def get_apple_music_button():
            return self.query_one(f"#{widgets.TuiIds.APPLE_MUSIC.value}")

        def check_db():
            if not self.db_connected:
                self.notify("Database not connected. Widget unavailable.", severity="warning")
                return False
            return True

        def handle_view_change(target_view: widgets.TuiViews):
            self.current_view = target_view
            self.update_view()

        match event.button.id:
            case widgets.TuiIds.APPLE_MUSIC:
                self.state.active_integration = Integration.APPLE_MUSIC
                self.poll_service = poll_apple_music
                get_apple_music_button().add_class(active_css)
                get_spotify_button().remove_class(active_css)
            case widgets.TuiIds.SPOTIFY:
                self.state.active_integration = Integration.SPOTIFY
                self.poll_service = self.spotify.poll_spotify
                get_spotify_button().add_class(active_css)
                get_apple_music_button().remove_class(active_css)
            case widgets.TuiIds.QUIT:
                self.action_quit()
            case widgets.TuiIds.SHOW_TRACK_HISTORY:
                handle_view_change(widgets.TuiViews.TRACK_HISTORY)
            case widgets.TuiIds.SHOW_ARTIST_STATS:
                if not check_db():
                    return
                handle_view_change(widgets.TuiViews.ARTIST_STATS)
            case widgets.TuiIds.SHOW_SESSION:
                handle_view_change(widgets.TuiViews.SESSION)
            case widgets.TuiIds.SHOW_MANUAL_SCROBBLE:
                if not check_db():
                    return
                handle_view_change(widgets.TuiViews.MANUAL_SCROBBLE)
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

    async def handle_scrobble(self):
        if self.state.is_scrobbling:
            return

        self.state.is_scrobbling = True
        scrobbled_track = await self.lastfm.scrobble(self.state.current_song)
        if scrobbled_track:
            self.state.session.add_scrobble(scrobbled_track)
            self.state.session.remove_pending(self.state.current_song)
            self.state.current_song.scrobbled = True
            self.get_session_info().update_session_info()
            if self.db_connected:
                repo = ScrobbleRepository()
                await repo.add_scrobble(scrobbled_track)
                self.notify(f"Scrobbled and added to database: {scrobbled_track.display_name}")
        else:
            self.state.session.add_pending(self.state.current_song)
            self.state.current_song.format_textual_song_info()
            self.update_song_info(self.state.current_song.format_textual_song_info(is_pending=True))
        self.state.is_scrobbling = False

    @work
    async def update_display(self) -> None:
        poll: Track = await self.poll_service()
        compare = Comparison(poll=poll, current_song=self.state.current_song)

        if compare.no_song_playing:
            status = self.WAITING
            self.state.current_song = None
            self.update_song_info(status)
            self.get_track_history().update(status)
            self.get_artist_stats().update(status)
            self.update_progress_bar()
            return

        if compare.song_has_changed:
            self.state.current_song = poll
            self.state.current_song.time_played = 0
            await self.get_track_history().update_chart(self.state.current_song, self.years)
            await self.get_artist_stats().update_artist_stats(self.state.current_song, self.years)
            if compare.update_lastfm_now_playing:
                self.state.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.state.current_song)

        if compare.update_song_playing_status:
            self.state.current_song.playing = poll.playing

        if self.state.current_song.playing and not self.state.current_song.scrobbled:
            self.state.current_song.time_played += 1
            if self.state.current_song.is_ready_to_be_scrobbled:
                await self.handle_scrobble()

        self.update_song_info(self.state.current_song.format_textual_song_info())
        self.update_progress_bar()


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
