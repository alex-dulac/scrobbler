"""Current listening context contracts, without a production database."""
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from library.dependencies import get_scrobbler_engine
from models.library_schemas import ListeningContext
from repositories.listening_repo import ListeningRepository
from routers.library_router import get_listening_repository, library_router


def empty_context():
    return {
        'track': {'name': 'Song', 'artist': 'Artist', 'total_scrobbles': 0,
                  'first_scrobbled_at': None, 'last_scrobbled_at': None,
                  'years': [], 'recent_scrobbles': []},
        'album': None,
        'artist': {'artist': 'Artist', 'total_scrobbles': 0, 'years': [],
                   'top_albums': [], 'top_tracks': []},
    }


class ContextApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(library_router)
        self.repository = AsyncMock()
        self.repository.context.return_value = empty_context()
        self.app.dependency_overrides[get_listening_repository] = lambda: self.repository
        self.client = TestClient(self.app)

    def test_contract_and_optional_album(self):
        response = self.client.get('/library/context/', params={'artist': 'Artist', 'track': 'Song'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), empty_context())
        self.repository.context.assert_awaited_once_with('Artist', 'Song', None)
        response = self.client.get('/library/context/', params={
            'artist': 'Artist', 'track': 'Song', 'album': 'Album'})
        self.assertEqual(response.status_code, 200)
        self.repository.context.assert_awaited_with('Artist', 'Song', 'Album')

    def test_validation(self):
        for overrides in ({'artist': ''}, {'track': ' '}, {'album': ''},
                          {'album': '  '}, {'artist': 'a' * 301}, {'track': 't' * 501}):
            response = self.client.get('/library/context/', params={
                'artist': 'Artist', 'track': 'Song', **overrides})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get('/library/context/').status_code, 422)
        self.repository.context.assert_not_awaited()

    def test_album_years_are_included_in_response(self):
        context = empty_context()
        context['album'] = {
            'name': 'Album', 'artist': 'Artist', 'total_scrobbles': 7,
            'unique_tracks': 2, 'first_scrobbled_at': '2020-01-01T12:00:00',
            'last_scrobbled_at': '2026-09-29T12:00:00', 'top_tracks': [],
            'years': [{'year': 2020, 'count': 2}, {'year': 2026, 'count': 5}],
        }
        self.repository.context.return_value = context
        response = self.client.get('/library/context/', params={
            'artist': 'Artist', 'track': 'Song', 'album': 'Album'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['album']['years'], context['album']['years'])

    def test_unavailable_and_failed_database_are_not_empty_history(self):
        self.app.dependency_overrides.pop(get_listening_repository)
        engine = SimpleNamespace(database_available=False)
        self.app.dependency_overrides[get_scrobbler_engine] = lambda: engine
        with patch.object(ListeningRepository, 'context', new_callable=AsyncMock) as context:
            response = self.client.get('/library/context/?artist=Artist&track=Song')
            self.assertEqual(response.status_code, 503)
            context.assert_not_awaited()
            engine.database_available = True
            context.side_effect = OperationalError('private connection detail', {}, None)
            response = self.client.get('/library/context/?artist=Artist&track=Song')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private connection', response.text)


class ContextQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_queries_are_exact_scoped_bounded_and_share_session(self):
        statements = []
        timestamp = datetime(2026, 9, 29, 12)

        async def execute(statement):
            statements.append(statement)
            sql = str(statement)
            result = Mock()
            rows = []
            if 'AS first_scrobbled_at' in sql:
                rows = [{'total_scrobbles': 4, 'first_scrobbled_at': timestamp,
                         'last_scrobbled_at': timestamp}]
                if 'AS unique_tracks' in sql:
                    rows[0]['unique_tracks'] = 2
            elif 'EXTRACT(year' in sql:
                rows = [{'year': 2026, 'count': 4}]
            elif sql.startswith('SELECT scrobbles.scrobbled_at'):
                rows = [{'scrobbled_at': timestamp}]
            result.mappings.return_value.all.return_value = rows
            result.scalar_one.return_value = 4
            return result

        session = SimpleNamespace(execute=AsyncMock(side_effect=execute))
        repo = ListeningRepository(session)
        context = await repo.context("Artist' OR 1=1", 'Song', 'Album')
        ListeningContext.model_validate(context)
        self.assertEqual(context['album']['unique_tracks'], 2)
        self.assertEqual(context['track']['recent_scrobbles'], [timestamp])
        self.assertEqual(context['album']['years'], [{'year': 2026, 'count': 4}])
        self.assertEqual(session.execute.await_count, 10)
        for statement in statements:
            compiled = statement.compile(dialect=postgresql.dialect())
            sql = str(compiled)
            self.assertIn('scrobbles.artist_name =', sql)
            self.assertIn("Artist' OR 1=1", compiled.params.values())
            self.assertNotIn("Artist'", sql)
        for statement in statements[:3]:
            compiled = statement.compile(dialect=postgresql.dialect())
            self.assertIn('scrobbles.track_name =', str(compiled))
            self.assertIn('Song', compiled.params.values())
        for statement in statements[3:6]:
            compiled = statement.compile(dialect=postgresql.dialect())
            self.assertIn('scrobbles.album_name =', str(compiled))
            self.assertIn('Album', compiled.params.values())
        for index in (1, 4):
            compiled = statements[index].compile(dialect=postgresql.dialect())
            self.assertIn(5, compiled.params.values())
        self.assertIn('scrobbles.scrobbled_at DESC, scrobbles.id DESC', str(statements[1]))
        album_year_sql = str(statements[5])
        self.assertIn('GROUP BY EXTRACT(year FROM scrobbles.scrobbled_at)', album_year_sql)
        self.assertIn('ORDER BY year', album_year_sql)

    async def test_unknown_track_has_zero_counts_and_null_dates(self):
        async def execute(statement):
            result = Mock()
            rows = []
            if 'AS first_scrobbled_at' in str(statement):
                rows = [{'total_scrobbles': 0, 'first_scrobbled_at': None,
                         'last_scrobbled_at': None}]
                if 'AS unique_tracks' in str(statement):
                    rows[0]['unique_tracks'] = 0
            result.mappings.return_value.all.return_value = rows
            result.scalar_one.return_value = 0
            return result

        repo = ListeningRepository(SimpleNamespace(execute=execute))
        context = await repo.context('Artist', 'Song')
        self.assertEqual(context, empty_context())
        context = await repo.context('Artist', 'Song', 'Unknown album')
        self.assertEqual(context['album']['years'], [])
        self.assertEqual(context['album']['total_scrobbles'], 0)
        ListeningContext.model_validate(context)
