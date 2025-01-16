import re

from loguru import logger

from api.state import AppState
from models.lastfm_models import LastFmAlbum
from models.track import AppleMusicTrack, Track

ALREADY_SCROBBLED = "This song has already been scrobbled."
KEEP_LISTENING = "Keep listening!"
NO_SONG = "No song playing"
NOT_PLAYING = "Current song is not playing."
SCROBBLING_NOT_ENABLED = "Scrobbling is not enabled."


class Comparison:
    def __init__(
            self,
            no_song_playing: bool = False,
            is_same_song: bool = False,
            update_song: bool = False,
            update_song_playing_status: bool = False,
            update_lastfm_now_playing: bool = False,
            update_lastfm_album: bool = False
    ) -> None:
        self.no_song_playing = no_song_playing
        self.is_same_song = is_same_song
        self.update_song = update_song
        self.update_song_playing_status = update_song_playing_status
        self.update_lastfm_now_playing = update_lastfm_now_playing
        self.update_lastfm_album = update_lastfm_album


def song_has_changed(poll: Track | None, current_song: Track | None) -> bool:
    return poll and (not current_song or poll.name != current_song.name)


def is_same_song(poll: Track | None, current_song: Track | None) -> bool:
    return current_song and poll and current_song.name == poll.name


async def poll_comparison(
        poll: Track | None,
        current_song: Track | None,
        lastfm_album: LastFmAlbum | None
) -> Comparison:
    if not poll:
        return Comparison(no_song_playing=True)

    if is_same_song(poll, current_song):
        return Comparison(is_same_song=True)

    update_song = song_has_changed(poll, current_song)

    update_song_playing_status = (
        poll and
        current_song and
        (poll.name, poll.artist == current_song.name, current_song.artist) and
        (poll.playing != current_song.playing)
    )

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
        update_song_playing_status=update_song_playing_status,
        update_lastfm_now_playing=update_lastfm_now_playing,
        update_lastfm_album=update_lastfm_album,
    )


async def validate_scrobble_in_state(state: AppState) -> bool:
    if not state.is_scrobbling:
        logger.info(SCROBBLING_NOT_ENABLED)
        return False

    if not state.current_song:
        logger.info(NO_SONG)
        return False

    if state.current_song.scrobbled:
        logger.info(ALREADY_SCROBBLED)
        return False

    if not state.current_song.playing:
        logger.info(NOT_PLAYING)
        return False

    return True


def clean_up_title(title: str) -> str:
    """
    Clean up the album or song title to get the actual name.
    Examples: High 'N' Dry (Remastered 2018), Time to Break Up (Bonus Track)
    Returns: High 'N' Dry, Time to Break Up

    Args:
        title (str): The title to clean up.

    Returns:
        str: The cleaned up title.
    """

    # Remove substrings in parentheses or brackets containing undesired detail (case-insensitive)...
    clean_title = re.sub(r'[\(\[][^)\]]*remaster[^)\]]*[\)\]]', '', title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\(\[][^)\]]*bonus[^)\]]*[\)\]]', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\(\[][^)\]]*extended[^)\]]*[\)\]]', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\(\[][^)\]]*anniversary[^)\]]*[\)\]]', '', clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\(\[][^)\]]*edit[^)\]]*[\)\]]', '', clean_title, flags=re.IGNORECASE).strip()

    return clean_title
