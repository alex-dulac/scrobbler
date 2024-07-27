from enum import Enum


class Integration(Enum):
    APPLE_MUSIC = 1
    SPOTIFY = 2

    def __str__(self) -> str:
        return self.name.lower()
