from pydantic import BaseModel

from models.schemas import Track, Album


class Comparison(BaseModel):
    no_song_playing: bool = False
    is_same_song: bool = False
    update_song: bool = False
    update_song_playing_status: bool = False
    update_lastfm_now_playing: bool = False
    update_lastfm_album: bool = False


def song_has_changed(poll: Track | None, current_song: Track | None) -> bool:
    return poll and (not current_song or poll.name != current_song.name)


def is_same_song(poll: Track | None, current_song: Track | None) -> bool:
    return (current_song
            and poll
            and current_song.name == poll.name
            and poll.artist == current_song.artist)


async def poll_comparison(
        poll: Track | None,
        current_song: Track | None,
        lastfm_album: Album | None = None
) -> Comparison:
    if not poll:
        return Comparison(no_song_playing=True)

    if is_same_song(poll, current_song):
        update_song_playing_status = poll.playing != current_song.playing
        return Comparison(is_same_song=True, update_song_playing_status=update_song_playing_status)

    update_song = song_has_changed(poll, current_song)

    update_lastfm_now_playing = (
            update_song or
            (current_song and current_song.playing and not current_song.lastfm_updated_now_playing)
    )

    update_lastfm_album = (
            update_song or
            (poll and (lastfm_album is None or current_song.album != lastfm_album.title))
    )

    return Comparison(
        update_song=update_song,
        update_lastfm_now_playing=update_lastfm_now_playing,
        update_lastfm_album=update_lastfm_album,
    )
