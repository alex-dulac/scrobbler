/**
  Index changes for an existing scrobbles table; create_all only applies them to
  new databases. CONCURRENTLY avoids blocking scrobble writes, and can't run
  inside a transaction.
 */

-- Library queries filter and sort by time (history, wrapped, years, on this day).
create index concurrently if not exists ix_scrobbles_scrobbled_at on scrobbles (scrobbled_at);

-- Duplicates the primary key index.
drop index concurrently if exists ix_scrobbles_id;

-- History search matches '%term%' across all three columns; trigram indexes let
-- each ILIKE use an index (terms of 3+ characters). Kept out of models/db.py so
-- create_all doesn't depend on the pg_trgm extension being available.
create extension if not exists pg_trgm;
create index concurrently if not exists ix_scrobbles_track_name_trgm on scrobbles using gin (track_name gin_trgm_ops);
create index concurrently if not exists ix_scrobbles_artist_name_trgm on scrobbles using gin (artist_name gin_trgm_ops);
create index concurrently if not exists ix_scrobbles_album_name_trgm on scrobbles using gin (album_name gin_trgm_ops);
