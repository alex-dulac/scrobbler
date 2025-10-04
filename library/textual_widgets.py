from collections import defaultdict
from datetime import datetime
from enum import Enum

from rich.console import RenderableType, Group
from rich.progress import Progress, TextColumn, BarColumn
from rich.table import Table
from textual.containers import Container
from textual.widgets import Static, Button, Input

from core import config
from core.database import get_async_session
from library.session_scrobbles import SessionScrobbles
from models.schemas import Track, LastFmTrack
from repositories.repository import ScrobbleRepository
from services.lastfm_service import LastFmService

css = """
    Button {
        margin: 0 1;
    }
    #song-info {
        height: 3;
        content-align: center middle;
        margin: 1 0;
    }
    #scrobble-progress {
        height: 1;
        margin: 2 2;
        width: 100%;
        content-align: center middle;
    }
    .controls {
        layout: horizontal;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    .content-container {
        padding: 1 2;
        width: 100%;
    }
    .active-button {
        background: $accent;
    }
    """


class TuiViews(str, Enum):
    TRACK_HISTORY = "track-history"
    ARTIST_STATS = "artist-stats"
    SESSION = "session-info"
    MANUAL_SCROBBLE = "manual-scrobble"


playback_controls = Container(
    Button("Apple Music", id="apple-music", classes="active-button"),
    Button("Spotify", id="spotify"),
    Button("⏯ Play/Pause", id="play-pause"),
    Button("⏮ Back", id="previous-track"),
    Button("⏭ Skip", id="next-track"),
    Button("Quit", id="quit", variant="error"),
    classes="controls",
    id="controls"
)


view_controls = Container(
    Button("Track History", id="show-track-history"),
    Button("Artist Stats", id="show-artist-stats"),
    Button("Session", id="show-session"),
    Button("Manual Scrobble", id="show-manual-scrobble"),
    classes="controls",
    id="view-controls"
)


class SongInfoWidget(Static):
    def render(self) -> RenderableType:
        return self.renderable


class ScrobbleProgressBar(Static):
    def __init__(self):
        super().__init__(id="scrobble-progress")
        self.progress = 0.0
        self.progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", justify="right"),
            BarColumn(bar_width=None),
            TextColumn("{task.description}", justify="left"),
            expand=True
        )
        self.task_id = self.progress_bar.add_task("", total=100, completed=0)

    def update_progress(self, value, description=""):
        percentage = min(100, max(0, int(value * 100)))
        self.progress = value
        self.progress_bar.update(self.task_id, completed=percentage, description=description)
        self.update(self.progress_bar)


class TrackHistoryWidget(Static):
    def __init__(self):
        super().__init__(id=TuiViews.TRACK_HISTORY, classes="content-container")
        self.start_year: int = datetime.today().year
        self.current_year: int = datetime.today().year
        self.all_years = range(self.start_year, self.current_year + 1)

    def set_years(self, start_year: int):
        self.start_year = start_year
        self.all_years = range(self.start_year, self.current_year + 1)

    def update_chart(self, current_song: Track, scrobbles: list[LastFmTrack]) -> None:
        if not current_song:
            self.update("No song selected")
            return

        if not scrobbles:
            self.update(f"No previous scrobbles found for: {current_song.display_name}")
            return

        year_counts = defaultdict(int)
        for scrobble in scrobbles:
            year_counts[scrobble.scrobbled_at.year] += 1

        chart_table = Table(title=f"Scrobbles by Year: {current_song.display_name}", expand=True)
        chart_table.add_column("Year", style="cyan", width=8)
        chart_table.add_column("Count", style="white", width=8)
        chart_table.add_column("Chart", style="green")

        # get max count for bar scaling
        max_count = max(year_counts.values()) if year_counts else 1

        for year in self.all_years:
            count = year_counts.get(year, 0)
            if count > 0:
                bar_width = int((count / max_count) * 50)
                bar = "█" * bar_width
                chart_display = f"{bar} ({count})"
            else:
                chart_display = f"({count})"

            chart_table.add_row(str(year), str(count), chart_display)

        chart_table.add_section()
        total_scrobbles = sum(year_counts.values())
        avg_per_year = total_scrobbles / len(self.all_years)

        summary_table = Table(title="Additional Stats", width=60)
        summary_table.add_column("Metric", style="dim")
        summary_table.add_column("Value", style="bold white")

        summary_table.add_row("Total Scrobbles", str(total_scrobbles))
        summary_table.add_row("Years With Scrobbles", str(len(year_counts)))
        summary_table.add_row("Average per Year", f"{avg_per_year:.1f}")
        summary_table.add_row("Peak Year", f"{max(year_counts, key=year_counts.get)} ({max(year_counts.values())} scrobbles)")

        history_table = Table(title=f"Scrobble History for: {current_song.display_name}", expand=True)
        history_table.add_column("#", style="dim", width=4)
        history_table.add_column("Timestamp", style="cyan")

        for i, scrobble in enumerate(scrobbles):
            timestamp = scrobble.scrobbled_at.strftime(config.DATETIME_FORMAT)
            history_table.add_row(
                str(i + 1),
                timestamp
            )

        history_table.add_section()
        history_table.add_row(
            "Total",
            f"{len(scrobbles)} scrobbles"
        )

        combined_display = Group(chart_table, "", summary_table, "", history_table)
        self.update(combined_display)


