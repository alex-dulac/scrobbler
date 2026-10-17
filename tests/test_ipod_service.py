import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from models.schemas import LastFmTrack
from services.ipod import IpodTrack, expand_plays
from services.ipod.itunesdb import PODCAST_MEDIA_TYPE
from services.ipod_service import SCROBBLE_WINDOW, get_pending_plays, scrobble_plays

LAST_PLAYED = datetime(2026, 10, 17, 18, 33).astimezone()


def make_track(**kwargs) -> IpodTrack:
    defaults = dict(index=0, track_id=1, dbid=2, title="Filler", artist="Minor Threat", duration_ms=90_000)
    return IpodTrack(**(defaults | kwargs))


class ExpandPlaysTest(unittest.TestCase):
    def test_no_pending_plays(self):
        self.assertEqual(expand_plays(make_track()), [])

    def test_single_play_starts_one_duration_before_it_finished(self):
        plays = expand_plays(make_track(pending_play_count=1, pending_last_played=LAST_PLAYED))

        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0].play_number, 1)
        self.assertEqual(plays[0].played_at, LAST_PLAYED - timedelta(seconds=90))
        self.assertFalse(plays[0].estimated)

    def test_repeat_plays_run_back_to_back(self):
        plays = expand_plays(make_track(pending_play_count=3, pending_last_played=LAST_PLAYED))

        self.assertEqual([p.play_number for p in plays], [1, 2, 3])
        self.assertEqual(
            [p.played_at for p in plays],
            [LAST_PLAYED - timedelta(seconds=270), LAST_PLAYED - timedelta(seconds=180), LAST_PLAYED - timedelta(seconds=90)],
        )
        self.assertEqual([p.estimated for p in plays], [True, True, False])


class IsScrobblableTest(unittest.TestCase):
    def test_music_track(self):
        self.assertTrue(make_track(media_type=1).is_scrobblable)
        self.assertTrue(make_track(media_type=None).is_scrobblable)

    def test_podcast(self):
        self.assertFalse(make_track(media_type=PODCAST_MEDIA_TYPE).is_scrobblable)

    def test_missing_artist(self):
        self.assertFalse(make_track(artist=None).is_scrobblable)


class ScrobblePlaysTest(unittest.IsolatedAsyncioTestCase):
    async def test_scrobbles_plays_and_counts_failures(self):
        plays = [
            SimpleNamespace(id=1, track_name="Filler", artist_name="Minor Threat", album_name="Complete Discography", played_at=LAST_PLAYED),
            SimpleNamespace(id=2, track_name="Screaming At A Wall", artist_name="Minor Threat", album_name=None, played_at=LAST_PLAYED),
        ]
        repo = Mock(mark_scrobbled=AsyncMock())
        scrobble_repo = Mock(add_scrobble=AsyncMock())
        lastfm_track = LastFmTrack(name="Filler", artist="Minor Threat")
        lastfm = Mock(scrobble=AsyncMock(side_effect=[lastfm_track, None]))

        result = await scrobble_plays(lastfm, repo, scrobble_repo, plays)

        self.assertEqual(result, (1, 1))
        track, = lastfm.scrobble.await_args_list[0].args
        self.assertEqual((track.clean_name, track.artist, track.clean_album), ("Filler", "Minor Threat", "Complete Discography"))
        self.assertEqual(lastfm.scrobble.await_args_list[0].kwargs["scrobbled_at"], LAST_PLAYED)

        repo.mark_scrobbled.assert_awaited_once()
        self.assertEqual(repo.mark_scrobbled.await_args.args[0], 1)
        scrobble_repo.add_scrobble.assert_awaited_once_with(lastfm_track)

    async def test_scrobbles_oldest_first(self):
        plays = [
            SimpleNamespace(id=1, track_name="B", artist_name="A", album_name=None, played_at=LAST_PLAYED),
            SimpleNamespace(id=2, track_name="A", artist_name="A", album_name=None, played_at=LAST_PLAYED - timedelta(minutes=5)),
        ]
        repo = Mock(mark_scrobbled=AsyncMock())
        lastfm = Mock(scrobble=AsyncMock(return_value=LastFmTrack(name="x", artist="A")))

        await scrobble_plays(lastfm, repo, Mock(add_scrobble=AsyncMock()), plays)

        self.assertEqual([c.args[0] for c in repo.mark_scrobbled.await_args_list], [2, 1])


class GetPendingPlaysTest(unittest.IsolatedAsyncioTestCase):
    async def test_limits_to_scrobble_window(self):
        repo = Mock(get_pending_plays=AsyncMock(return_value=[]))

        await get_pending_plays(repo)

        since = repo.get_pending_plays.await_args.args[0]
        self.assertAlmostEqual(since, datetime.now().astimezone() - SCROBBLE_WINDOW, delta=timedelta(seconds=5))


if __name__ == "__main__":
    unittest.main()
