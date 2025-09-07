import asyncio
from datetime import datetime

from pylast import WSError
from loguru import logger
from pylast import TopItem, Track as PylastTrack
from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

import db.tables as tables
from db.filters import ScrobbleFilter
from db.repository import ScrobbleRepository
from library.utils import lastfm_friendly, clean_up_title
from services.lastfm_service import LastFmService


class SyncService:
    """
    Service to sync data from Last.fm API into the database.
    Db must be provided when triggered from outside an async context manager.
    This has the potential to make a lot of API calls, so be mindful of usage.
    """
    def __init__(self, db: AsyncSession):
        self.lastfm_service = LastFmService()
        self.scrobble_repo = ScrobbleRepository(db)

    async def sync_scrobbles(
            self,
            time_from: str = None,
            time_to: str = None,
            clean: bool = True
    ) -> dict[str, int]:
        fetched = 0
        saved = 0
        time_from = int(datetime.strptime(time_from, "%Y-%m-%d").timestamp()) if time_from else None
        time_to = int(datetime.strptime(time_to, "%Y-%m-%d").timestamp()) if time_to else None

        while True:
            if time_from and time_to and time_from >= time_to:
                logger.info("Reached the specified time_from limit. Stopping sync.")
                break

            tracks = self.lastfm_service.user.get_recent_tracks(
                limit=200, # max allowed by the API
                time_to=time_to
            )

            if not tracks:
                break

            fetched += len(tracks)
            logger.info(f"Fetched {fetched} scrobbles...")

            batch_scrobbles = []

            for t in tracks:
                track_name = await clean_up_title(t.track.title) if clean else t.track.title
                artist_name = t.track.artist.name if t.track.artist else "Unknown Artist"
                album_name = await clean_up_title(t.album) if clean and t.album else t.album
                scrobbled_at = datetime.fromtimestamp(int(t.timestamp))

                existing = await self.scrobble_repo.get_scrobbles(
                    ScrobbleFilter(
                        track_name=track_name,
                        artist_name=artist_name,
                        album_name=album_name,
                        scrobbled_at=scrobbled_at
                    )
                )
                if existing:
                    logger.info(f"Scrobble already exists in DB: {artist_name} - {track_name} at {scrobbled_at}. Skipping.")
                    continue

                scrobble = tables.Scrobble(
                    track_name=track_name,
                    artist_name=artist_name,
                    album_name=album_name,
                    scrobbled_at=scrobbled_at,
                    created_at=datetime.now()
                )
                batch_scrobbles.append(scrobble)

            await self.scrobble_repo.add_and_commit(batch_scrobbles)
            saved += len(batch_scrobbles)

            if len(batch_scrobbles) > 0:
                logger.info(f"Saved {len(batch_scrobbles)} new scrobbles to the database.")
            else:
                logger.info("No new scrobbles to save from this batch.")

            # update time_to to the oldest timestamp from this batch - 1
            oldest = int(tracks[-1].timestamp)
            time_to = oldest - 1

            await asyncio.sleep(0.5)

        logger.info(f"Done. Total fetched: {fetched}. Total saved: {saved}.")
        return {
            "fetched_scrobbles": fetched,
            "new_scrobbles": saved
        }

    async def sync_all_ref_data(self) -> None:
        await self.sync_artists()
        await self.sync_albums()
        await self.sync_tracks()
        logger.info("All data sync complete.")

    async def sync_artists(self, only_missing: bool = True) -> dict[str, int]:
        if only_missing:
            artists = await self.scrobble_repo.get_artists_with_no_ref_data()
        else:
            artists = await self.scrobble_repo.get_artists_from_scrobbles()

        logger.info("Starting all artist data sync...")
        for artist_name in artists:
            await self.sync_artist(artist_name)
            await asyncio.sleep(1) # to respect Last.fm's API

        logger.info("Artist data sync complete.")
        return {"synced_artists": len(artists)}

    async def sync_albums(self, only_missing: bool = True) -> dict[str, int]:
        if only_missing:
            albums = await self.scrobble_repo.get_albums_with_no_ref_data()
        else:
            albums = await self.scrobble_repo.get_albums_from_scrobbles()

        logger.info("Starting all albums data sync...")
        for album in albums:
            await self.sync_album(album)
            await asyncio.sleep(1)

        logger.info("Album data sync complete.")
        return {"synced_albums": len(albums)}

    async def sync_tracks(self, only_missing: bool = True) -> dict[str, int]:
        if only_missing:
            tracks = await self.scrobble_repo.get_tracks_with_no_ref_data()
        else:
            tracks = await self.scrobble_repo.get_tracks_from_scrobbles()

        logger.info("Starting all tracks data sync...")
        for track in tracks:
            await self.sync_track(track)
            await asyncio.sleep(1)

        logger.info("Track data sync complete.")
        return {"synced_tracks": len(tracks)}

    async def sync_artist(self, artist_name: str) -> None:
        to_db = []
        logger.info(f"Syncing artist: {artist_name}")
        lastfm_artist = self.lastfm_service.network.get_artist(
            lastfm_friendly(artist_name)
        )

        mbid = lastfm_artist.get_mbid()
        url = lastfm_artist.get_url()
        bio = lastfm_artist.get_bio_summary()
        user_playcount = lastfm_artist.get_userplaycount()
        listener_count = lastfm_artist.get_listener_count()

        db_artist: tables.Artist = await self.scrobble_repo.get_artist(artist_name)
        if db_artist:
            db_artist.mbid = mbid
            db_artist.url = url
            db_artist.bio = bio
            db_artist.user_playcount = user_playcount
            db_artist.listener_count = listener_count
            logger.info(f"Updating artist in DB: {artist_name}")
        else:
            a = tables.Artist(
                name=artist_name,
                mbid=mbid,
                url=url,
                bio=bio,
                user_playcount=user_playcount,
                listener_count=listener_count,
            )
            to_db.append(a)
            logger.info(f"Adding artist to DB: {artist_name}")

        top_tags: list[TopItem]  = lastfm_artist.get_top_tags()
        for tag in top_tags:
            tag_name = tag.item.name
            weight = int(tag.weight)

            db_artist_tag = await self.scrobble_repo.check_artist_tag(artist_name=artist_name, tag=tag_name)
            if db_artist_tag:
                db_artist_tag.weight = weight
                # logger.info(f"Updating artist tag in DB: {tag_name} for artist {artist_name}")
            else:
                at = tables.ArtistTag(
                    artist_name=artist_name,
                    tag=tag_name,
                    weight=weight,
                )
                to_db.append(at)
                # logger.info(f"Adding artist tag to DB: {tag_name} for artist {artist_name}")

        similar = lastfm_artist.get_similar(limit=20)
        for s in similar:
            s_artist = s.item
            s_name = s_artist.name
            match = s.match

            db_similar_artist = await self.scrobble_repo.check_similar_artist(artist_name=artist_name, similar_artist_name=s_name)

            if db_similar_artist:
                # match is the only field to update
                db_similar_artist.match = match
                # logger.info(f"Updating similar artist in DB: {s_name} for artist {artist_name}")
            else:
                sa = tables.SimilarArtist(
                    artist_name=artist_name,
                    similar_artist_name=s_name,
                    match=match,
                )
                to_db.append(sa)
                # logger.info(f"Adding similar artist to DB: {s_name} for artist {artist_name}")

        top_tracks: list[TopItem] = lastfm_artist.get_top_tracks(limit=20)
        top_tracks.sort(key=lambda x: x.weight , reverse=True)
        for rank, t in enumerate(top_tracks, start=1):
            weight = int(t.weight)
            track = t.item
            title = track.title

            db_top_track = await self.scrobble_repo.check_artist_top_track(artist_name=artist_name, track_name=title)
            if db_top_track:
                db_top_track.weight = weight
                db_top_track.rank = rank
                # logger.info(f"Updating top track in DB: {title} for artist {artist_name}")
            else:
                att = tables.ArtistTopTrack(
                    artist_name=artist_name,
                    track_name=title,
                    weight=weight,
                    rank=rank
                )
                to_db.append(att)
                # logger.info(f"Adding top track to DB: {track.title} for artist {artist_name}")

        top_albums: list[TopItem] = lastfm_artist.get_top_albums(limit=20)
        top_albums.sort(key=lambda x: x.weight, reverse=True)
        for rank, a in enumerate(top_albums, start=1):
            weight = int(a.weight)
            album = a.item
            title = album.title

            db_top_album = await self.scrobble_repo.check_artist_top_album(artist_name=artist_name, album_name=title)
            if db_top_album:
                db_top_album.weight = weight
                db_top_album.rank = rank
                # logger.info(f"Updating top album in DB: {title} for artist {artist_name}")
            else:
                ata = tables.ArtistTopAlbum(
                    artist_name=artist_name,
                    album_name=title,
                    weight=weight,
                    rank=rank
                )
                to_db.append(ata)
                # logger.info(f"Adding top album to DB: {album.title} for artist {artist_name}")

        await self.scrobble_repo.add_and_commit(to_db)
        logger.info(f"Artist data sync complete for {artist_name}.")

    async def sync_album(self, album: Row[tuple[str, str]]) -> None:
        to_db = []
        logger.info(f"Syncing album: {album}")
        title = album[0]
        artist = album[1]

        if not artist or not title:
            logger.warning(f"Skipping album with missing artist or title: {album}")
            return

        lastfm_album = self.lastfm_service.network.get_album(
            artist=lastfm_friendly(artist),
            title=lastfm_friendly(title)
        )

        if not lastfm_album:
            logger.warning(f"Album not found on Last.fm: {artist} - {title}")
            return

        # Sniff out edge case occurrence where lastfm_album is returned but cannot be found when fetching details
        try:
            lastfm_album.get_mbid()
        except WSError as e:
            logger.warning(f"Error fetching album details from Last.fm for {artist} - {title}: {e}")
            return

        mbid = lastfm_album.get_mbid()
        url = lastfm_album.get_url()
        wiki = lastfm_album.get_wiki_summary()
        cover_image = lastfm_album.get_cover_image()
        user_playcount = lastfm_album.get_userplaycount()
        listener_count = lastfm_album.get_listener_count()

        db_album: tables.Album = await self.scrobble_repo.get_album(album_name=title, artist_name=artist)
        if db_album:
            db_album.mbid = mbid
            db_album.url = url
            db_album.wiki = wiki
            db_album.cover_image = cover_image
            db_album.user_playcount = user_playcount
            db_album.listener_count = listener_count
            logger.info(f"Updating album in DB: {artist}")
        else:
            a = tables.Album(
                title=title,
                artist_name=artist,
                mbid=mbid,
                url=url,
                wiki=wiki,
                cover_image=cover_image,
                user_playcount=user_playcount,
                listener_count=listener_count,
            )
            to_db.append(a)
            logger.info(f"Adding album to DB: {title}")

        top_tags: list[TopItem] = lastfm_album.get_top_tags()
        for tag in top_tags:
            tag_name = tag.item.name
            weight = int(tag.weight)

            db_album_tag = await self.scrobble_repo.check_album_tag(album_name=title, tag=tag_name, artist_name=artist)
            if db_album_tag:
                db_album_tag.weight = weight
                # logger.info(f"Updating album tag in DB: {tag_name} for album {title}")
            else:
                at = tables.AlbumTag(
                    album_name=title,
                    artist_name=artist,
                    tag=tag_name,
                    weight=weight,
                )
                to_db.append(at)
                # logger.info(f"Adding album tag to DB: {tag_name} for album {title}")

        album_tracks: list[PylastTrack] = lastfm_album.get_tracks()
        for order, track in enumerate(album_tracks, start=1):
            track_title = track.title

            db_album_track: tables.AlbumTrack = await self.scrobble_repo.check_album_track(album_name=title, track_name=track_title)
            if db_album_track:
                db_album_track.order = order
                # logger.info(f"Updating track in DB: {track_title} for album {title}")
            else:
                at = tables.AlbumTrack(
                    album_name=title,
                    track_name=track_title,
                    artist_name=artist,
                    order=order
                )
                to_db.append(at)
                # logger.info(f"Adding track to DB: {track_title} for album {title} by {artist}")

        await self.scrobble_repo.add_and_commit(to_db)
        logger.info(f"Album data sync complete for {title} by {artist}.")

    async def sync_track(self, track: Row[tuple[str, str]]) -> None:
        to_db = []
        title = track[0]
        artist = track[1]
        lastfm_track = self.lastfm_service.network.get_track(
            artist=lastfm_friendly(artist),
            title=lastfm_friendly(title)
        )

        mbid = lastfm_track.get_mbid()
        url = lastfm_track.get_url()
        wiki = lastfm_track.get_wiki_summary()
        duration = lastfm_track.get_duration()
        cover_image = lastfm_track.get_cover_image()
        user_loved = lastfm_track.get_userloved()
        user_playcount = lastfm_track.get_userplaycount()
        listener_count = lastfm_track.get_listener_count()
        listener_playcount = lastfm_track.get_playcount()

        db_track: tables.Track = await self.scrobble_repo.get_track(track_name=title, artist_name=artist)
        if db_track:
            db_track.mbid = mbid
            db_track.url = url
            db_track.wiki = wiki
            db_track.duration = duration
            db_track.cover_image = cover_image
            db_track.user_loved = user_loved
            db_track.user_playcount = user_playcount
            db_track.listener_count = listener_count
            db_track.listener_playcount = listener_playcount
            logger.info(f"Updating track in DB: {artist}")
        else:
            t = tables.Track(
                title=title,
                artist_name=artist,
                mbid=mbid,
                url=url,
                wiki=wiki,
                cover_image=cover_image,
                user_loved=user_loved,
                user_playcount=user_playcount,
                listener_count=listener_count,
                listener_playcount=listener_playcount,
            )
            to_db.append(t)
            logger.info(f"Adding track to DB: {title}")

        similar_tracks = lastfm_track.get_similar(limit=20)
        for s in similar_tracks:
            s_track = s.item
            s_name = s_track.title
            s_artist_name = s_track.artist.name
            match = s.match

            db_similar_track = await self.scrobble_repo.check_similar_track(
                track_name=title,
                artist_name=artist,
                similar_track_name=s_name,
                similar_track_artist_name=s_artist_name
            )

            if db_similar_track:
                db_similar_track.match = match
                # logger.info(f"Updating similar track in DB: {s_name} for track {title}")
            else:
                st = tables.SimilarTrack(
                    track_name=title,
                    artist_name=artist,
                    similar_track_name=s_name,
                    similar_track_artist_name=s_artist_name,
                    match=match,
                )
                to_db.append(st)
                # logger.info(f"Adding similar track to DB: {s_name} for track {title}")

        await self.scrobble_repo.add_and_commit(to_db)
        logger.info(f"Track data sync complete for {title} by {artist}.")


