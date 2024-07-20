import applescript
from loguru import logger

from model import AppleMusicTrack


"""
Apple Music related methods
"""


async def poll_apple_music() -> AppleMusicTrack | None:
    script = """
    tell application "Music"
        if it is running then
            set currentTrack to the current track
            set trackInfo to (get properties of currentTrack)
            return {trackInfo, player state is playing}
        else
            return {missing value, false}
        end if
    end tell
    """
    try:
        result = applescript.AppleScript(script).run()
        track = result[0]
        playing = result[1]

        if track != applescript.AEType(applescript.kae.cMissingValue):
            return AppleMusicTrack(track_info=track, playing=playing)
        else:
            return None
    except applescript.ScriptError as e:
        if e.number == -1728:
            logger.info("Apple Music is open but no song is selected.")
            return None
        else:
            logger.error(f"Applescript Error: {e}")
            return None


