import unittest
from unittest.mock import AsyncMock, Mock

from spotipy.exceptions import SpotifyOauthError

from library.integrations import PlaybackAction
from services.spotify_service import SpotifyService


class SpotifyServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_poll_spotify_uses_desktop_by_default(self):
        service = SpotifyService.__new__(SpotifyService)
        service.web_api_enabled = False
        expected_track = Mock()
        service.poll_spotify_desktop = AsyncMock(return_value=expected_track)

        self.assertIs(await service.poll_spotify(), expected_track)
        service.poll_spotify_desktop.assert_awaited_once()

    async def test_poll_spotify_returns_none_when_refresh_token_is_revoked(self):
        service = SpotifyService.__new__(SpotifyService)
        service.spotify = Mock()
        service.web_api_enabled = True
        service.spotify.current_user_playing_track.side_effect = SpotifyOauthError(
            400, "invalid_grant", "Refresh token revoked"
        )
        service.poll_spotify_desktop = AsyncMock(return_value=None)

        self.assertIsNone(await service.poll_spotify())
        self.assertEqual(service.authorization_error, "400")

    async def test_poll_spotify_falls_back_to_the_desktop_app_after_an_api_error(self):
        service = SpotifyService.__new__(SpotifyService)
        service.spotify = Mock()
        service.web_api_enabled = True
        service.spotify.current_user_playing_track.side_effect = SpotifyOauthError(
            400, "invalid_grant", "Refresh token revoked"
        )
        expected_track = Mock()
        service.poll_spotify_desktop = AsyncMock(return_value=expected_track)

        self.assertIs(await service.poll_spotify(), expected_track)
        service.poll_spotify_desktop.assert_awaited_once()

    async def test_playback_control_uses_desktop_when_web_api_is_disabled(self):
        service = SpotifyService.__new__(SpotifyService)
        service.web_api_enabled = False
        service.playback_control_desktop = AsyncMock(return_value=True)

        self.assertTrue(await service.playback_control(PlaybackAction.NEXT))
        service.playback_control_desktop.assert_awaited_once_with(PlaybackAction.NEXT, None)
