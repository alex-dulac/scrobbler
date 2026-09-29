import asyncio
import json
import sys
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from desktop_backend import managed_instance_lock
from library.session_scrobbles import SessionScrobbles
from library.state import AppState
from models.schemas import LastFmTrack, Track
from services.scrobbler_engine import ScrobblerEngine


class DesktopPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_survives_restart_with_original_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pending.json"
            started = datetime(2026, 9, 28, tzinfo=UTC)
            track = Track(name="Song", artist="Artist", listening_started_at=started)
            session = SessionScrobbles()
            session.attach_pending_store(path)
            session.add_pending(track)
            restored = SessionScrobbles()
            restored.attach_pending_store(path)
            state = AppState(session=restored)
            lastfm = AsyncMock()
            lastfm.scrobble.return_value = LastFmTrack(name="Song", artist="Artist")
            engine = ScrobblerEngine(state=state, lastfm=lastfm, pollers={}, playback_controllers={})
            self.assertEqual(await engine.process_pending(), 1)
            self.assertEqual(lastfm.scrobble.call_args.kwargs["scrobbled_at"], started)
            reloaded = SessionScrobbles()
            reloaded.attach_pending_store(path)
            self.assertEqual(reloaded.pending, [])

    async def test_failed_submission_is_durable_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pending.json"
            state = AppState(current_song=Track(name="Song", playing=True))
            state.session.attach_pending_store(path)

            async def fail(track, **kwargs):
                self.assertTrue(path.exists())
                raise OSError("offline")

            lastfm = AsyncMock()
            lastfm.scrobble.side_effect = fail
            engine = ScrobblerEngine(state=state, lastfm=lastfm, pollers={}, playback_controllers={})
            await engine.scrobble_current()
            await engine.shutdown(process_pending=False)
            self.assertEqual(len(SessionScrobbles.model_validate_json(path.read_text()).pending), 1)

    async def test_accepted_listen_stays_marked_if_local_removal_fails(self):
        track = Track(name="Song", playing=True)
        state = AppState(current_song=track)
        lastfm = AsyncMock()
        lastfm.scrobble.return_value = LastFmTrack(name="Song")
        engine = ScrobblerEngine(state=state, lastfm=lastfm, pollers={}, playback_controllers={})
        with patch.object(SessionScrobbles, "remove_pending", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                await engine.scrobble_current()
        self.assertTrue(track.scrobbled)
        self.assertFalse((await engine.scrobble_current()).accepted)

    def test_pending_identity_survives_model_subclasses(self):
        from models.schemas import AppleMusicTrack
        track = AppleMusicTrack(name="Song", artist="Artist", listening_started_at=datetime.now(UTC))
        session = SessionScrobbles()
        session.add_pending(track)
        restored = SessionScrobbles.model_validate_json(session.model_dump_json())
        restored.add_pending(track)
        self.assertEqual(len(restored.pending), 1)
        restored.remove_pending(track)
        self.assertEqual(restored.pending, [])

    def test_second_managed_process_is_rejected_and_lock_released(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SCROBBLER_STATE_DIR": directory}):
            with managed_instance_lock():
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with managed_instance_lock():
                        pass
            with managed_instance_lock():
                pass

    async def test_readiness_and_parent_eof_shutdown_without_integrations(self):
        script = """
import sys, types
from fastapi import FastAPI
module = types.ModuleType('server')
module.app = FastAPI()
sys.modules['server'] = module
import desktop_backend
desktop_backend.main()
"""
        with tempfile.TemporaryDirectory() as directory:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                env={**os.environ, "APP_TOKEN": "test-token", "SCROBBLER_STATE_DIR": directory},
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
                if not line:
                    self.fail((await process.stderr.read()).decode())
                readiness = json.loads(line)
                self.assertEqual(readiness["event"], "ready")
                self.assertEqual(readiness["host"], "127.0.0.1")
                self.assertGreater(readiness["port"], 0)
                process.stdin.close()
                self.assertEqual(await asyncio.wait_for(process.wait(), timeout=10), 0)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    def test_state_initialization_does_not_fetch_profile(self):
        with patch("services.lastfm_service.get_lastfm_account_details", side_effect=AssertionError):
            self.assertIsNone(AppState().user)
