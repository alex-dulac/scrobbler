import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from library.dependencies import get_ipod_watcher
from models.schemas import LastFmTrack
from routers.ipod_router import ipod_router
from services.ipod_watcher import IpodBusyError, IpodUnavailableError, IpodWatcher

PLAYED_AT = datetime(2026, 10, 17, 18, 30).astimezone()


def make_play(id: int, minute: int = 30, **kwargs) -> SimpleNamespace:
    defaults = dict(id=id, track_name="Filler", artist_name="Minor Threat", album_name=None,
                    played_at=PLAYED_AT.replace(minute=minute), played_at_estimated=False)
    return SimpleNamespace(**(defaults | kwargs))


class WatcherTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.volumes = Path(tempfile.mkdtemp())
        self.engine = SimpleNamespace(database_available=True)
        self.repo = Mock(
            count_pending_plays=AsyncMock(return_value=3),
            get_pending_plays_by_id=AsyncMock(return_value=[]),
            discard_plays=AsyncMock(),
            mark_scrobbled=AsyncMock(),
        )
        self.lastfm = Mock(scrobble=AsyncMock(return_value=LastFmTrack(name="Filler", artist="Minor Threat")))
        self.watcher = IpodWatcher(
            self.engine,
            self.lastfm,
            volumes_dir=self.volumes,
            repo_factory=lambda: self.repo,
            scrobble_repo_factory=lambda: Mock(add_scrobble=AsyncMock()),
        )

    def mount_ipod(self, name: str = "IPOD") -> Path:
        itunes = self.volumes / name / "iPod_Control" / "iTunes"
        itunes.mkdir(parents=True)
        (itunes / "iTunesDB").write_bytes(b"")
        return self.volumes / name

    def unmount_ipod(self, name: str = "IPOD") -> None:
        (self.volumes / name / "iPod_Control" / "iTunes" / "iTunesDB").unlink()


@patch("services.ipod_watcher.capture_plays", new_callable=AsyncMock, return_value=5)
class CaptureTest(WatcherTestCase):
    async def test_captures_once_per_mount(self, capture_plays):
        await self.watcher.check_mount()
        capture_plays.assert_not_awaited()

        mount = self.mount_ipod()
        await self.watcher.check_mount()
        await self.watcher.check_mount()

        capture_plays.assert_awaited_once()
        self.assertEqual(capture_plays.await_args.args[0], mount)
        status = self.watcher.status()
        self.assertEqual(
            {k: status[k] for k in ("connected", "name", "capture_id", "last_captured", "error", "pending_count")},
            {"connected": True, "name": "IPOD", "capture_id": 1, "last_captured": 5, "error": None, "pending_count": 3},
        )

    async def test_recaptures_after_remount(self, capture_plays):
        self.mount_ipod()
        await self.watcher.check_mount()
        self.unmount_ipod()
        await self.watcher.check_mount()
        self.assertFalse(self.watcher.status()["connected"])

        self.mount_ipod("IPOD 2")
        await self.watcher.check_mount()

        self.assertEqual(capture_plays.await_count, 2)
        self.assertEqual(self.watcher.capture_id, 2)

    async def test_without_database_reports_instead_of_capturing(self, capture_plays):
        self.engine.database_available = False
        self.mount_ipod()

        await self.watcher.check_mount()

        capture_plays.assert_not_awaited()
        self.assertEqual(self.watcher.capture_id, 1)
        self.assertIn("database", self.watcher.error)

    async def test_read_failure_is_reported(self, capture_plays):
        capture_plays.side_effect = ValueError("Truncated Play Counts file")
        self.mount_ipod()

        await self.watcher.check_mount()

        self.assertEqual(self.watcher.error, "Failed to read plays from iPod: Truncated Play Counts file")
        self.assertEqual(self.watcher.last_captured, 0)

    async def test_rescan_needs_a_connected_ipod(self, capture_plays):
        with self.assertRaises(IpodUnavailableError):
            await self.watcher.capture()


