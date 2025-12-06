from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel
from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from textual import work
from textual.containers import Container
from textual.widgets import Static, Button, Input

from core import config
from core.database import get_db
from library.session_scrobbles import SessionScrobbles
from models.db import Scrobble
from models.schemas import Track, LastFmTrack
from repositories.filters import ScrobbleFilter
from repositories.scrobble_repo import ScrobbleRepository
from services.lastfm_service import LastFmService, get_lastfm_user

css = """
    Button {
        margin: 0 1;
    }
    #now-playing {
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
        background: $success;
    }
    .active-view {
        background: $secondary;
    }
    """


class TuiViews(str, Enum):
    TRACK_HISTORY = "track-history"
    ARTIST_STATS = "artist-stats"
    SESSION = "session-info"
    MANUAL_SCROBBLE = "manual-scrobble"
    LASTFM_USER = "lastfm-user"
    WRAPPED = "wrapped"


class TuiIds(str, Enum):
    APPLE_MUSIC = "apple-music"
    SPOTIFY = "spotify"
    PLAY_PAUSE = "play-pause"
    PREVIOUS_TRACK = "previous-track"
    NEXT_TRACK = "next-track"
    QUIT = "quit"
    SHOW_TRACK_HISTORY = "show-track-history"
    SHOW_ARTIST_STATS = "show-artist-stats"
    SHOW_SESSION = "show-session"
    SHOW_MANUAL_SCROBBLE = "show-manual-scrobble"
    SHOW_LASTFM_USER = "show-lastfm-user"
    SHOW_WRAPPED = "show-wrapped"


playback_controls = Container(
    Button("Apple Music", id=TuiIds.APPLE_MUSIC.value, classes="active-button"),
    Button("Spotify", id=TuiIds.SPOTIFY.value),
    Button("⏯ Play/Pause", id=TuiIds.PLAY_PAUSE),
    Button("⏮ Back", id=TuiIds.PREVIOUS_TRACK),
    Button("⏭ Skip", id=TuiIds.NEXT_TRACK),
    Button("Quit", id=TuiIds.QUIT, variant="error"),
    classes="controls",
    id="controls"
)


view_controls = Container(
    Button("Track History", id=TuiIds.SHOW_TRACK_HISTORY),
    Button("Artist Stats", id=TuiIds.SHOW_ARTIST_STATS),
    Button("Session", id=TuiIds.SHOW_SESSION),
    Button("Manual Scrobble", id=TuiIds.SHOW_MANUAL_SCROBBLE),
    Button("Last.fm User", id=TuiIds.SHOW_LASTFM_USER),
    Button("Wrapped", id=TuiIds.SHOW_WRAPPED),
    classes="controls",
    id="view-controls"
)

class ViewConfig(BaseModel):
    view: TuiViews
    requires_db: bool


view_configs = {
    TuiIds.SHOW_TRACK_HISTORY: ViewConfig(view=TuiViews.TRACK_HISTORY, requires_db=True),
    TuiIds.SHOW_ARTIST_STATS: ViewConfig(view=TuiViews.ARTIST_STATS, requires_db=True),
    TuiIds.SHOW_SESSION: ViewConfig(view=TuiViews.SESSION, requires_db=False),
    TuiIds.SHOW_MANUAL_SCROBBLE: ViewConfig(view=TuiViews.MANUAL_SCROBBLE, requires_db=True),
    TuiIds.SHOW_LASTFM_USER: ViewConfig(view=TuiViews.LASTFM_USER, requires_db=False),
    TuiIds.SHOW_WRAPPED: ViewConfig(view=TuiViews.WRAPPED, requires_db=True),
}

async def get_scrobbles_by_year_chart(
        scrobbles: list[LastFmTrack],
        table_name: str,
        years: range
) -> tuple[Table, defaultdict[Any, int]]:
    chart_table = Table(title=table_name, expand=True)
    chart_table.add_column("Year", style="cyan", width=8)
    chart_table.add_column("Count", style="white", width=8)
    chart_table.add_column("Chart", style="green")

    year_counts = defaultdict(int)
    for scrobble in scrobbles:
        year_counts[scrobble.scrobbled_at.year] += 1

    # get max count for bar scaling
    max_count = max(year_counts.values()) if year_counts else 1

    for year in years:
        count = year_counts.get(year, 0)
        chart_display = "|"
        if count > 0:
            bar_width = int((count / max_count) * 100)
            bar = "█" * bar_width
            chart_display = f"{bar} ({count})"

        chart_table.add_row(str(year), str(count), chart_display)

    chart_table.add_section()

    return chart_table, year_counts


