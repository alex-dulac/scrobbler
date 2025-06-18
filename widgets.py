from datetime import datetime

from rich.console import RenderableType
from rich.progress import Progress, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from textual.containers import ScrollableContainer
from textual.widgets import Static

from config import settings
from models.session import SessionScrobbles
from utils import internet

css = """
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
    #controls {
        layout: horizontal;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #scrobble-history-container {
        height: auto;
        min-height: 10;
        margin: 1 10;
        border: solid $accent;
        width: 80;
    }
    #scrobble-history {
        padding: 1 2;
        width: 100%;
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
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", justify="right"),
            BarColumn(bar_width=None),
            TextColumn("{task.description}", justify="left"),
            expand=True
        )
        self.task_id = self.progress_bar.add_task("", total=100, completed=0)

    def update_progress(self, value, description=""):
        """Update progress value (0-1) and description."""
        percentage = min(100, max(0, int(value * 100)))
        self.progress = value
        self.progress_bar.update(self.task_id, completed=percentage, description=description)
        self.update(self.progress_bar)


class ScrobbleHistoryContent(Static):
    """Content widget for scrobble history."""
    def __init__(self, id=None):
        super().__init__(id=id)
        self.update("No song selected")


class ScrobbleHistoryWidget(ScrollableContainer):
    """Widget to display scrobble history for the current track."""
    def __init__(self, id=None):
        super().__init__(id=id or "scrobble-history-container")
        self.content = ScrobbleHistoryContent(id="scrobble-history")

    def on_mount(self) -> None:
        """Mount the content widget after this widget is mounted."""
        self.mount(self.content)
        self.content.update("No song selected")

    def update(self, renderable):
        """Update the content widget."""
        if hasattr(self, "content") and self.content.is_mounted:
            self.content.update(renderable)

    async def update_history(self, lastfm_service, current_song):
        """Update the scrobble history for the current song."""
        if not current_song:
            self.update("No song selected")
            return

        if not internet():
            self.update("No internet connection. Cannot load scrobble history...")
            return

        self.update(f"Loading scrobble history for: {current_song.display_name()}...")

        scrobbles = await lastfm_service.current_track_user_scrobbles(current_song)

        if scrobbles is False:
            self.update("Failed to load scrobble history")
            return

        if not scrobbles:
            self.update(f"No previous scrobbles found for: {current_song.display_name()}")
            return

        table = Table(title=f"Scrobble History for: {current_song.display_name()}", width=100)
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


class SessionInfoWidget(Static):
    """Widget to display session information."""
    def __init__(self, session: SessionScrobbles, id=None):
        super().__init__(id=id)
        self.session = session
        self.update_session_info()

    def update_session_info(self):
        """Update the session information display."""
        if not self.session or len(self.session) == 0:
            self.update("No scrobbles in this session yet.")
            return

        table = Table(title="Session Information", width=100)
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Information", style="green")

        table.add_row("Total Scrobbles", str(self.session.count))

        artist_counts = self.session.get_artist_counts()
        if artist_counts:
            top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_artists_str = ", ".join([f"{artist} ({count})" for artist, count in top_artists])
            table.add_row("Top Artists", top_artists_str)

        multiple = self.session.get_multiple_scrobbles()
        if multiple:
            multiple_str = ", ".join([f"{song} ({count}×)" for song, count in list(multiple.items())[:3]])
            if len(multiple) > 3:
                multiple_str += f" and {len(multiple) - 3} more..."
            table.add_row("Repeat Scrobbles", multiple_str)

        if self.session.pending:
            table.add_row("Pending Scrobbles", str(len(self.session.pending)))

        self.update(table)
