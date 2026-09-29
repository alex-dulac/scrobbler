"""Local state shared by managed desktop launches."""
import os
from pathlib import Path


def state_directory() -> Path:
    override = os.environ.get("SCROBBLER_STATE_DIR")
    return Path(override) if override else Path.home() / "Library/Application Support/PyScrobbler"
