"""Bounded, read-only queries for the desktop listening library.

Dates follow the existing database's naive datetime convention. Track identity is
artist + title; album metadata does not split a track's listening count.
"""
import asyncio
from datetime import date, datetime, timedelta

from sqlalchemy import Date, and_, cast, extract, func, or_, select

from models.db import Scrobble as S
from repositories.base import BaseRepository


class ListeningRepository(BaseRepository):
    async def _gather(self, *queries):
        """Run independent queries together, each on its own pooled session.

        The library database may be remote, where round trips dominate. A shared
        session can't run queries concurrently, so it runs them in turn.
        """
        if self._db is not None:
            return [await query for query in queries]
        return await asyncio.gather(*queries)

    async def _rows(self, statement):
        result = await self.execute(statement)
        return [dict(row) for row in result.mappings().all()]

    async def _count(self, *conditions, columns=()):
        if columns:
            source = select(*columns).where(*conditions).distinct().subquery()
            statement = select(func.count()).select_from(source)
        else:
            statement = select(func.count(S.id)).where(*conditions)
        return (await self.execute(statement)).scalar_one()

    async def history(self, query: str, page: int, page_size: int):
        conditions = []
        if query:
            # SQLAlchemy escapes %, _ and the escape character for literal search.
            conditions.append(or_(*[
                column.icontains(query, autoescape=True)
                for column in (S.track_name, S.artist_name, S.album_name)
            ]))
        statement = select(
            S.id, S.track_name.label('track'), S.artist_name.label('artist'),
            S.album_name.label('album'), S.scrobbled_at,
        ).where(*conditions).order_by(S.scrobbled_at.desc(), S.id.desc())
        return {
            'items': await self._rows(statement.limit(page_size).offset((page - 1) * page_size)),
            'total': await self._count(*conditions), 'page': page, 'page_size': page_size,
        }

    async def years(self):
        year = extract('year', S.scrobbled_at).label('year')
        result = await self.execute(select(year).distinct().order_by(year.desc()))
        return {'years': [int(value) for value in result.scalars().all()]}

    async def _ranking(self, conditions, columns, *, album=False, limit=10):
        selections = [column.label(label) for column, label in columns]
        if album:
            # A representative album is metadata, not part of track identity.
            selections.append(func.min(S.album_name).label('album'))
        count = func.count(S.id).label('count')
        statement = select(*selections, count).where(*conditions).group_by(
            *[column for column, _ in columns]
        ).order_by(count.desc(), *[column for column, _ in columns]).limit(limit)
        return await self._rows(statement)

    @staticmethod
    def _year_range(year: int):
        return (S.scrobbled_at >= datetime(year, 1, 1),
                S.scrobbled_at < datetime(year + 1, 1, 1))

    @staticmethod
    def _known_album(conditions):
        return (*conditions, S.album_name.is_not(None), S.album_name != '')

    async def _ranked(self, conditions, previous, columns, *, album=False):
        """Top ten for the year, each with its rank in the previous year's top 50."""
        labels = [label for _, label in columns]
        rows, previous_rows = await self._gather(
            self._ranking(conditions, columns, album=album),
            self._ranking(previous, columns, limit=50) if previous is not None else asyncio.sleep(0, []),
        )
        earlier = {tuple(row[label] for label in labels): rank for rank, row in enumerate(previous_rows, 1)}
        return [{**row, 'previous_rank': earlier.get(tuple(row[label] for label in labels))} for row in rows]

    async def wrapped(self, year: int):
        conditions = self._year_range(year)
        previous = self._year_range(year - 1) if year > 1 else None
        known_album = self._known_album(conditions)
        month = extract('month', S.scrobbled_at).label('month')
        day = cast(S.scrobbled_at, Date).label('date')
        (monthly, daily, total, previous_total, artists, albums, tracks,
         top_artists, top_albums, top_tracks) = await self._gather(
            self._rows(select(month, func.count(S.id).label('count')).where(
                *conditions).group_by(month).order_by(month)),
            self._rows(select(day, func.count(S.id).label('count')).where(
                *conditions).group_by(day).order_by(day)),
            self._count(*conditions),
            self._count(*previous) if previous else asyncio.sleep(0, 0),
            self._count(*conditions, columns=(S.artist_name,)),
            self._count(*known_album, columns=(S.artist_name, S.album_name)),
            self._count(*conditions, columns=(S.artist_name, S.track_name)),
            self._ranked(conditions, previous, [(S.artist_name, 'name')]),
            self._ranked(
                known_album, previous and self._known_album(previous),
                [(S.album_name, 'name'), (S.artist_name, 'artist')]),
            self._ranked(
                conditions, previous, [(S.track_name, 'name'), (S.artist_name, 'artist')], album=True),
        )
        counts = {int(row['month']): row['count'] for row in monthly}
        return {
            'year': year,
            'total_scrobbles': total,
            'previous_total_scrobbles': previous_total,
            'unique_artists': artists,
            'unique_albums': albums,
            'unique_tracks': tracks,
            'monthly': [{'month': value, 'count': counts.get(value, 0)} for value in range(1, 13)],
            'daily': daily,
            'top_artists': top_artists,
            'top_albums': top_albums,
            'top_tracks': top_tracks,
        }

    async def on_this_day(self, day: date, *, tracks_per_year: int = 3):
        """What was played on this calendar day in each earlier year."""
        ranges = []
        for year in (await self.years())['years']:
            if year >= day.year:
                continue
            try:
                start = datetime(year, day.month, day.day)
            except ValueError:  # 29 February in a non-leap year
                continue
            ranges.append(and_(S.scrobbled_at >= start, S.scrobbled_at < start + timedelta(days=1)))
        if not ranges:
            return {'date': day, 'years': []}
        year = extract('year', S.scrobbled_at).label('year')
        count = func.count(S.id).label('count')
        rows = await self._rows(select(
            year, S.track_name.label('name'), S.artist_name.label('artist'),
            func.min(S.album_name).label('album'), count,
        ).where(or_(*ranges)).group_by(year, S.track_name, S.artist_name).order_by(
            year.desc(), count.desc(), S.artist_name, S.track_name))
        years: dict[int, dict] = {}
        for row in rows:
            entry = years.setdefault(int(row.pop('year')), {'total_scrobbles': 0, 'top_tracks': []})
            entry['total_scrobbles'] += row['count']
            if len(entry['top_tracks']) < tracks_per_year:
                entry['top_tracks'].append(row)
        return {'date': day, 'years': [{'year': key, **value} for key, value in years.items()]}

    async def _year_counts(self, conditions):
        year = extract('year', S.scrobbled_at).label('year')
        years = await self._rows(select(year, func.count(S.id).label('count')).where(
            *conditions).group_by(year).order_by(year))
        return [{'year': int(row['year']), 'count': row['count']} for row in years]

    async def artist(self, artist: str):
        conditions = (S.artist_name == artist,)
        span, years, ahead, first, top_albums, top_tracks = await self._gather(
            self._listening_span(conditions),
            self._year_counts(conditions),
            self._artists_ahead(artist),
            self._rows(select(
                S.track_name.label('name'), S.album_name.label('album'), S.scrobbled_at,
            ).where(*conditions).order_by(S.scrobbled_at, S.id).limit(1)),
            self._ranking(self._known_album(conditions), [(S.album_name, 'name')]),
            self._ranking(conditions, [(S.track_name, 'name')], album=True),
        )
        return {
            'artist': artist,
            **span,
            # Position among all artists by lifetime scrobbles; ties share a rank.
            'rank': ahead + 1 if span['total_scrobbles'] else None,
            'first_track': first[0] if first else None,
            'years': years,
            'top_albums': top_albums,
            'top_tracks': top_tracks,
        }

    async def _artists_ahead(self, artist: str):
        """How many artists have more lifetime scrobbles than this one."""
        total = select(func.count(S.id)).where(S.artist_name == artist).scalar_subquery()
        ahead = select(S.artist_name).group_by(S.artist_name).having(func.count(S.id) > total).subquery()
        return (await self.execute(select(func.count()).select_from(ahead))).scalar_one()


    async def _listening_span(self, conditions, *, album=False):
        selections = [
            func.count(S.id).label('total_scrobbles'),
            func.min(S.scrobbled_at).label('first_scrobbled_at'),
            func.max(S.scrobbled_at).label('last_scrobbled_at'),
        ]
        if album:
            selections.append(func.count(func.distinct(S.track_name)).label('unique_tracks'))
        rows = await self._rows(select(*selections).where(*conditions))
        return rows[0]

    async def context(self, artist: str, track: str, album: str | None = None):
        # A single session owns all component queries and closes on any failure.
        async with self._get_session() as session:
            return await ListeningRepository(session)._context(artist, track, album)

    async def _context(self, artist: str, track: str, album: str | None):
        track_conditions = (S.artist_name == artist, S.track_name == track)
        track_years = await self._year_counts(track_conditions)
        recent = await self._rows(select(S.scrobbled_at).where(*track_conditions).order_by(
            S.scrobbled_at.desc(), S.id.desc()).limit(5))
        track_context = {
            'name': track, 'artist': artist,
            **await self._listening_span(track_conditions),
            'years': track_years,
            'recent_scrobbles': [row['scrobbled_at'] for row in recent],
        }
        album_context = None
        if album is not None:
            album_conditions = (S.artist_name == artist, S.album_name == album)
            album_context = {
                'name': album, 'artist': artist,
                **await self._listening_span(album_conditions, album=True),
                'top_tracks': await self._ranking(
                    album_conditions, [(S.track_name, 'name')], limit=5),
                'years': await self._year_counts(album_conditions),
            }
        return {'track': track_context, 'album': album_context, 'artist': await self.artist(artist)}
