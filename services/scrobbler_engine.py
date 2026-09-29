from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from library.integrations import Integration, PlaybackAction
from models.schemas import LastFmTrack, Track

if TYPE_CHECKING:
    from library.state import AppState


class LastFmClient(Protocol):
    async def update_now_playing(self, current_song: Track) -> bool: ...

    async def scrobble(
        self,
        track: Track,
        scrobbled_at: datetime | None = None,
    ) -> LastFmTrack | None: ...


class ScrobbleRepository(Protocol):
    async def add_scrobble(self, lastfm_track: LastFmTrack) -> None: ...


Poller = Callable[[], Awaitable[Track | None]]
PlaybackController = Callable[[PlaybackAction], Awaitable[bool | None]]
RepositoryFactory = Callable[[], ScrobbleRepository]


class EngineEventType(str, Enum):
    WAITING = "waiting"
    TRACK_CHANGED = "track_changed"
    PLAYBACK_CHANGED = "playback_changed"
    PROGRESS = "progress"
    SCROBBLED = "scrobbled"
    PENDING = "pending"
    INTEGRATION_CHANGED = "integration_changed"
    SCROBBLING_CHANGED = "scrobbling_changed"
    DATABASE_WRITE_FAILED = "database_write_failed"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class EngineUpdate:
    type: EngineEventType
    track: Track | None
    scrobble: LastFmTrack | None = None
    database_saved: bool | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class PlaybackResult:
    accepted: bool
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ScrobbleCommandResult:
    accepted: bool
    scrobble: LastFmTrack | None = None
    updates: tuple[EngineUpdate, ...] = ()
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ShutdownResult:
    pending_processed: int
    pending_remaining: int


