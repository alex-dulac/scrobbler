from collections import defaultdict
from datetime import datetime

from rich.console import RenderableType, Group
from rich.progress import Progress, TextColumn, BarColumn
from rich.table import Table
from textual.containers import ScrollableContainer
from textual.widgets import Static

from config import settings
from models.session import SessionScrobbles
from models.track import Track, LastFmTrack

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


class SongInfoWidget(Static):
    def render(self) -> RenderableType:
        return self.renderable


class ScrobbleProgressBar(Static):
    def __init__(self, id=None):
        super().__init__(id=id)
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


class HistoryContent(Static):
    def __init__(self, id=None):
        super().__init__(id=id)
        self.update("No song selected")


class HistoryListWidget(ScrollableContainer):
    def __init__(self, id=None):
        super().__init__(id=id, classes="content-container")
        self.content = HistoryContent(id="history-list")

    def on_mount(self) -> None:
        self.mount(self.content)
        self.content.update("No song selected")

    def update(self, renderable):
        if hasattr(self, "content") and self.content.is_mounted:
            self.content.update(renderable)

    def update_list(self, current_song: Track, scrobbles: list[LastFmTrack]):
        if not current_song:
            self.update("No song selected")
            return

        if scrobbles is False:
            self.update("Failed to load scrobble history")
            return

        if not scrobbles:
            self.update(f"No previous scrobbles found for: {current_song.display_name()}")
            return

        table = Table(title=f"Scrobble History for: {current_song.display_name()}", expand=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Timestamp", style="cyan")

        for i, scrobble in enumerate(scrobbles):
            dt = datetime.strptime(scrobble.scrobbled_at, settings.DATETIME_FORMAT)
            timestamp = dt.strftime(settings.DATETIME_FORMAT)
            table.add_row(
                str(i + 1),
                timestamp
            )

        table.add_section()
        table.add_row(
            "Total",
            f"{len(scrobbles)} scrobbles"
        )

        self.update(table)


class HistoryChartWidget(ScrollableContainer):
    def __init__(self, id=None):
        super().__init__(id=id, classes="content-container")
        self.content = HistoryContent(id="history-chart")

    def on_mount(self) -> None:
        self.mount(self.content)
        self.content.update("No song selected")

    def update(self, renderable):
        if hasattr(self, "content") and self.content.is_mounted:
            self.content.update(renderable)

    def update_chart(self, current_song: Track, scrobbles: list[LastFmTrack], start_year: int) -> None:
        if not current_song:
            self.update("No song selected")
            return

        if scrobbles is False:
            self.update("Failed to load scrobble history")
            return

        if not scrobbles:
            self.update(f"No previous scrobbles found for: {current_song.display_name()}")
            return

        year_counts = defaultdict(int)
        for scrobble in scrobbles:
            dt = datetime.strptime(scrobble.scrobbled_at, settings.DATETIME_FORMAT)
            year_counts[dt.year] += 1

        current_year = datetime.now().year
        all_years = range(start_year, current_year + 1)

        chart_table = Table(title=f"Scrobbles by Year: {current_song.display_name()}", expand=True)
        chart_table.add_column("Year", style="cyan", width=8)
        chart_table.add_column("Count", style="white", width=8)
        chart_table.add_column("Chart", style="green")

        # get max count for bar scaling
        max_count = max(year_counts.values()) if year_counts else 1

        for year in all_years:
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
        avg_per_year = total_scrobbles / len(all_years)

        summary_table = Table(title="Additional Stats", width=60)
        summary_table.add_column("Metric", style="dim")
        summary_table.add_column("Value", style="bold white")

        summary_table.add_row("Total Scrobbles", str(total_scrobbles))
        summary_table.add_row("Years With Scrobbles", str(len(year_counts)))
        summary_table.add_row("Average per Year", f"{avg_per_year:.1f}")
        summary_table.add_row("Peak Year", f"{max(year_counts, key=year_counts.get)} ({max(year_counts.values())} scrobbles)")

        combined_display = Group(chart_table, "", summary_table)
        self.update(combined_display)


class SessionInfoWidget(Static):
    def __init__(self, session: SessionScrobbles, id=None):
        super().__init__(id=id, classes="content-container")
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
                scrobble.scrobbled_at
            )

        combined_display = Group(summary_table, "", scrobbles_table)
        self.update(combined_display)
