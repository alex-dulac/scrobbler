"""Read-only contract and SQL tests; never connect to the configured database."""
import asyncio
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from library.dependencies import get_scrobbler_engine
from repositories.listening_cache import ListeningCache, listening_cache
from repositories.listening_repo import ListeningRepository
from repositories.scrobble_repo import ScrobbleRepository
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

    def test_on_this_day_contract(self):
        self.repository.on_this_day.return_value = {'date': '2026-10-17', 'years': [
            {'year': 2025, 'total_scrobbles': 2,
             'top_tracks': [{'name': 'Song', 'artist': 'Artist', 'album': None, 'count': 2}]},
        ]}
        response = self.client.get('/library/on-this-day/', params={'date': '2026-10-17'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['years'][0]['top_tracks'][0]['name'], 'Song')
        self.repository.on_this_day.assert_awaited_once_with(date(2026, 10, 17))
        self.assertEqual(self.client.get('/library/on-this-day/').status_code, 422)
        self.assertEqual(self.client.get('/library/on-this-day/?date=nope').status_code, 422)

    def test_artist_contract(self):
        self.repository.artist.return_value = {
            'artist': 'Artist', 'total_scrobbles': 3, 'rank': 14,
            'first_scrobbled_at': '2011-03-04T20:00:00', 'last_scrobbled_at': '2026-09-01T12:00:00',
            'first_track': {'name': 'Song', 'album': None, 'scrobbled_at': '2011-03-04T20:00:00'},
            'years': [{'year': 2011, 'count': 3}], 'top_albums': [],
            'top_tracks': [{'name': 'Song', 'album': None, 'count': 3}],
        }
        body = self.client.get('/library/artists/', params={'artist': 'Artist'}).json()
        self.assertEqual(body['rank'], 14)
        self.assertEqual(body['first_track']['name'], 'Song')
        self.repository.artist.assert_awaited_once_with('Artist')

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
    def setUp(self):
        listening_cache.invalidate()
        self.addCleanup(listening_cache.invalidate)

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

    async def test_history_total_is_counted_once_per_query(self):
        repo = ListeningRepository()
        repo._rows = AsyncMock(return_value=[])
        repo._count = AsyncMock(return_value=120)
        for page in (1, 2, 3):
            self.assertEqual((await repo.history('love', page, 40))['total'], 120)
        self.assertEqual(repo._count.await_count, 1)
        await repo.history('', 1, 40)
        self.assertEqual(repo._count.await_count, 2)

    async def test_years_and_artist_totals_are_cached_until_a_scrobble_is_written(self):
        repo = ListeningRepository()
        repo.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(
            all=Mock(return_value=[2026, 2025])))))
        self.assertEqual(await repo.years(), {'years': [2026, 2025]})
        (await repo.years())['years'].clear()  # callers can't corrupt the cache
        self.assertEqual(await repo.years(), {'years': [2026, 2025]})
        await repo._artist_totals()
        await repo._artist_totals()
        self.assertEqual(repo.execute.await_count, 2)

        session = SimpleNamespace(add_all=Mock(), commit=AsyncMock())
        await ScrobbleRepository(session).add_and_commit([object()])
        await repo.years()
        await repo._artist_totals()
        self.assertEqual(repo.execute.await_count, 4)

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
        statements = []

        async def execute(statement):
            statements.append(statement)
            result = Mock()
            result.scalar_one.return_value = 0
            # One row that satisfies every component query's shape.
            result.mappings.return_value.all.return_value = [{
                'total_scrobbles': 0, 'first_scrobbled_at': None, 'last_scrobbled_at': None,
                'year': 2026, 'count': 0}]
            return result

        repo.execute = execute
        repo._ranking = AsyncMock(return_value=[])
        # Ranking totals cover every artist by design, and are shared via the cache.
        repo._artist_totals = AsyncMock(return_value=())
        await repo.artist("Artist' OR 1=1")
        for statement in statements:
            compiled = statement.compile(dialect=postgresql.dialect())
            self.assertIn('scrobbles.artist_name =', str(compiled))
            self.assertNotIn("Artist'", str(compiled))
            self.assertIn("Artist' OR 1=1", compiled.params.values())

    async def test_artist_reports_rank_span_and_first_listen(self):
        repo = ListeningRepository()
        first = {'name': 'Song', 'album': 'LP', 'scrobbled_at': datetime(2011, 3, 4, 20)}
        repo._listening_span = AsyncMock(return_value={
            'total_scrobbles': 5, 'first_scrobbled_at': first['scrobbled_at'],
            'last_scrobbled_at': datetime(2026, 9, 1)})
        repo._year_counts = AsyncMock(return_value=[{'year': 2011, 'count': 5}])
        # 13 artists ahead; ties with this artist's 5 share its rank.
        repo._artist_totals = AsyncMock(return_value=(1, 5, 5, *[6] * 12, 40))
        repo._rows = AsyncMock(return_value=[first])
        repo._ranking = AsyncMock(return_value=[])
        summary = await repo.artist('Artist')
        self.assertEqual(summary['rank'], 14)
        self.assertEqual(summary['first_track'], first)
        self.assertEqual(summary['last_scrobbled_at'], datetime(2026, 9, 1))
        first_statement = str(repo._rows.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('ORDER BY scrobbles.scrobbled_at, scrobbles.id', first_statement)

        repo._listening_span.return_value = {
            'total_scrobbles': 0, 'first_scrobbled_at': None, 'last_scrobbled_at': None}
        repo._rows.return_value = []
        summary = await repo.artist('Nobody')
        self.assertIsNone(summary['rank'])
        self.assertIsNone(summary['first_track'])

    async def test_wrapped_reports_previous_ranks_and_daily_counts(self):
        repo = ListeningRepository()
        repo._count = AsyncMock(return_value=0)
        statements = []

        async def rows(statement):
            statements.append(statement)
            return []

        repo._rows = rows

        async def ranking(conditions, columns, *, album=False, limit=10):
            year = conditions[0].right.value.year
            if columns[0][1] != 'name' or len(columns) != 1:
                return []
            return [{'name': 'Kept', 'count': 9}, {'name': 'New', 'count': 5}] if year == 2026 else [
                {'name': 'Gone', 'count': 9}, {'name': 'Kept', 'count': 4}]

        repo._ranking = ranking
        summary = await repo.wrapped(2026)
        self.assertEqual(
            [(row['name'], row['previous_rank']) for row in summary['top_artists']],
            [('Kept', 2), ('New', None)],
        )
        daily = str(statements[-1].compile(dialect=postgresql.dialect()))
        self.assertIn('CAST(scrobbles.scrobbled_at AS DATE)', daily)
        self.assertIn('scrobbles.scrobbled_at >=', daily)

    async def test_first_year_has_no_previous_ranking(self):
        repo = ListeningRepository()
        repo._count = AsyncMock(return_value=0)
        repo._rows = AsyncMock(return_value=[])
        repo._ranking = AsyncMock(side_effect=lambda conditions, columns, **_: [
            {**{label: 'Only' for _, label in columns}, 'count': 1}])
        summary = await repo.wrapped(1)
        self.assertEqual(repo._ranking.await_count, 3)  # no previous-year queries
        self.assertEqual(summary['previous_total_scrobbles'], 0)
        self.assertIsNone(summary['top_artists'][0]['previous_rank'])

    async def test_on_this_day_groups_earlier_years(self):
        repo = ListeningRepository()
        repo.years = AsyncMock(return_value={'years': [2026, 2025, 2023]})
        repo._rows = AsyncMock(return_value=[
            {'year': 2025, 'name': 'A', 'artist': 'X', 'album': None, 'count': 3},
            {'year': 2025, 'name': 'B', 'artist': 'X', 'album': 'LP', 'count': 1},
            {'year': 2023, 'name': 'C', 'artist': 'Y', 'album': None, 'count': 2},
        ])
        result = await repo.on_this_day(date(2026, 10, 17), tracks_per_year=1)
        self.assertEqual(result['years'], [
            {'year': 2025, 'total_scrobbles': 4,
             'top_tracks': [{'name': 'A', 'artist': 'X', 'album': None, 'count': 3}]},
            {'year': 2023, 'total_scrobbles': 2,
             'top_tracks': [{'name': 'C', 'artist': 'Y', 'album': None, 'count': 2}]},
        ])
        sql = str(repo._rows.call_args.args[0].compile(dialect=postgresql.dialect()))
        self.assertEqual(sql.count('scrobbles.scrobbled_at >='), 2)  # 2026 itself is excluded

    async def test_on_this_day_skips_missing_leap_days(self):
        repo = ListeningRepository()
        repo.years = AsyncMock(return_value={'years': [2023]})
        repo._rows = AsyncMock()
        result = await repo.on_this_day(date(2024, 2, 29))
        self.assertEqual(result['years'], [])
        repo._rows.assert_not_awaited()

    async def test_queries_overlap_only_without_a_shared_session(self):
        started, release = [], asyncio.Event()

        async def query(number):
            started.append(number)
            await release.wait()
            return number

        async def settle():
            for _ in range(5):
                await asyncio.sleep(0)

        task = asyncio.create_task(ListeningRepository()._gather(query(1), query(2)))
        await settle()
        self.assertEqual(started, [1, 2])
        release.set()
        self.assertEqual(await task, [1, 2])

        started.clear()
        release.clear()
        task = asyncio.create_task(ListeningRepository(Mock())._gather(query(1), query(2)))
        await settle()
        self.assertEqual(started, [1])  # one session: the second waits its turn
        release.set()
        self.assertEqual(await task, [1, 2])


class ListeningCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_expiry_capacity_and_writes_during_a_load(self):
        now = [0.0]
        cache = ListeningCache(ttl=10, capacity=2, clock=lambda: now[0])
        load = AsyncMock(side_effect=[1, 2, 3, 4, 5])
        self.assertEqual(await cache.get('a', load), 1)
        self.assertEqual(await cache.get('a', load), 1)
        now[0] = 10
        self.assertEqual(await cache.get('a', load), 2)  # expired
        await cache.get('b', load)
        await cache.get('c', load)  # evicts 'a', the least recently used
        self.assertEqual(await cache.get('a', load), 5)

        async def load_then_write():
            cache.invalidate()
            return 'stale'
        self.assertEqual(await cache.get('d', load_then_write), 'stale')
        self.assertEqual(await cache.get('d', AsyncMock(return_value='fresh')), 'fresh')

    async def test_failed_write_still_invalidates(self):
        listening_cache.invalidate()
        self.addCleanup(listening_cache.invalidate)
        load = AsyncMock(return_value=(2026,))
        await listening_cache.get('years', load)
        session = SimpleNamespace(add_all=Mock(), commit=AsyncMock(side_effect=OSError))
        with self.assertRaises(OSError):
            await ScrobbleRepository(session).add_and_commit([object()])
        await listening_cache.get('years', load)
        self.assertEqual(load.await_count, 2)