class ScrobbleJobTest(WatcherTestCase):
    async def test_scrobbles_selected_plays_in_background(self):
        self.repo.get_pending_plays_by_id.return_value = [make_play(1), make_play(2, minute=35)]

        self.assertEqual(await self.watcher.start_scrobble([1, 2]), 2)
        self.assertTrue(self.watcher.job.running)
        await self.watcher._job_task

        self.assertEqual(self.repo.get_pending_plays_by_id.await_args.args[0], [1, 2])
        self.assertEqual(
            self.watcher.status()["job"],
            {"id": 1, "running": False, "total": 2, "scrobbled": 2, "failed": 0, "error": None},
        )
        self.repo.count_pending_plays.assert_awaited()

    async def test_counts_failed_scrobbles(self):
        self.repo.get_pending_plays_by_id.return_value = [make_play(1), make_play(2, minute=35)]
        self.lastfm.scrobble.side_effect = [None, LastFmTrack(name="Filler", artist="Minor Threat")]

        await self.watcher.start_scrobble([1, 2])
        await self.watcher._job_task

        self.assertEqual((self.watcher.job.scrobbled, self.watcher.job.failed), (1, 1))

    async def test_rejects_a_second_job_while_running(self):
        release = asyncio.Event()

        async def slow_scrobble(*args, **kwargs):
            await release.wait()
            return LastFmTrack(name="Filler", artist="Minor Threat")

        self.lastfm.scrobble.side_effect = slow_scrobble
        self.repo.get_pending_plays_by_id.return_value = [make_play(1)]
        await self.watcher.start_scrobble([1])

        with self.assertRaises(IpodBusyError):
            await self.watcher.start_scrobble([1])

        release.set()
        await self.watcher._job_task

    async def test_nothing_left_to_scrobble(self):
        with self.assertRaises(ValueError):
            await self.watcher.start_scrobble([99])
        self.assertFalse(self.watcher.job.running)

    async def test_job_error_marks_remaining_plays_failed(self):
        self.repo.get_pending_plays_by_id.return_value = [make_play(1), make_play(2, minute=35)]
        self.lastfm.scrobble.side_effect = [LastFmTrack(name="Filler", artist="Minor Threat"), RuntimeError("offline")]

        await self.watcher.start_scrobble([1, 2])
        await self.watcher._job_task

        job = self.watcher.job
        self.assertEqual((job.running, job.scrobbled, job.failed), (False, 1, 1))
        self.assertIn("offline", job.error)


class IpodApiTest(unittest.TestCase):
    def setUp(self):
        self.watcher = Mock(
            pending_plays=AsyncMock(return_value=[make_play(1, album_name="Complete Discography", played_at_estimated=True)]),
            start_scrobble=AsyncMock(return_value=1),
            discard=AsyncMock(),
            capture=AsyncMock(),
            error=None,
            last_captured=4,
        )
        app = FastAPI()
        app.include_router(ipod_router)
        app.dependency_overrides[get_ipod_watcher] = lambda: self.watcher
        self.client = TestClient(app)

    def test_lists_pending_plays(self):
        response = self.client.get("/ipod/plays/")

        self.assertEqual(response.status_code, 200)
        play, = response.json()["plays"]
        self.assertEqual(play["album_name"], "Complete Discography")
        self.assertTrue(play["played_at_estimated"])

    def test_scrobble_and_discard_take_selected_ids(self):
        self.assertEqual(self.client.post("/ipod/scrobble/", json={"play_ids": [1]}).json()["count"], 1)
        self.watcher.start_scrobble.assert_awaited_once_with([1])

        self.assertEqual(self.client.post("/ipod/discard/", json={"play_ids": [2, 3]}).json()["count"], 2)
        self.watcher.discard.assert_awaited_once_with([2, 3])

    def test_validates_requests(self):
        for body in ({"play_ids": []}, {"play_ids": [1], "extra": True}, {}):
            self.assertEqual(self.client.post("/ipod/scrobble/", json=body).status_code, 422)

    def test_maps_watcher_errors_to_statuses(self):
        cases = [
            (IpodUnavailableError("needs a database"), 503),
            (IpodBusyError("already running"), 409),
            (ValueError("nothing to scrobble"), 422),
        ]
        for error, status in cases:
            self.watcher.start_scrobble.side_effect = error
            response = self.client.post("/ipod/scrobble/", json={"play_ids": [1]})
            self.assertEqual((response.status_code, response.json()["detail"]), (status, str(error)))

    def test_rescan_reports_capture(self):
        self.assertEqual(self.client.post("/ipod/rescan/").json()["count"], 4)

        self.watcher.error = "Failed to read plays from iPod: bad file"
        response = self.client.post("/ipod/rescan/")
        self.assertEqual((response.status_code, response.json()["detail"]), (503, self.watcher.error))


if __name__ == "__main__":
    unittest.main()
