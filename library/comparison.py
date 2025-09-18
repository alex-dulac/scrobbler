from pydantic import BaseModel

from models.schemas import Track, Album


class Comparison(BaseModel):
    poll: Track | None = None
    current_song: Track | None = None
    lastfm_album: Album | None = None

    @property
    def no_song_playing(self) -> bool:
        return not self.poll

    @property
    def song_has_changed(self) -> bool:
        return self.poll and (not self.current_song or self.poll.name != self.current_song.name)

    @property
    def is_same_song(self) -> bool:
        if not self.poll or not self.current_song:
            return False
        same_title = self.poll.name == self.current_song.name
        same_artist = self.poll.artist == self.current_song.artist
        return same_title and same_artist

    @property
    def update_song_playing_status(self) -> bool:
        return self.is_same_song and self.poll.playing != self.current_song.playing

    @property
    def update_lastfm_now_playing(self):
        playing = self.current_song.playing if self.current_song else False
        already_updated = self.current_song.lastfm_updated_now_playing if self.current_song else False
        return self.song_has_changed or (playing and not already_updated)

    @property
    def update_lastfm_album(self):
        return self.song_has_changed or (self.poll and (self.lastfm_album is None or self.current_song.album != self.lastfm_album.title))

