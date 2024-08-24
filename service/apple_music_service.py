import base64

import applescript
from loguru import logger

from models.mac_os import MacOSSystemInfo
from models.track import AppleMusicTrack

"""
Apple Music related methods
"""


async def handle_applescript_error(e: applescript.ScriptError) -> None:
    if e.number == -1728:
        logger.info("Apple Music is open but no song is selected.")
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
        result = applescript.AppleScript(script).run()
        track = result[0]
        playing = result[1]

        if track != applescript.AEType(applescript.kae.cMissingValue):
            return AppleMusicTrack(track_info=track, playing=playing)
        else:
            return None
    except applescript.ScriptError as e:
        await handle_applescript_error(e)


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
        result = applescript.AppleScript(script).run()
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
        result = applescript.AppleScript(script).run()

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
    except applescript.ScriptError as e:
        await handle_applescript_error(e)


