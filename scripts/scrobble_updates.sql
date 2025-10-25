/**
  A running log of sql statements to clean up various album names,
  ensuring data integrity when viewed in the TUI app.
 */

update scrobbles
set album_name = '...And Out Come the Wolves'
where artist_name = 'Rancid'
and album_name = '...And Out Come The Wolves';

update scrobbles
set album_name = 'Let''s Go'
where artist_name = 'Rancid'
and album_name = 'Let''s Go!';

update scrobbles
set album_name = 'Rancid (5)'
where artist_name = 'Rancid'
and album_name = 'Rancid 2000' or album_name = 'Rancid [5]';

update scrobbles
set album_name = 'Let the Dominoes Fall'
where artist_name = 'Rancid'
and album_name = 'Let The Dominoes Fall (Expanded Version)' or album_name = 'Let The Dominoes Fall';

update scrobbles
set album_name = 'Stand Tall - EP'
where artist_name = 'Such Gold'
and album_name = 'Stand Tall' or album_name = 'Stand Tall EP';

update scrobbles
set album_name = 'All Killer, No Filler'
where artist_name = 'Sum 41'
and album_name = 'All Killer No Filler';

