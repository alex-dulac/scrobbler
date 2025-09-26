import asyncio
import base64

from applescript import AppleScript, AEType, kae, ScriptError
from loguru import logger

from library.integrations import PlaybackAction
from library.utils import clean_up_title
from models.schemas import AppleMusicTrack, MacOS

"""
Apple Music related methods
"""


async def handle_applescript_error(e: ScriptError) -> None:
    if e.number == -1728:
        # logger.info("Apple Music is open but no song is selected.")
        return None
    elif e.number == -609:
        logger.info("Connection is invalid.")
        return None
    else:
        logger.error(f"Applescript Error: {e}")
        return None


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
        result = await asyncio.wait_for(
            asyncio.to_thread(AppleScript(script).run),
            timeout=3  # seconds
        )
        track = result[0]
        playing = result[1]

        track_exists = isinstance(track, dict) and track != AEType(kae.cMissingValue)
        skip = track_exists and (track.get(AEType(kae.keyAEName)) == 'Connecting…' or not track.get(AEType(b'pArt')))

        if track_exists and not skip:
            apple_music_track = AppleMusicTrack.from_apple_event(track, playing)
            apple_music_track.clean_name = await clean_up_title(apple_music_track.name)
            apple_music_track.clean_album = await clean_up_title(apple_music_track.album)

            return apple_music_track
        else:
            return None
    except asyncio.TimeoutError:
        logger.error("AppleScript execution timed out.")
        return None
    except ScriptError as e:
        await handle_applescript_error(e)
        return None


async def playback_control(action: PlaybackAction) -> bool:
    """
    Control Apple Music playback.
    """
    applescript_command = None
    match action:
        case PlaybackAction.PAUSE:
            applescript_command = "playpause"
        case PlaybackAction.NEXT:
            applescript_command = "next track"
        case PlaybackAction.PREVIOUS:
            applescript_command = "previous track"
        case _:
            raise ValueError(f"Invalid playback action: {action}")

    if applescript_command is None:
        return False

    script = f"""
    tell application "Music"
        if it is running then
            {applescript_command}
            return true
        else
            return false
        end if
    end tell
    """
    try:
        result = AppleScript(script).run()
        return result
    except ScriptError as e:
        await handle_applescript_error(e)
        return False


async def set_volume(volume: int) -> bool:
    """
    Set the volume of Apple Music.
    :param volume: Integer between 0 and 100
    :return: True if successful, False otherwise
    """
    script = f"""
    tell application "Music"
        if it is running then
            set sound volume to {volume}
            return true
        else
            return false
        end if
    end tell
    """
    try:
        result = AppleScript(script).run()
        return result
    except ScriptError as e:
        await handle_applescript_error(e)
        return False


async def get_volume() -> int:
    """
    Get the current volume of Apple Music.
    :return: Volume as an integer between 0 and 100, or -1 if an error occurred
    """
    script = """
    tell application "Music"
        if it is running then
            return sound volume
        else
            return -1
        end if
    end tell
    """
    try:
        result = AppleScript(script).run()
        return result
    except ScriptError as e:
        await handle_applescript_error(e)
        return -1


async def get_current_track_artwork_data() -> str | None:
    script = """
    tell application "Music"
        if it is running then
            set currentTrack to the current track
            set albumArtwork to artwork 1 of currentTrack
            set artworkData to data of albumArtwork
            return {artworkData}
        else
            return {missing value}
        end if
    end tell
    """
    try:
        result = AppleScript(script).run()
        artwork_data = result[0]

        if artwork_data:
            artwork_bytes = artwork_data.data()
            return base64.b64encode(artwork_bytes).decode('utf-8')
        else:
            return None
    except ScriptError as e:
        await handle_applescript_error(e)


# Apparently, Apple Music does not provide very much information about the user account via applescript
# Getting macOS information as an alternative
async def get_macos_information() -> MacOS | None:
    script = """
    set sysInfo to system info

    set userName to short user name of sysInfo
    set longUserName to long user name of sysInfo
    set userID to user id of sysInfo
    set homeDir to home directory of sysInfo
    set bootVolume to boot volume of sysInfo
    set systemVersion to system version of sysInfo
    set cpuType to cpu type of sysInfo
    set physicalMemory to physical memory of sysInfo
    set userLocale to user locale of sysInfo

    return {userName, longUserName, userID, homeDir, bootVolume, systemVersion, cpuType, physicalMemory, userLocale}
    """

    try:
        result = AppleScript(script).run()

        return MacOS(
            user_name=result[0],
            long_user_name=result[1],
            user_id=result[2],
            home_dir=result[3],
            boot_volume=result[4],
            system_version=result[5],
            cpu_type=result[6],
            physical_memory=result[7],
            user_locale=result[8]
        )
    except ScriptError as e:
        await handle_applescript_error(e)


