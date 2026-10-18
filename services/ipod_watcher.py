"""Background iPod detection and review state for the desktop backend."""
import asyncio
import os
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger

from models.db import IpodPlay
from repositories.ipod_repo import IPodRepository
from repositories.scrobble_repo import ScrobbleRepository
from services.ipod import find_ipod_mount
from services.ipod.library import VOLUMES_DIR
from services.ipod_service import capture_plays, get_pending_plays, scrobble_plays, scrobble_window_start


class IpodUnavailableError(RuntimeError):
    """The request needs a database or a connected iPod that isn't there."""


class IpodBusyError(RuntimeError):
    """A scrobble job is already running."""


@dataclass(slots=True)
class IpodScrobbleJob:
    # increments per job so clients can tell a finished job from the previous one
    id: int = 0
    running: bool = False
    total: int = 0
    scrobbled: int = 0
    failed: int = 0
    error: str | None = None


class IpodWatcher:
    """
    Captures plays the moment an iPod mounts and scrobbles reviewed plays in the background.
    Clients follow progress through status(), which /state/ includes on every poll.
    """
    POLL_INTERVAL_SECONDS = 2

    def __init__(
        self,
        engine,
        lastfm,
        *,
        volumes_dir: Path | None = None,
        repo_factory=IPodRepository,
        scrobble_repo_factory=ScrobbleRepository,
    ):
        self._engine = engine
        self._lastfm = lastfm
        self._volumes_dir = volumes_dir or Path(os.environ.get("SCROBBLER_IPOD_VOLUMES", VOLUMES_DIR))
        self._repo_factory = repo_factory
        self._scrobble_repo_factory = scrobble_repo_factory
        self._capture_lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._job_task: asyncio.Task | None = None

        self.mount: Path | None = None
        # increments per capture attempt so clients can announce each one once
        self.capture_id = 0
        self.last_captured = 0
        self.error: str | None = None
        self.pending_count = 0
        self.job = IpodScrobbleJob()

    def status(self) -> dict:
        return {
            "connected": self.mount is not None,
            "name": self.mount.name if self.mount else None,
            "capture_id": self.capture_id,
            "last_captured": self.last_captured,
            "error": self.error,
            "pending_count": self.pending_count,
            "job": asdict(self.job),
        }

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="ipod-watcher")

    async def stop(self) -> None:
        # Plays a cancelled job hadn't reached stay pending for the next review
        for task in (self._task, self._job_task):
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        self._task = None

    async def _run(self) -> None:
        await self.refresh_pending_count()
        while True:
            try:
                await self.check_mount()
            except Exception as e:
                logger.exception(f"iPod check failed: {e}")
            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

    async def check_mount(self) -> None:
        mount = await asyncio.to_thread(find_ipod_mount, self._volumes_dir)
        if mount == self.mount:
            return

        self.mount = mount
        if mount:
            await self.capture()

    async def capture(self) -> None:
        """Apple Music discards the iPod's plays once it opens the iPod, so capture them as soon as it mounts."""
        async with self._capture_lock:
            if self.mount is None:
                raise IpodUnavailableError("No iPod is connected.")

            if not self._engine.database_available:
                self._finish_capture(0, "iPod connected, but its plays can't be captured without a database connection.")
                return

            try:
                captured = await capture_plays(self.mount, self._repo_factory())
            except Exception as e:
                logger.exception(f"Failed to read plays from iPod: {e}")
                self._finish_capture(0, f"Failed to read plays from iPod: {e}")
                return

            await self.refresh_pending_count()
            self._finish_capture(captured, None)

    def _finish_capture(self, captured: int, error: str | None) -> None:
        self.last_captured = captured
        self.error = error
        self.capture_id += 1

    async def refresh_pending_count(self) -> None:
        if not self._engine.database_available:
            return
        try:
            self.pending_count = await self._repo_factory().count_pending_plays(scrobble_window_start())
        except Exception as e:
            logger.warning(f"Could not count pending iPod plays: {e}")

    def _require_database(self) -> None:
        if not self._engine.database_available:
            raise IpodUnavailableError("Reviewing iPod plays requires a database connection.")

    async def pending_plays(self) -> list[IpodPlay]:
        self._require_database()
        plays = await get_pending_plays(self._repo_factory())
        self.pending_count = len(plays)
        return plays

    async def discard(self, play_ids: list[int]) -> None:
        self._require_database()
        await self._repo_factory().discard_plays(play_ids, datetime.now())
        await self.refresh_pending_count()

    async def start_scrobble(self, play_ids: list[int]) -> int:
        """Start scrobbling the given plays in the background. Returns how many will be attempted."""
        if self.job.running:
            raise IpodBusyError("iPod plays are already being scrobbled.")
        self._require_database()

        # Claim the job before awaiting so a concurrent request can't start a second one
        job = self.job = IpodScrobbleJob(id=self.job.id + 1, running=True)
        try:
            plays = await self._repo_factory().get_pending_plays_by_id(play_ids, scrobble_window_start())
        except BaseException:
            job.running = False
            raise

        if not plays:
            job.running = False
            raise ValueError("None of the selected plays can still be scrobbled.")

        job.total = len(plays)
        self._job_task = asyncio.create_task(self._scrobble(job, plays), name="ipod-scrobble")
        return len(plays)

    async def _scrobble(self, job: IpodScrobbleJob, plays: list[IpodPlay]) -> None:
        def progress(scrobbled: int, failed: int) -> None:
            job.scrobbled, job.failed = scrobbled, failed

        try:
            await scrobble_plays(
                self._lastfm, self._repo_factory(), self._scrobble_repo_factory(), plays, on_progress=progress
            )
        except Exception as e:
            logger.exception(f"Scrobbling iPod plays stopped: {e}")
            job.error = f"Scrobbling iPod plays stopped: {e}"
            job.failed = job.total - job.scrobbled
        finally:
            try:
                await self.refresh_pending_count()
            finally:
                job.running = False