class NowPlayingWidget(Static):
    def __init__(self):
        super().__init__(id="now-playing")


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


class BaseDbWidget(Static):
    def __init__(self, id = None, db_connected: bool = False):
        super().__init__(id=id, classes="content-container")
        self.db_connected = db_connected


class TrackHistoryWidget(BaseDbWidget):
    def __init__(self):
        super().__init__(
            id=TuiViews.TRACK_HISTORY,
            db_connected=False,
        )

    @work
    async def update_chart(self, current_song: Track, years: range) -> None:
        if not self.db_connected:
            return

        if not current_song:
            self.update("No song selected")
            return

        async with get_db() as session:
            repo = ScrobbleRepository(session)
            scrobbles = await repo.get_scrobbles_like_track(
                track_name=current_song.clean_name,
                artist_name=current_song.artist
            )

        if not scrobbles:
            self.update(f"No previous scrobbles found for: {current_song.display_name}")
            return

        chart_table, year_counts = await get_scrobbles_by_year_chart(
            scrobbles=scrobbles,
            table_name=f"Scrobbles by Year for: {current_song.display_name}",
            years=years
        )
        total_scrobbles = sum(year_counts.values())
        avg_per_year = total_scrobbles / len(years)

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


class ArtistStatsWidget(BaseDbWidget):
    def __init__(self, db_connected: bool = False):
        super().__init__(
            id=TuiViews.ARTIST_STATS,
            db_connected=db_connected,
        )

    @work
    async def update_artist_stats(self, current_song: Track, years: range) -> None:
        if not self.db_connected:
            return

        if not current_song:
            self.update("No song selected")
            return

        artist = current_song.artist

        async with get_db() as session:
            repo = ScrobbleRepository(session)
            top_played_tracks = await repo.get_top_tracks_by_artist(artist, limit=30)
            top_played_albums = await repo.get_top_albums_by_artist(artist)
            f = ScrobbleFilter(artist_name=artist)
            all_scrobbles_by_artist = await repo.get_scrobbles(f)

        if not top_played_tracks:
            self.update(f"No scrobbles found for artist: {artist}")
            return

        tracks = Table(title=f"Top Played Tracks for: {artist}", expand=True)
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

        albums = Table(title=f"Top Played Albums for: {artist}", expand=True)
        albums.add_column("#", style="dim", width=4)
        albums.add_column("Album", style="white", width=60)
        albums.add_column("Play Count", style="cyan", width=12)

        for i, (album_name, play_count) in enumerate(top_played_albums):
            row_style = album_styles.get(album_name, "white")
            albums.add_row(str(i + 1), album_name, str(play_count), style=row_style)

        chart_table, year_counts = await get_scrobbles_by_year_chart(
            scrobbles=all_scrobbles_by_artist,
            table_name=f"Scrobbles by Year for: {artist}",
            years=years
        )

        combined = Group(chart_table, "", tracks, "", albums)
        self.update(combined)


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


