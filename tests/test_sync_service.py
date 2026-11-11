import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from library.dependencies import get_scrobbler_runtime, get_sync_service
from repositories.scrobble_repo import ScrobbleRepository
from routers.sync_router import sync_router
from services.sync_service import SyncBusyError, SyncService


def played(title: str, artist: str, at: datetime, album: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        track=SimpleNamespace(title=title, artist=SimpleNamespace(name=artist)),
        album=album,
        timestamp=str(int(at.timestamp())),
    )


class SyncScrobblesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = Mock(insert_scrobbles=AsyncMock(side_effect=lambda rows: len(rows)))
        self.lastfm = Mock(get_user_played_tracks_by_time_to=AsyncMock(return_value=[]))
        self.service = SyncService()
        self.service.scrobble_repo = self.repo
        patches = [
            patch("library.dependencies.get_lastfm_service", AsyncMock(return_value=self.lastfm)),
            patch("services.sync_service.asyncio.sleep", AsyncMock()),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def pages(self, *pages):
        self.lastfm.get_user_played_tracks_by_time_to.side_effect = [*pages, []]

    async def test_saves_cleaned_titles_and_counts_only_new_rows(self):
        at = datetime(2026, 11, 10, 9, 15)
        self.pages([played("High 'N' Dry (Remastered 2018)", "Def Leppard", at, "High 'N' Dry (Remastered)")])
        # The unique index skips a scrobble already saved
        self.repo.insert_scrobbles.side_effect = lambda rows: 0

        result = await self.service.sync_scrobbles("2026-11-10", "2026-11-10")

        self.assertEqual(self.repo.insert_scrobbles.await_args.args[0], [{
            "track_name": "High 'N' Dry", "artist_name": "Def Leppard",
            "album_name": "High 'N' Dry", "scrobbled_at": at,
        }])
        self.assertEqual(result, {"fetched_scrobbles": 1, "new_scrobbles": 0})

    async def test_saves_new_scrobbles_once_and_reports_progress(self):
        first, second = datetime(2026, 11, 10, 9, 15), datetime(2026, 11, 10, 9, 10)
        self.pages([played("Filler", "Minor Threat", first), played("Filler", "Minor Threat", first)],
                   [played("Seeing Red", "Minor Threat", second)])
        progress = []

        result = await self.service.sync_scrobbles(on_progress=lambda *counts: progress.append(counts))

        saved = [s for call in self.repo.insert_scrobbles.await_args_list for s in call.args[0]]
        self.assertEqual([(s["track_name"], s["scrobbled_at"]) for s in saved], [("Filler", first), ("Seeing Red", second)])
        self.assertEqual(progress, [(2, 1), (3, 2)])
        self.assertEqual(result, {"fetched_scrobbles": 3, "new_scrobbles": 2})

    async def test_range_includes_the_end_date_and_pages_back_from_the_oldest_scrobble(self):
        oldest = datetime(2026, 11, 9, 23, 0)
        self.pages([played("Filler", "Minor Threat", oldest)])

        await self.service.sync_scrobbles("2026-11-01", "2026-11-09")

        calls = self.lastfm.get_user_played_tracks_by_time_to.await_args_list
        time_from = int(datetime(2026, 11, 1).timestamp())
        self.assertEqual(calls[0].args[0], int(datetime(2026, 11, 10).timestamp()))
        self.assertEqual(calls[0].kwargs["time_from"], time_from)
        # Last.fm's time_to is exclusive, so overlap the oldest second
        self.assertEqual(calls[1].args[0], int(oldest.timestamp()) + 1)

    async def test_page_of_one_second_still_moves_back(self):
        at = datetime(2026, 11, 10, 9, 0)
        self.pages([played("Filler", "Minor Threat", at)], [played("Filler", "Minor Threat", at)])

        await self.service.sync_scrobbles()

        calls = self.lastfm.get_user_played_tracks_by_time_to.await_args_list
        self.assertEqual([c.args[0] for c in calls[1:]], [int(at.timestamp()) + 1, int(at.timestamp())])


class InsertScrobblesTest(unittest.IsolatedAsyncioTestCase):
    async def test_skips_conflicts_and_counts_inserted_rows(self):
        statements = []

        async def execute(statement):
            statements.append(statement)
            return Mock(all=Mock(return_value=[(1,)]))

        session = SimpleNamespace(execute=execute, commit=AsyncMock())
        rows = [{"track_name": "Filler", "artist_name": "Minor Threat", "album_name": None,
                 "scrobbled_at": datetime(2026, 11, 10, 9, 15)}] * 2

        self.assertEqual(await ScrobbleRepository(session).insert_scrobbles(rows), 1)
        self.assertIn("ON CONFLICT DO NOTHING", str(statements[0].compile(dialect=postgresql.dialect())))
        session.commit.assert_awaited_once()
        self.assertEqual(await ScrobbleRepository(session).insert_scrobbles([]), 0)


class SyncJobTest(unittest.IsolatedAsyncioTestCase):
    async def test_runs_one_job_at_a_time_and_records_errors(self):
        service = SyncService()
        release = asyncio.Event()

        async def sync(time_from, time_to, on_progress):
            on_progress(200, 12)
            await release.wait()
            raise RuntimeError("Last.fm is down")

        service.sync_scrobbles = sync
        service.start_scrobble_sync("2026-11-01")
        await asyncio.sleep(0)
        with self.assertRaises(SyncBusyError):
            service.start_scrobble_sync()
        self.assertEqual(
            service.status(),
            {"id": 1, "running": True, "time_from": "2026-11-01", "time_to": None,
             "fetched": 200, "saved": 12, "error": None},
        )

        release.set()
        await service._job_task
        self.assertFalse(service.status()["running"])
        self.assertEqual(service.status()["error"], "Scrobble sync stopped: Last.fm is down")

    async def test_rejects_bad_dates_before_starting(self):
        service = SyncService()
        with self.assertRaises(ValueError):
            service.start_scrobble_sync("11/01/2026")
        self.assertEqual(service.status()["id"], 0)


class SyncRouterTest(unittest.TestCase):
    def setUp(self):
        self.service = Mock(start_scrobble_sync=Mock())
        self.engine = SimpleNamespace(database_available=True)
        app = FastAPI()
        app.include_router(sync_router)
        app.dependency_overrides[get_sync_service] = lambda: self.service
        app.dependency_overrides[get_scrobbler_runtime] = lambda: SimpleNamespace(engine=self.engine)
        self.client = TestClient(app)

    def test_starts_a_sync(self):
        response = self.client.post("/sync/scrobbles/", json={"time_from": "2026-11-04"})
        self.assertEqual(response.status_code, 200)
        self.service.start_scrobble_sync.assert_called_once_with(time_from="2026-11-04", time_to=None)

    def test_rejects_requests_it_cannot_run(self):
        self.service.start_scrobble_sync.side_effect = SyncBusyError("busy")
        self.assertEqual(self.client.post("/sync/scrobbles/", json={}).status_code, 409)
        self.assertEqual(
            self.client.post("/sync/scrobbles/", json={"time_from": "2026-11-05", "time_to": "2026-11-04"}).status_code,
            422,
        )
        self.engine.database_available = False
        self.assertEqual(self.client.post("/sync/scrobbles/", json={}).status_code, 503)


if __name__ == "__main__":
    unittest.main()
