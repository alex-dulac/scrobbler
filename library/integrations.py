from enum import Enum, EnumType


class Integration(Enum):
    APPLE_MUSIC = 1
    SPOTIFY = 2

    def __str__(self) -> str:
        return self.name.lower()

    def normalized_name(self) -> str:
        names = {
            Integration.APPLE_MUSIC: 'Apple Music',
            Integration.SPOTIFY: 'Spotify'
        }
        return names.get(self, self.name)


class PlaybackAction(EnumType):
    PAUSE = 'pause'
    NEXT = 'next'
    PREVIOUS = 'previous'
    SEEK = 'seek'
