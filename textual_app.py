import asyncio

from textual.app import App, ComposeResult
from textual.visual import VisualType
from textual.widgets import Header, Footer, Button
from textual import work
from rich.text import Text

from core.database import session_manager, get_async_session
from library.comparison import Comparison
from library.integrations import Integration, PlaybackAction
from library.state import AppState
from models.db import Scrobble
from models.schemas import Track
from repositories.repository import ScrobbleRepository
from services.apple_music_service import poll_apple_music, playback_control
from services.spotify_service import SpotifyService, get_spotify_service
from services.lastfm_service import LastFmService, get_lastfm_service
import library.textual_widgets as widgets


WAITING  = "Waiting for music..."


def format_song_info(song: Track, status="") -> Text:
    text = Text()
    text.append(f"{song.clean_name}\n", style="bold white")
    text.append(f"by ", style="dim")
    text.append(f"{song.artist}", style="italic cyan")
    if song.album:
        text.append(f" • ", style="dim")
        text.append(f"{song.clean_album}", style="italic green")
    if status:
        text.append(f"\n{status}", style="yellow" if "Scrobbled" in status else "blue")
    return text


class ScrobblerApp(App):
    CSS = widgets.css

    def __init__(self):
        super().__init__()
        self.state: AppState = AppState()
        self.lastfm: LastFmService | None = None
        self.spotify: SpotifyService | None = None
        self.poll_service = poll_apple_music
        self.current_view = widgets.TuiViews.TRACK_HISTORY
        self.db_connected: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield widgets.playback_controls
        yield widgets.view_controls
        yield widgets.SongInfoWidget(id="song-info")
        yield widgets.ScrobbleProgressBar()
        yield widgets.TrackHistoryWidget()
        yield widgets.ArtistStatsWidget()
        yield widgets.SessionInfoWidget(self.state.session)
        yield widgets.ManualScrobbleWidget(lastfm=self.lastfm)
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
        text = WAITING if not self.state.current_song else self.state.current_song.scrobble_progress_text
        self.query_one(widgets.ScrobbleProgressBar).update_progress(value, text)

    def update_song_info(self, info: VisualType) -> None:
        self.query_one(widgets.SongInfoWidget).update(info)

    async def on_mount(self) -> None:
        self.lastfm = await get_lastfm_service()
        self.spotify = await get_spotify_service()

        try:
            await session_manager.init_db()
            self.db_connected = True
            self.get_artist_stats().db_connected = True
            self.notify("Database connected successfully.")
        except Exception as e:
            self.notify("Database connection failed. Some features might not work as expected.", severity="warning")

        self.get_track_history().set_years(self.state.user.registered.year)
        self.set_interval(1, self.update_display)
        self.update_song_info(WAITING)
        self.update_progress_bar()
        self.get_artist_stats().update(WAITING)
        self.update_view_visibility()

    def update_view_visibility(self) -> None:
        history_chart = self.get_track_history()
        artist_stats = self.get_artist_stats()
        session = self.get_session_info()
        album_form = self.get_album_form()
        views = [history_chart, artist_stats, session, album_form]
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
                album_form.display = True

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
        def get_spotify_button():
            return self.query_one(f"#{widgets.TuiIds.SPOTIFY}")
        def get_apple_music_button():
            return self.query_one(f"#{widgets.TuiIds.APPLE_MUSIC}")
        active_css = "active-button"

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
                self.current_view = widgets.TuiViews.TRACK_HISTORY
                self.update_view_visibility()
            case widgets.TuiIds.SHOW_ARTIST_STATS:
                if not self.db_connected:
                    self.notify("Database not connected. Artist stats unavailable.", severity="warning")
                    return
                self.current_view = widgets.TuiViews.ARTIST_STATS
                self.update_view_visibility()
            case widgets.TuiIds.SHOW_SESSION:
                self.current_view = widgets.TuiViews.SESSION
                self.update_view_visibility()
            case widgets.TuiIds.SHOW_MANUAL_SCROBBLE:
                if not self.db_connected:
                    self.notify("Database not connected. Manual scrobble unavailable.", severity="warning")
                    return
                self.current_view = widgets.TuiViews.MANUAL_SCROBBLE
                self.update_view_visibility()
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
        self.state.is_scrobbling = True
        scrobbled_track = await self.lastfm.scrobble(self.state.current_song)
        if scrobbled_track:
            self.state.session.add_scrobble(scrobbled_track)
            self.state.session.remove_pending(self.state.current_song)
            self.state.current_song.scrobbled = True
            self.get_session_info().update_session_info()
            if self.db_connected:
                scrobble = Scrobble(
                    artist_name=scrobbled_track.artist,
                    album_name=scrobbled_track.album,
                    track_name=scrobbled_track.name,
                    scrobbled_at=scrobbled_track.scrobbled_at
                )
                repo = ScrobbleRepository(db=await get_async_session())
                await repo.add_and_commit([scrobble])
        else:
            self.state.session.add_pending(self.state.current_song)
            self.update_song_info(format_song_info(self.state.current_song, "⏱ Pending scrobble (no internet)"))
        self.state.is_scrobbling = False

    @work
    async def update_display(self) -> None:
        poll: Track = await self.poll_service()
        compare = Comparison(poll=poll, current_song=self.state.current_song)

        if compare.no_song_playing:
            self.state.current_song = None
            self.update_song_info(WAITING)
            self.get_track_history().update(WAITING)
            self.get_artist_stats().update(WAITING)
            self.update_progress_bar()
            return

        if compare.song_has_changed:
            self.state.current_song = poll
            self.state.current_song.time_played = 0
            scrobbles = await self.lastfm.current_track_user_scrobbles(self.state.current_song)
            self.get_track_history().update_chart(self.state.current_song, scrobbles)
            await self.get_artist_stats().update_artist_stats(self.state.current_song)
            if compare.update_lastfm_now_playing:
                self.state.current_song.lastfm_updated_now_playing = await self.lastfm.update_now_playing(self.state.current_song)
            return

        if compare.update_song_playing_status:
            self.state.current_song.playing = poll.playing

        if self.state.current_song.scrobbled:
            self.update_song_info(format_song_info(self.state.current_song, "✓ Scrobbled to Last.fm"))
            self.update_progress_bar()
        elif not self.state.current_song.playing:
            self.update_song_info(format_song_info(self.state.current_song, "Paused"))
            self.update_progress_bar()
        else:
            self.state.current_song.time_played += 1
            self.update_song_info(format_song_info(self.state.current_song))
            self.update_progress_bar()
            if self.state.current_song.is_ready_to_be_scrobbled and not self.state.is_scrobbling:
                await self.handle_scrobble()


if __name__ == "__main__":
    app = ScrobblerApp()
    app.run()