class ScrobblerEngine:
    """UI-independent owner of the real-time scrobbling state machine."""

    def __init__(
        self,
        *,
        state: AppState,
        lastfm: LastFmClient,
        pollers: Mapping[Integration, Poller],
        playback_controllers: Mapping[Integration, PlaybackController],
        repository_factory: RepositoryFactory | None = None,
        database_available: bool = False,
    ) -> None:
        self._state = state
        self._lastfm = lastfm
        self._pollers = dict(pollers)
        self._playback_controllers = dict(playback_controllers)
        self._repository_factory = repository_factory
        self._database_available = database_available
        self._lock = asyncio.Lock()

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def database_available(self) -> bool:
        return self._database_available

    def set_database_available(self, available: bool) -> None:
        self._database_available = available

    async def set_integration(self, integration: Integration) -> EngineUpdate:
        if integration not in self._pollers:
            raise ValueError(f"No poller configured for {integration.normalized_name()}")

        async with self._lock:
            self._state.active_integration = integration
            self._state.current_song = None
            self._state.lastfm_album = None
            self._state.spotify_artist_image = None

            return EngineUpdate(
                type=EngineEventType.INTEGRATION_CHANGED,
                track=None,
                message=f"Switched to {integration.normalized_name()}",
            )

    async def set_scrobbling_enabled(self, enabled: bool) -> EngineUpdate:
        async with self._lock:
            self._state.scrobble_enabled = enabled
            return EngineUpdate(
                type=EngineEventType.SCROBBLING_CHANGED,
                track=self._track_snapshot(self._state.current_song),
                message=f"Scrobbling {'enabled' if enabled else 'disabled'}",
            )

    async def scrobble_current(self) -> ScrobbleCommandResult:
        """Explicitly scrobble the current track without waiting for its threshold."""
        async with self._lock:
            track = self._state.current_song
            if not self._state.scrobble_enabled:
                return ScrobbleCommandResult(
                    accepted=False,
                    message="Scrobbling is disabled",
                )
            if track is None:
                return ScrobbleCommandResult(
                    accepted=False,
                    message="No track is currently selected",
                )
            if track.scrobbled:
                return ScrobbleCommandResult(
                    accepted=False,
                    message="The current track has already been scrobbled",
                )
            if not track.playing:
                return ScrobbleCommandResult(
                    accepted=False,
                    message="The current track is not playing",
                )
            if self._state.is_scrobbling:
                return ScrobbleCommandResult(
                    accepted=False,
                    message="A scrobble is already in progress",
                )

            updates = tuple(await self._scrobble(track))
            scrobble = next(
                (
                    update.scrobble
                    for update in updates
                    if update.type == EngineEventType.SCROBBLED
                ),
                None,
            )
            message = next(
                (
                    update.message
                    for update in updates
                    if update.message is not None
                ),
                None,
            )
            return ScrobbleCommandResult(
                accepted=True,
                scrobble=(
                    scrobble.model_copy(deep=True)
                    if scrobble is not None
                    else None
                ),
                updates=updates,
                message=message,
            )

    async def control_playback(self, action: PlaybackAction) -> PlaybackResult:
        controller = self._playback_controllers.get(self._state.active_integration)
        if controller is None:
            return PlaybackResult(
                accepted=False,
                message="Playback control is unavailable for the active integration",
            )

        try:
            result = await controller(action)
        except Exception as error:
            return PlaybackResult(accepted=False, message=str(error))

        if result is False:
            return PlaybackResult(
                accepted=False,
                message="The active integration rejected the playback command",
            )

        return PlaybackResult(accepted=True)

    async def poll_once(self) -> list[EngineUpdate]:
        """Run one serialized poll and advance the scrobbling state once."""
        async with self._lock:
            poller = self._pollers.get(self._state.active_integration)
            if poller is None:
                raise ValueError(
                    f"No poller configured for "
                    f"{self._state.active_integration.normalized_name()}"
                )

            try:
                polled_track = await poller()
            except Exception as error:
                return [
                    EngineUpdate(
                        type=EngineEventType.ERROR,
                        track=self._track_snapshot(self._state.current_song),
                        message=f"Playback poll failed: {error}",
                    )
                ]

            if polled_track is None:
                self._state.current_song = None
                return [EngineUpdate(type=EngineEventType.WAITING, track=None)]

            updates: list[EngineUpdate] = []
            current_track = self._state.current_song

            if not self._same_track(polled_track, current_track):
                polled_track.listening_started_at = datetime.now(UTC)
                polled_track.time_played = 0
                self._state.current_song = polled_track
                self._state.lastfm_album = None
                updates.append(
                    EngineUpdate(
                        type=EngineEventType.TRACK_CHANGED,
                        track=self._track_snapshot(polled_track),
                    )
                )
                updates.extend(await self._update_now_playing(polled_track))
            elif current_track is not None and current_track.playing != polled_track.playing:
                current_track.playing = polled_track.playing
                updates.append(
                    EngineUpdate(
                        type=EngineEventType.PLAYBACK_CHANGED,
                        track=self._track_snapshot(current_track),
                    )
                )

            current_track = self._state.current_song
            if current_track is None:
                return updates

            if (
                self._state.scrobble_enabled
                and current_track.playing
                and not current_track.scrobbled
                and current_track not in self._state.session.pending
                and not self._state.is_scrobbling
            ):
                current_track.time_played += 1
                updates.append(
                    EngineUpdate(
                        type=EngineEventType.PROGRESS,
                        track=self._track_snapshot(current_track),
                    )
                )

                if current_track.is_ready_to_be_scrobbled:
                    updates.extend(await self._scrobble(current_track))

            return updates

    async def process_pending(self) -> int:
        async with self._lock:
            processed = 0
            for track in self._state.session.pending.copy():
                if track.scrobbled:
                    self._state.session.remove_pending(track)
                    continue
                self._state.is_scrobbling = True
                try:
                    scrobbled_track = await self._lastfm.scrobble(track, scrobbled_at=track.listening_started_at)
                    if scrobbled_track is None:
                        continue

                    await self._finalize_scrobble(track, scrobbled_track)
                    processed += 1
                except Exception:
                    continue
                finally:
                    self._state.is_scrobbling = False

            return processed

    async def shutdown(self, *, process_pending: bool = True) -> ShutdownResult:
        processed = await self.process_pending() if process_pending else 0
        return ShutdownResult(
            pending_processed=processed,
            pending_remaining=len(self._state.session.pending),
        )

    async def _update_now_playing(self, track: Track) -> list[EngineUpdate]:
        try:
            track.lastfm_updated_now_playing = await self._lastfm.update_now_playing(track)
        except Exception as error:
            return [
                EngineUpdate(
                    type=EngineEventType.ERROR,
                    track=self._track_snapshot(track),
                    message=f"Last.fm now-playing update failed: {error}",
                )
            ]
        return []

    async def _scrobble(self, track: Track) -> list[EngineUpdate]:
        self._state.session.add_pending(track)
        self._state.is_scrobbling = True
        try:
            scrobbled_track = await self._lastfm.scrobble(track, scrobbled_at=track.listening_started_at)
        except Exception as error:
            self._state.session.add_pending(track)
            return [
                EngineUpdate(
                    type=EngineEventType.PENDING,
                    track=self._track_snapshot(track),
                    message=f"Scrobble failed: {error}",
                )
            ]
        finally:
            self._state.is_scrobbling = False

        if scrobbled_track is None:
            self._state.session.add_pending(track)
            return [
                EngineUpdate(
                    type=EngineEventType.PENDING,
                    track=self._track_snapshot(track),
                    message="Last.fm did not accept the scrobble",
                )
            ]

        database_saved, updates = await self._finalize_scrobble(
            track,
            scrobbled_track,
        )
        updates.insert(
            0,
            EngineUpdate(
                type=EngineEventType.SCROBBLED,
                track=self._track_snapshot(track),
                scrobble=scrobbled_track.model_copy(deep=True),
                database_saved=database_saved,
            ),
        )
        return updates

    async def _finalize_scrobble(
        self,
        source_track: Track,
        scrobbled_track: LastFmTrack,
    ) -> tuple[bool | None, list[EngineUpdate]]:
        source_track.scrobbled = True
        self._state.session.add_scrobble(scrobbled_track)
        self._state.session.remove_pending(source_track)

        if not self._database_available or self._repository_factory is None:
            return None, []

        try:
            repository = self._repository_factory()
            await repository.add_scrobble(scrobbled_track)
        except Exception as error:
            self._database_available = False
            return False, [
                EngineUpdate(
                    type=EngineEventType.DATABASE_WRITE_FAILED,
                    track=self._track_snapshot(source_track),
                    scrobble=scrobbled_track.model_copy(deep=True),
                    database_saved=False,
                    message=str(error),
                )
            ]

        return True, []

    @classmethod
    def _same_track(cls, first: Track | None, second: Track | None) -> bool:
        if first is None or second is None:
            return False
        return cls._track_identity(first) == cls._track_identity(second)

    @staticmethod
    def _track_identity(track: Track) -> tuple[str, ...]:
        persistent_id = getattr(track, "persistent_id", None)
        if persistent_id:
            return ("persistent_id", str(persistent_id))

        source_id = getattr(track, "id", None)
        if source_id:
            return ("source_id", str(source_id))

        def normalize(value: str | None) -> str:
            return (value or "").strip().casefold()

        return (
            "metadata",
            normalize(track.artist),
            normalize(track.clean_name or track.name),
            normalize(track.clean_album or track.album),
        )

    @staticmethod
    def _track_snapshot(track: Track | None) -> Track | None:
        return track.model_copy(deep=True) if track is not None else None
