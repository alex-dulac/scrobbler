import base64

from applescript import AppleScript, AEType, kae, ScriptError
from loguru import logger

from models.mac_os import MacOSSystemInfo
from models.track import AppleMusicTrack
from utils import clean_up_title

"""
Apple Music related methods
"""


async def handle_applescript_error(e: ScriptError) -> None:
    if e.number == -1728:
        logger.info("Apple Music is open but no song is selected.")
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
        result = AppleScript(script).run()
        track = result[0]
        playing = result[1]

        track_exists = isinstance(track, dict) and track != AEType(kae.cMissingValue)
        skip = track_exists and (track.get(AEType(kae.keyAEName)) == 'Connecting…' or not track.get(AEType(b'pArt')))

        if track_exists and not skip:
            apple_music_track = AppleMusicTrack(track, playing)
            apple_music_track.clean_name = clean_up_title(apple_music_track.name)
            apple_music_track.clean_album = clean_up_title(apple_music_track.album)

            return apple_music_track
        else:
            return None
    except ScriptError as e:
        await handle_applescript_error(e)
        return None


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
    except applescript.ScriptError as e:
        await handle_applescript_error(e)


# Apparently, Apple Music does not provide very much information about the user account via applescript
# Getting mac os information as an alternative
async def get_macos_information() -> MacOSSystemInfo | None:
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

        return MacOSSystemInfo(
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