class ArtistStatsWidget(Static):
    def __init__(self, db_connected: bool = False):
        super().__init__(id=TuiViews.ARTIST_STATS, classes="content-container")
        self.db_connected = db_connected
        if not self.db_connected:
            self.update("Database not connected")
        else:
            self.update("No song selected")

    async def update_artist_stats(self, artist_name: Track) -> None:
        if not self.db_connected:
            self.update("Database not connected")
            return

        if not artist_name:
            self.update("No song selected")
            return

        db = await get_async_session()
        repo = ScrobbleRepository(db=db)

        top_played_tracks = await repo.get_top_tracks_by_artist(artist_name.artist, limit=30)

        if not top_played_tracks:
            self.update(f"No scrobbles found for artist: {artist_name.artist}")
            return

        tracks = Table(title=f"Top Played Tracks for: {artist_name.artist}", expand=True)
        tracks.add_column("#", style="dim", width=4)
        tracks.add_column("Track", style="white", width=40)
        tracks.add_column("Album", style="white", width=40)
        tracks.add_column("Play Count", style="cyan", width=12)

        album_styles = {}
        available_styles = [
            "bold magenta", "bold green", "bold blue", "bold yellow", "bold cyan",
            "bold red", "magenta", "green", "blue", "yellow", "cyan", "red"
        ]

        for i, (track_name, album_name, play_count) in enumerate(top_played_tracks):
            if album_name not in album_styles:
                album_styles[album_name] = available_styles[len(album_styles) % len(available_styles)]
            row_style = album_styles[album_name]
            tracks.add_row(str(i + 1), track_name, album_name, str(play_count), style=row_style)

        top_played_albums = await repo.get_top_albums_by_artist(artist_name.artist)

        albums = Table(title=f"Top Played Albums for: {artist_name.artist}", expand=True)
        albums.add_column("#", style="dim", width=4)
        albums.add_column("Album", style="white", width=60)
        albums.add_column("Play Count", style="cyan", width=12)

        for i, (album_name, play_count) in enumerate(top_played_albums):
            row_style = album_styles.get(album_name, "white")
            albums.add_row(str(i + 1), album_name, str(play_count), style=row_style)

        self.update(Group(tracks, "", albums))


class SessionInfoWidget(Static):
    def __init__(self, session: SessionScrobbles):
        super().__init__(id=TuiViews.SESSION, classes="content-container")
        self.session = session
        self.update_session_info()

    def update_session_info(self):
        if not self.session or len(self.session) == 0:
            self.update("No scrobbles in this session yet.")
            return

        summary_table = Table(title="Session Summary", width=100)
        summary_table.add_column("Category", style="cyan", width=20)
        summary_table.add_column("Information", style="green")

        summary_table.add_row("Total Scrobbles", str(self.session.count))

        artist_counts = self.session.get_artist_counts()
        if artist_counts:
            top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_artists_str = ", ".join([f"{artist} ({count})" for artist, count in top_artists])
            summary_table.add_row("Top Artists", top_artists_str)

        multiple = self.session.get_multiple_scrobbles()
        if multiple:
            multiple_str = ", ".join([f"{song} ({count}×)" for song, count in list(multiple.items())[:3]])
            if len(multiple) > 3:
                multiple_str += f" and {len(multiple) - 3} more..."
            summary_table.add_row("Repeat Scrobbles", multiple_str)

        if self.session.pending:
            summary_table.add_row("Pending Scrobbles", str(len(self.session.pending)))

        scrobbles_table = Table(title="Session Scrobbles", expand=True)
        scrobbles_table.add_column("#", style="dim", width=4)
        scrobbles_table.add_column("Track", style="white", width=30)
        scrobbles_table.add_column("Artist", style="cyan", width=25)
        scrobbles_table.add_column("Album", style="yellow", width=25)
        scrobbles_table.add_column("Time", style="green", width=16)

        for i, scrobble in enumerate(reversed(self.session.scrobbles)):
            scrobbles_table.add_row(
                str(len(self.session.scrobbles) - i),
                scrobble.name,
                scrobble.artist,
                scrobble.album,
                scrobble.scrobbled_at_formatted
            )

        combined_display = Group(summary_table, "", scrobbles_table)
        self.update(combined_display)


class ManualScrobbleWidget(Container):
    def __init__(self, lastfm: LastFmService):
        super().__init__(id=TuiViews.MANUAL_SCROBBLE, classes="content-container")
        self.lastfm = lastfm
        self.album_input = Input(placeholder="Enter album name", id="album-input")
        self.artist_input = Input(placeholder="Enter artist name", id="artist-input")
        self.submit_button = Button("Search", id="search")
        self.result_display = Static(id="result")

    def on_mount(self) -> None:
        self.mount(Static("Album Search", classes="header"))
        self.mount(self.album_input)
        self.mount(self.artist_input)
        self.mount(self.submit_button)
        self.mount(self.result_display)

    async def on_button_pressed(self, event):
        if event.button.id == "search":
            album_name = self.album_input.value
            artist_name = self.artist_input.value
            result = await self.lastfm.get_album(album_name, artist_name, True)
            self.result_display.update(result.__str__() if result else "No results found")
