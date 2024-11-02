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


async def poll_comparison(
        poll: Track,
        current_song: Track | None,
        lastfm_album: LastFmAlbum | None
) -> dict[str, bool]:
    update_song = (
        poll and
        (current_song is None or poll.name != current_song.name)
    )

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

    return {
        "update_song": update_song,
        "update_song_playing_status": update_song_playing_status,
        "update_lastfm_now_playing": update_lastfm_now_playing,
        "update_lastfm_album": update_lastfm_album,
    }


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


async def validate_scrobble_in_loop(
        current_song: AppleMusicTrack | None,
        previous_song: AppleMusicTrack | None
) -> bool:
    if not current_song:
        logger.info(NO_SONG)
        return False

    if not current_song.time_played > 60:
        logger.info(KEEP_LISTENING)
        logger.info(f"Time played: {current_song.time_played}")
        return False

    if current_song.scrobbled:
        logger.info(ALREADY_SCROBBLED)
        return False

    if not current_song.playing:
        logger.info(NOT_PLAYING)
        return False

    if previous_song and previous_song.id == current_song.id:
        logger.info("This might not happen but if it does I want to see it.")
        return False

    return True


async def clean_up_title(title: str) -> str:
    """
    Clean up the album or song title to get the actual name.
    Examples: High 'N' Dry (Remastered 2018), Time to Break Up (Bonus Track)
    Returns: High 'N' Dry, Time to Break Up

    Args:
        title (str): The title to clean up.

    Returns:
        str: The cleaned up title.
    """

    # Remove substrings in parentheses or brackets containing 'remastered' or 'bonus' (case-insensitive)
    clean_title = re.sub(r'[\(\[][^)\]]*remastered[^)\]]*[\)\]]', '', title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'[\(\[][^)\]]*bonus[^)\]]*[\)\]]', '', clean_title, flags=re.IGNORECASE).strip()

    return clean_title
