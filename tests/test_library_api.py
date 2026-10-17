"""Read-only contract and SQL tests; never connect to the configured database."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from library.dependencies import get_scrobbler_engine
from repositories.listening_repo import ListeningRepository
from routers.library_router import get_listening_repository, library_router


class LibraryApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(library_router)
        self.repository = AsyncMock()
        self.app.dependency_overrides[get_listening_repository] = lambda: self.repository
        self.client = TestClient(self.app)

    def test_history_contract_and_validation(self):
        self.repository.history.return_value = {
            'items': [{'id': 7, 'track': 'Song', 'artist': 'Artist', 'album': None,
                       'scrobbled_at': '2026-09-29T12:00:00'}],
            'page': 2, 'page_size': 40, 'total': 41,
        }
        response = self.client.get('/library/history/', params={'page': 2, 'query': ' Song '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['items'][0]['album'], None)
        self.repository.history.assert_awaited_once_with('Song', 2, 40)
        for params in ({'page': 0}, {'page_size': 101}, {'query': 'a' * 201}):
            self.assertEqual(self.client.get('/library/history/', params=params).status_code, 422)
        self.assertEqual(self.client.get('/library/wrapped/9999/').status_code, 422)
        self.assertEqual(self.client.get('/library/artists/?artist=%20').status_code, 422)

    def test_unavailable_database_is_not_empty_success(self):
        self.app.dependency_overrides.pop(get_listening_repository)
        self.app.dependency_overrides[get_scrobbler_engine] = lambda: SimpleNamespace(database_available=False)
        with patch.object(ListeningRepository, 'history', new_callable=AsyncMock) as history:
            self.assertEqual(self.client.get('/library/history/').status_code, 503)
            history.assert_not_awaited()

    def test_database_failure_returns_recoverable_error(self):
        self.app.dependency_overrides.pop(get_listening_repository)
        self.app.dependency_overrides[get_scrobbler_engine] = lambda: SimpleNamespace(database_available=True)
        with patch.object(ListeningRepository, 'history', new_callable=AsyncMock,
                          side_effect=OperationalError('hidden database details', {}, None)):
            response = self.client.get('/library/history/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('hidden database', response.text)


class ListeningQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_literal_search_and_stable_pagination(self):
        repo = ListeningRepository()
        repo._rows = AsyncMock(return_value=[])
        repo._count = AsyncMock(return_value=0)
        await repo.history('100%_match/', 3, 40)
        statement = repo._rows.call_args.args[0]
        compiled = statement.compile(dialect=postgresql.dialect())
        self.assertIn('ORDER BY scrobbles.scrobbled_at DESC, scrobbles.id DESC', str(compiled))
        self.assertIn('100/%/_match//', compiled.params.values())
        self.assertIn(80, compiled.params.values())
        self.assertIn(40, compiled.params.values())
        self.assertIn('ESCAPE', str(compiled))

    async def test_wrapped_uses_range_and_composite_identities(self):
        repo = ListeningRepository()
        statements = []

        async def execute(statement):
            statements.append(statement)
            result = Mock()
            result.scalar_one.return_value = 0
            result.mappings.return_value.all.return_value = []
            return result

        repo.execute = execute
        summary = await repo.wrapped(2026)
        self.assertEqual(summary['monthly'], [{'month': month, 'count': 0} for month in range(1, 13)])
        sql = [str(statement.compile(dialect=postgresql.dialect())) for statement in statements]
        for query in sql:
            self.assertIn('scrobbles.scrobbled_at >=', query)
            self.assertIn('scrobbles.scrobbled_at <', query)
            self.assertNotIn('EXTRACT(year', query)
        self.assertTrue(any('SELECT DISTINCT scrobbles.artist_name AS artist_name, scrobbles.track_name' in query for query in sql))
        self.assertTrue(any('SELECT DISTINCT scrobbles.artist_name AS artist_name, scrobbles.album_name' in query for query in sql))
        tracks = sql[-1]
        self.assertIn('GROUP BY scrobbles.track_name, scrobbles.artist_name', tracks)
        self.assertNotIn('GROUP BY scrobbles.track_name, scrobbles.artist_name, scrobbles.album_name', tracks)

    async def test_artist_scope_is_exact_and_parameterized(self):
        repo = ListeningRepository()
        repo._rows = AsyncMock(return_value=[])
        repo._count = AsyncMock(return_value=0)
        repo._ranking = AsyncMock(return_value=[])
        await repo.artist("Artist' OR 1=1")
        compiled = repo._rows.call_args.args[0].compile(dialect=postgresql.dialect())
        self.assertIn('WHERE scrobbles.artist_name =', str(compiled))
        self.assertNotIn("Artist'", str(compiled))
        self.assertIn("Artist' OR 1=1", compiled.params.values())