class ManualScrobbleWidget(BaseDbWidget):
    """
    Widget for manually searching and scrobbling albums.
    Allows user to input album name, artist name, and optional datetime.
    Useful if you are old school like me and listen to CDs and vinyl records.
    """
    def __init__(self, db_connected: bool = False):
        super().__init__(
            id=TuiViews.MANUAL_SCROBBLE,
            db_connected=db_connected,
        )
        self.lastfm_service: LastFmService | None = None
        self.album_input = Input(placeholder="Enter album name", id="album-input")
        self.artist_input = Input(placeholder="Enter artist name", id="artist-input")
        self.dt_input = Input(placeholder="Enter around when you finished the album (2025-10-06 18:03:25)", id="datetime-input")
        self.search_button = Button("Search", id="search")
        self.clear_button = Button("Clear", id="clear")
        self.result_display = Static(id="result")
        self.scrobble_button = Button("Scrobble All", id="scrobble-all")
        self.tracks: list[Track] = []

    def on_mount(self) -> None:
        self.mount(Static("Album Search", classes="header"))
        self.mount(Static("Scrobble all tracks of an album. Preview before sending to Last.fm", classes="header"))
        self.mount(self.album_input)
        self.mount(self.artist_input)
        self.mount(self.dt_input)
        self.mount(
            Container(
                self.search_button,
                self.clear_button,
                classes="controls"
            )
        )
        self.mount(self.result_display)

    @work
    async def handle_batch_scrobble(self):
        to_db = []
        for t in self.tracks:
            scrobbled_track = await self.lastfm_service.scrobble(t, t.time_to_scrobble)
            if scrobbled_track:
                db_obj = Scrobble(
                    track_name=scrobbled_track.name,
                    artist_name=scrobbled_track.artist,
                    album_name=scrobbled_track.album,
                    scrobbled_at=scrobbled_track.scrobbled_at,
                )
                to_db.append(db_obj)
        if len(to_db) > 0:
            if not self.db_connected:
                self.update("Database not connected")
                return
            repo = ScrobbleRepository()
            await repo.add_and_commit(to_db)
            self.notify(f"Scrobbled and saved {len(to_db)} tracks to the database.")

    @work(thread=True)
    async def handle_search(self):
        if not self.album_input.value or not self.artist_input.value:
            self.result_display.update("Please enter both album and artist names.")
            return

        now = datetime.now()
        listened_at = now
        if self.dt_input.value:
            listened_at = datetime.strptime(self.dt_input.value, config.DATETIME_FORMAT)

        if listened_at > now:
            self.result_display.update("The 'listened at' datetime cannot be in the future.")
            return

        try:
            album = await self.lastfm_service.get_album(
                title=self.album_input.value,
                artist=self.artist_input.value,
                with_tracks=True
            )
        except Exception as e:
            self.result_display.update(Panel(f"[red]Error loading album info: {str(e)}[/red]", title="Error"))
            return

        if album and album.tracks:
            self.tracks = album.tracks
            current_listened_at = listened_at
            tracks_list = ""
            for t in reversed(self.tracks):
                time_to_scrobble = current_listened_at - timedelta(milliseconds=t.duration)
                t.time_to_scrobble = time_to_scrobble
                tracks_list += f"{t.order}. {t.name} ({time_to_scrobble.strftime(config.DATETIME_FORMAT)})\n"
                current_listened_at = time_to_scrobble
            if tracks_list and not self.scrobble_button.is_mounted:
                self.result_display.update(f"Album: {album.title}\nArtist: {album.artist_name}\nTracks:\n{tracks_list}")
                await self.mount(self.scrobble_button)
        else:
            self.result_display.update("No results found")
            if self.scrobble_button.is_mounted:
                await self.scrobble_button.remove()

    def reset_inputs(self):
        self.album_input.value = ""
        self.artist_input.value = ""
        self.dt_input.value = ""
        self.result_display.update("")
        if self.scrobble_button.is_mounted:
            self.scrobble_button.remove()
        self.tracks = []

    def on_button_pressed(self, event):
        match event.button.id:
            case "clear":
                self.reset_inputs()
            case "search":
                self.result_display.update("Searching...")
                self.result_display.refresh()
                self.handle_search()
            case "scrobble-all":
                self.handle_batch_scrobble()
                self.reset_inputs()


