"""Bounded, read-only queries for the desktop listening library.

Dates follow the existing database's naive datetime convention. Track identity is
artist + title; album metadata does not split a track's listening count.
"""
from datetime import datetime

from sqlalchemy import extract, func, or_, select

from models.db import Scrobble as S
from repositories.base import BaseRepository


class ListeningRepository(BaseRepository):
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

    async def wrapped(self, year: int):
        conditions = (S.scrobbled_at >= datetime(year, 1, 1),
                      S.scrobbled_at < datetime(year + 1, 1, 1))
        known_album = (*conditions, S.album_name.is_not(None), S.album_name != '')
        month = extract('month', S.scrobbled_at).label('month')
        monthly = await self._rows(select(month, func.count(S.id).label('count')).where(
            *conditions).group_by(month).order_by(month))
        counts = {int(row['month']): row['count'] for row in monthly}
        return {
            'year': year,
            'total_scrobbles': await self._count(*conditions),
            'unique_artists': await self._count(*conditions, columns=(S.artist_name,)),
            'unique_albums': await self._count(*known_album, columns=(S.artist_name, S.album_name)),
            'unique_tracks': await self._count(*conditions, columns=(S.artist_name, S.track_name)),
            'monthly': [{'month': value, 'count': counts.get(value, 0)} for value in range(1, 13)],
            'top_artists': await self._ranking(conditions, [(S.artist_name, 'name')]),
            'top_albums': await self._ranking(known_album, [(S.album_name, 'name'), (S.artist_name, 'artist')]),
            'top_tracks': await self._ranking(conditions, [(S.track_name, 'name'), (S.artist_name, 'artist')], album=True),
        }

    async def _year_counts(self, conditions):
        year = extract('year', S.scrobbled_at).label('year')
        years = await self._rows(select(year, func.count(S.id).label('count')).where(
            *conditions).group_by(year).order_by(year))
        return [{'year': int(row['year']), 'count': row['count']} for row in years]

    async def artist(self, artist: str):
        conditions = (S.artist_name == artist,)
        years = await self._year_counts(conditions)
        return {
            'artist': artist,
            'total_scrobbles': await self._count(*conditions),
            'years': years,
            'top_albums': await self._ranking((*conditions, S.album_name.is_not(None), S.album_name != ''), [(S.album_name, 'name')]),
            'top_tracks': await self._ranking(conditions, [(S.track_name, 'name')], album=True),
        }


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
