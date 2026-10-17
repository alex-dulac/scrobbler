import asyncio
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from library.session_scrobbles import SessionScrobbles
from library.state import AppState
from models.schemas import Album, Track
from services.manual_scrobble_service import ManualScrobbleService
from services.scrobbler_engine import ScrobblerEngine
from services.scrobbler_runtime import ScrobblerRuntime, RuntimeState


class ManualScrobbleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ManualScrobbleService()
        self.lastfm = AsyncMock()
        self.lastfm.get_album.return_value = Album(title="Album", artist_name="Artist", tracks=[
            Track(name="First", artist="Artist", duration=180000),
            Track(name="Second", artist="Artist", duration=240000)])
        self.finished = datetime.now(UTC) - timedelta(minutes=1)

    async def preview(self):
        return await self.service.preview(self.lastfm, artist="Artist", album="Album", finished_at=self.finished)

    def runtime(self, session):
        engine = ScrobblerEngine(state=AppState(session=session, scrobble_enabled=False),
                                lastfm=self.lastfm, pollers={}, playback_controllers={})
        runtime = ScrobblerRuntime(engine)
        runtime._state = RuntimeState.RUNNING
        return runtime

    async def test_preview_uses_milliseconds_and_chronological_original_timestamps(self):
        preview = await self.preview()
        self.assertEqual(preview.tracks[0].duration_seconds, 180)
        self.assertEqual(preview.tracks[0].started_at, self.finished - timedelta(seconds=420))
        self.assertEqual(preview.tracks[1].started_at, self.finished - timedelta(seconds=240))
        self.lastfm.scrobble.assert_not_called()

    async def test_duplicate_and_restart_submissions_reuse_durable_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            session = SessionScrobbles()
            session.attach_pending_store(path)
            runtime = self.runtime(session)
            preview = await self.preview()
            results = await asyncio.gather(*(self.service.submit(runtime, preview.preview_id) for _ in range(3)))
            self.assertEqual(len(session.pending), 2)
            self.assertTrue(all(result.count == 2 for result in results))
            self.assertIn("enable scrobbling", results[0].message)
            session.pending.clear()
            session._persist_pending()
            restored = SessionScrobbles()
            restored.attach_pending_store(path)
            result = await ManualScrobbleService().submit(self.runtime(restored), preview.preview_id)
            self.assertEqual(result.count, 2)
            self.assertEqual(restored.pending, [])
            self.assertEqual(await runtime.engine.process_pending(), 0)
            self.lastfm.scrobble.assert_not_called()

    async def test_disk_failure_rolls_back_entire_batch_and_allows_retry(self):
        runtime = self.runtime(SessionScrobbles())
        preview = await self.preview()
        with patch.object(SessionScrobbles, "_persist_pending", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                await self.service.submit(runtime, preview.preview_id)
        self.assertEqual(runtime.snapshot().session.pending, [])
        self.assertEqual(runtime.snapshot().session.manual_batches, {})
        await self.service.submit(runtime, preview.preview_id)
        self.assertEqual(len(runtime.snapshot().session.pending), 2)

    async def test_pending_drain_bounds_network_calls_and_preserves_pause(self):
        from models.schemas import LastFmTrack
        runtime = self.runtime(SessionScrobbles())
        preview = await self.preview()
        await self.service.submit(runtime, preview.preview_id)
        await runtime.engine.set_scrobbling_enabled(True)
        self.lastfm.scrobble.return_value = LastFmTrack(name="First", artist="Artist")
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 1)
        self.assertEqual(self.lastfm.scrobble.await_count, 1)
        self.assertEqual(len(runtime.snapshot().session.pending), 1)
        await runtime.engine.set_scrobbling_enabled(False)
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 0)
        self.assertEqual(self.lastfm.scrobble.await_count, 1)
        await runtime.engine.set_scrobbling_enabled(True)
        self.lastfm.scrobble.return_value = None
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 0)
        self.assertEqual(len(runtime.snapshot().session.pending), 1)

    async def test_rejected_first_track_does_not_starve_later_pending_listens(self):
        from models.schemas import LastFmTrack
        runtime = self.runtime(SessionScrobbles())
        preview = await self.preview()
        await self.service.submit(runtime, preview.preview_id)
        await runtime.engine.set_scrobbling_enabled(True)
        self.lastfm.scrobble.side_effect = [None, LastFmTrack(name="Second", artist="Artist"), None]
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 0)
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 1)
        self.assertEqual(await runtime.engine.process_pending(max_tracks=1), 0)
        submitted_names = [call.args[0].name for call in self.lastfm.scrobble.await_args_list]
        self.assertEqual(submitted_names, ["First", "Second", "First"])
        self.assertEqual([track.name for track in runtime.snapshot().session.pending], ["First"])

    async def test_pending_drain_rejects_nonpositive_batch_size(self):
        runtime = self.runtime(SessionScrobbles())
        for maximum in (0, -1):
            with self.assertRaises(ValueError):
                await runtime.engine.process_pending(max_tracks=maximum)

    async def test_missing_duration_does_not_guess(self):
        self.lastfm.get_album.return_value.tracks[0].duration = 0
        with self.assertRaisesRegex(ValueError, "missing track durations"):
            await self.preview()

    async def test_invalid_time_rejected(self):
        for finished in (datetime.now(), datetime.now(UTC) + timedelta(hours=1)):
            with self.subTest(finished=finished):
                self.finished = finished
                with self.assertRaises(ValueError):
                    await self.preview()

    async def test_short_intro_is_reviewed_and_advances_timeline_but_not_queued(self):
        self.lastfm.get_album.return_value.tracks[0].duration = 20000
        preview = await self.preview()
        self.assertFalse(preview.tracks[0].eligible)
        self.assertTrue(preview.tracks[1].eligible)
        self.assertEqual(preview.tracks[0].started_at, self.finished - timedelta(seconds=260))
        self.assertEqual(preview.tracks[1].started_at, self.finished - timedelta(seconds=240))
        runtime = self.runtime(SessionScrobbles())
        result = await self.service.submit(runtime, preview.preview_id)
        self.assertEqual(result.count, 1)
        self.assertEqual(runtime.snapshot().session.pending[0].name, "Second")

    async def test_album_without_eligible_tracks_is_rejected(self):
        for track in self.lastfm.get_album.return_value.tracks:
            track.duration = 30000
        with self.assertRaisesRegex(ValueError, "no tracks longer"):
            await self.preview()

    async def test_unknown_and_expired_previews_rejected(self):
        runtime = self.runtime(SessionScrobbles())
        with self.assertRaises(ValueError):
            await self.service.submit(runtime, "unknown")
        preview = await self.preview()
        self.service._previews[preview.preview_id].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with self.assertRaises(ValueError):
            await self.service.submit(runtime, preview.preview_id)

    async def test_client_mutation_cannot_change_reviewed_tracks(self):
        runtime = self.runtime(SessionScrobbles())
        preview = await self.preview()
        preview.tracks[0].name = "Changed"
        await self.service.submit(runtime, preview.preview_id)
        self.assertEqual(runtime.snapshot().session.pending[0].name, "First")


class ManualRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_preview_and_submission_require_reviewed_identifier(self):
        import httpx
        from fastapi import FastAPI
        from library.dependencies import get_lastfm_service, get_scrobbler_runtime
        from routers.manual_router import manual_router

        lastfm = AsyncMock()
        lastfm.get_album.return_value = Album(title="Album", artist_name="Artist", tracks=[
            Track(name="Song", artist="Artist", duration=180000)])
        state = AppState(scrobble_enabled=False)
        engine = ScrobblerEngine(state=state, lastfm=lastfm, pollers={}, playback_controllers={})
        runtime = ScrobblerRuntime(engine)
        runtime._state = RuntimeState.RUNNING
        app = FastAPI()
        app.include_router(manual_router)
        app.dependency_overrides[get_lastfm_service] = lambda: lastfm
        app.dependency_overrides[get_scrobbler_runtime] = lambda: runtime
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/manual/album/", params={"artist": "Artist", "album": "Album",
                "finished_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()})
            self.assertEqual(response.status_code, 200, response.text)
            preview_id = response.json()["preview_id"]
            altered = await client.post("/manual/submit/", json={"preview_id": preview_id, "tracks": []})
            self.assertEqual(altered.status_code, 422)
            response = await client.post("/manual/submit/", json={"preview_id": preview_id})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["count"], 1)
            response = await client.post("/manual/submit/", json={"preview_id": preview_id})
            self.assertEqual(len(state.session.pending), 1)
            self.assertEqual(response.status_code, 200)
            lastfm.scrobble.assert_not_called()
