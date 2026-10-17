import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from routers.artwork_router import _cache, album_artwork


class ArtworkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _cache.clear()

    async def test_album_identity_is_cached_without_touching_playback(self):
        cover = Mock(return_value='https://example.test/cover.jpg')
        network = Mock()
        network.get_album.return_value.get_cover_image = cover
        service = SimpleNamespace(network=network)
        first = await album_artwork('Artist', 'Album', service)
        second = await album_artwork('artist', 'album', service)
        self.assertEqual(first, {'url': 'https://example.test/cover.jpg'})
        self.assertEqual(second, first)
        network.get_album.assert_called_once_with('Artist', 'Album')

    async def test_lookup_failure_is_optional_and_cached_briefly(self):
        network = Mock()
        network.get_album.side_effect = OSError('offline')
        service = SimpleNamespace(network=network)
        self.assertEqual(await album_artwork('Artist', 'Album', service), {'url': None})
        self.assertEqual(await album_artwork('Artist', 'Album', service), {'url': None})
        network.get_album.assert_called_once()