class LastFmUserWidget(Static):
    def __init__(self):
        super().__init__()
        self.lastfm_service: LastFmService | None = None
        self.update("[cyan]Loading Last.fm user data...[/cyan]")

    @work
    async def refresh_data(self):
        if not self.lastfm_service:
            self.update("Last.fm service not initialized")
            return

        self.update("[cyan]Loading Last.fm user data...[/cyan]")

        try:
            user_info = await get_lastfm_user()
        except Exception as e:
            self.update(Panel(f"[red]Error loading user info: {str(e)}[/red]", title="Error"))
            return

        user_table = Table(title="Last.fm User Profile", show_header=False, box=None, width=100)
        user_table.add_column("Field", style="cyan", width=20)
        user_table.add_column("Value", style="white")

        user_table.add_row("Username", user_info.name)
        if user_info.realname:
            user_table.add_row("Real Name", user_info.realname)
        user_table.add_row("Country", user_info.country)
        user_table.add_row("Total Scrobbles", user_info.playcount)
        user_table.add_row("Tracks", user_info.track_count)
        user_table.add_row("Albums", user_info.album_count)
        user_table.add_row("Artists", user_info.artist_count)
        if user_info.registered:
            user_table.add_row("Member Since", user_info.registered.strftime("%B %d, %Y"))
        user_table.add_row("Subscriber", "Yes" if user_info.subscriber == "1" else "No")
        user_table.add_row("Profile URL", str(user_info.url))

        try:
            recent_tracks = await self.lastfm_service.get_user_recent_tracks()
        except Exception as e:
            self.update(user_table)  # Show user info even if tracks fail
            return

        tracks_table = Table(title="Recent Scrobbles", show_header=True, box=None, expand=True)
        tracks_table.add_column("Track", style="green", width=30)
        tracks_table.add_column("Artist", style="yellow", width=25)
        tracks_table.add_column("Album", style="magenta", width=25)
        tracks_table.add_column("Time", style="cyan", width=20)

        for t in recent_tracks:
            tracks_table.add_row(
                t.name,
                t.artist,
                t.album,
                t.scrobbled_at.strftime(config.DATETIME_FORMAT)
            )

        combined_display = Group(user_table, "", tracks_table)
        self.update(combined_display)


class WrappedWidget(BaseDbWidget):
    def __init__(self, db_connected: bool = False):
        super().__init__(
            id=TuiViews.WRAPPED,
            db_connected=db_connected,
        )
        self.years = list(range(datetime.now().year, datetime.now().year))
        self.update("Loading data...")

    @work
    async def get_wrapped_by_year(self, year: int) -> None:
        if not self.db_connected:
            self.update("Database not connected")
            return

        async with get_db() as session:
            repo = ScrobbleRepository(session)

            overview = await repo.get_year_overview(year)

            year_comparison_data = []
            for year_item in sorted(self.years, reverse=True):
                total = await repo.get_total_scrobbles_by_year(year_item)
                artists = await repo.get_unique_artists_by_year(year_item)
                tracks = await repo.get_unique_tracks_by_year(year_item)
                albums = await repo.get_unique_albums_by_year(year_item)
                avg_per_day = total / 365 if total > 0 else 0

                year_comparison_data.append({
                    'year': year_item,
                    'total': total,
                    'artists': artists,
                    'tracks': tracks,
                    'albums': albums,
                    'avg_per_day': avg_per_day
                })

        header = Text()
        header.append(f"\nTotal Scrobbles: ", style="white")
        header.append(f"{overview['total_scrobbles']:,}", style="bold cyan")
        header.append(f" | Unique Artists: ", style="white")
        header.append(f"{overview['unique_artists']:,}", style="bold green")
        header.append(f" | Unique Tracks: ", style="white")
        header.append(f"{overview['unique_tracks']:,}", style="bold yellow")
        header.append(f" | Unique Albums: ", style="white")
        header.append(f"{overview['unique_albums']:,}", style="bold blue")

        top_artists_table = Table(title="🎤 Top Artists", expand=True, show_header=True)
        top_artists_table.add_column("#", style="dim", width=4)
        top_artists_table.add_column("Artist", style="bold magenta", width=40)
        top_artists_table.add_column("Plays", style="cyan", justify="right", width=10)

        for i, (artist, count) in enumerate(overview['top_artists'], 1):
            rank_style = "bold yellow" if i <= 3 else "dim"
            top_artists_table.add_row(
                f"{i}",
                artist,
                f"{count:,}",
                style=rank_style if i <= 3 else None
            )

        top_tracks_table = Table(title="🎵 Top Tracks", expand=True, show_header=True)
        top_tracks_table.add_column("#", style="dim", width=4)
        top_tracks_table.add_column("Track", style="bold green", width=30)
        top_tracks_table.add_column("Artist", style="white", width=25)
        top_tracks_table.add_column("Plays", style="cyan", justify="right", width=10)

        for i, (track, artist, album, count) in enumerate(overview['top_tracks'], 1):
            rank_style = "bold yellow" if i <= 3 else "dim"
            top_tracks_table.add_row(
                f"{i}",
                track,
                artist,
                f"{count:,}",
                style=rank_style if i <= 3 else None
            )

        top_albums_table = Table(title="💿 Top Albums", expand=True, show_header=True)
        top_albums_table.add_column("#", style="dim", width=4)
        top_albums_table.add_column("Album", style="bold blue", width=30)
        top_albums_table.add_column("Artist", style="white", width=25)
        top_albums_table.add_column("Plays", style="cyan", justify="right", width=10)

        for i, (album, artist, count) in enumerate(overview['top_albums'], 1):
            rank_style = "bold yellow" if i <= 3 else "dim"
            top_albums_table.add_row(
                f"{i}",
                album,
                artist,
                f"{count:,}",
                style=rank_style if i <= 3 else None
            )

        monthly_table = Table(title="📅 Monthly Activity", expand=True, show_header=True)
        monthly_table.add_column("Month", style="bold white", width=12)
        monthly_table.add_column("Scrobbles", style="cyan", justify="right", width=12)
        monthly_table.add_column("Chart", style="green", width=40)

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        monthly_data = {month: count for month, count in overview['monthly_breakdown']}
        max_count = max(monthly_data.values()) if monthly_data else 1

        for month_num in range(1, 13):
            count = monthly_data.get(month_num, 0)
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = "█" * bar_length
            monthly_table.add_row(
                month_names[month_num - 1],
                f"{count:,}",
                bar
            )

        fun_facts = Text()
        fun_facts.append("\n✨ Fun Facts ✨\n", style="bold yellow")

        if overview['first_scrobble']:
            first = overview['first_scrobble']
            fun_facts.append(f"\n🎉 First scrobble: ", style="white")
            fun_facts.append(f"{first.track_name}", style="bold green")
            fun_facts.append(f" by ", style="white")
            fun_facts.append(f"{first.artist_name}", style="bold magenta")
            fun_facts.append(f" on {first.scrobbled_at.strftime('%B %d')}", style="dim")

        if overview['most_active_day']:
            date, count = overview['most_active_day']
            fun_facts.append(f"\n🔥 Most active day: ", style="white")
            fun_facts.append(f"{date}", style="bold cyan")
            fun_facts.append(f" with ", style="white")
            fun_facts.append(f"{count:,} scrobbles", style="bold yellow")

        avg_per_day = overview['total_scrobbles'] / 365 if overview['total_scrobbles'] > 0 else 0
        fun_facts.append(f"\n📊 Average per day: ", style="white")
        fun_facts.append(f"{avg_per_day:.1f} scrobbles", style="bold cyan")

        if overview['total_scrobbles'] > 0:
            diversity_score = (overview['unique_tracks'] / overview['total_scrobbles']) * 100
            fun_facts.append(f"\n🎨 Diversity score: ", style="white")
            fun_facts.append(f"{diversity_score:.1f}%", style="bold green")
            fun_facts.append(f" (unique tracks per scrobble)", style="dim")

        comparison_table = Table(title="📊 Year Comparison", expand=True)
        comparison_table.add_column("Year", style="bold magenta", width=8)
        comparison_table.add_column("Scrobbles", style="cyan", justify="right", width=12)
        comparison_table.add_column("Artists", style="green", justify="right", width=10)
        comparison_table.add_column("Tracks", style="yellow", justify="right", width=10)
        comparison_table.add_column("Albums", style="blue", justify="right", width=10)
        comparison_table.add_column("Avg/Day", style="white", justify="right", width=10)

        for year_data in year_comparison_data:
            comparison_table.add_row(
                str(year_data['year']),
                f"{year_data['total']:,}",
                f"{year_data['artists']:,}",
                f"{year_data['tracks']:,}",
                f"{year_data['albums']:,}",
                f"{year_data['avg_per_day']:.1f}"
            )

        combined = Group(
            Panel(header, border_style="magenta"),
            "",
            top_artists_table,
            "",
            top_tracks_table,
            "",
            top_albums_table,
            "",
            monthly_table,
            "",
            Panel(fun_facts, border_style="yellow"),
            "",
            comparison_table
        )

        self.update(combined)

