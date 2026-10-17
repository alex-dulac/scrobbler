from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from library.integrations import Integration, PlaybackAction
from models.schemas import Track
from services.scrobbler_engine import (
    EngineUpdate,
    PlaybackResult,
    ScrobbleCommandResult,
    ScrobblerEngine,
    ShutdownResult,
)

if TYPE_CHECKING:
    from library.state import AppState


CommandResult = TypeVar("CommandResult")


class RuntimeState(str, Enum):
    NEW = "new"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class RuntimeEventType(str, Enum):
    TICK = "tick"
    COMMAND = "command"
    POLL_ERROR = "poll_error"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    sequence: int
    type: RuntimeEventType
    emitted_at: datetime
    updates: tuple[EngineUpdate, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeSubscription:
    id: int
    queue: asyncio.Queue[RuntimeEvent]


class ScrobblerRuntime:
    """Runs one scrobbling loop and broadcasts its updates to UI adapters."""

    DEFAULT_SUBSCRIBER_QUEUE_SIZE = 16

    def __init__(
        self,
        engine: ScrobblerEngine,
        *,
        poll_interval_seconds: float = 1.0,
        subscriber_queue_size: int = DEFAULT_SUBSCRIBER_QUEUE_SIZE,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if subscriber_queue_size <= 0:
            raise ValueError("subscriber_queue_size must be greater than zero")

        self._engine = engine
        self._poll_interval_seconds = poll_interval_seconds
        self._subscriber_queue_size = subscriber_queue_size
        self._state = RuntimeState.NEW
        self._lifecycle_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._stop_requested = asyncio.Event()
        self._poll_task: asyncio.Task[None] | None = None
        self._stop_task: asyncio.Task[ShutdownResult] | None = None
        self._command_tasks: set[asyncio.Task] = set()
        self._subscriptions: dict[int, asyncio.Queue[RuntimeEvent]] = {}
        self._next_subscription_id = 1
        self._sequence = 0
        self._latest_event: RuntimeEvent | None = None

    @property
    def engine(self) -> ScrobblerEngine:
        return self._engine

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == RuntimeState.RUNNING

    @property
    def latest_event(self) -> RuntimeEvent | None:
        return self._latest_event

    @property
    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    def snapshot(self) -> AppState:
        return self._engine.state.model_copy(deep=True)

    async def set_integration(self, integration: Integration) -> EngineUpdate:
        self._ensure_accepting_commands()
        return await self._shield_command(self._set_integration(integration))

    async def _set_integration(self, integration: Integration) -> EngineUpdate:
        async with self._operation_lock:
            self._ensure_accepting_commands()
            update = await self._engine.set_integration(integration)
            self._publish(RuntimeEventType.COMMAND, updates=(update,))
            return update

    async def set_scrobbling_enabled(self, enabled: bool) -> EngineUpdate:
        self._ensure_accepting_commands()
        return await self._shield_command(self._set_scrobbling_enabled(enabled))

    async def _set_scrobbling_enabled(self, enabled: bool) -> EngineUpdate:
        async with self._operation_lock:
            self._ensure_accepting_commands()
            update = await self._engine.set_scrobbling_enabled(enabled)
            self._publish(RuntimeEventType.COMMAND, updates=(update,))
            return update

    async def scrobble_current(self) -> ScrobbleCommandResult:
        self._ensure_accepting_commands()
        return await self._shield_command(self._scrobble_current())

    async def _scrobble_current(self) -> ScrobbleCommandResult:
        async with self._operation_lock:
            self._ensure_accepting_commands()
            result = await self._engine.scrobble_current()
            self._publish(
                RuntimeEventType.COMMAND,
                updates=result.updates,
                error=(
                    result.message
                    if result.scrobble is None
                    else None
                ),
            )
            return result

    async def enqueue_manual(self, batch_id: str, tracks: list[Track]) -> int:
        self._ensure_accepting_commands()
        return await self._shield_command(self._enqueue_manual(batch_id, tracks))

    async def _enqueue_manual(self, batch_id: str, tracks: list[Track]) -> int:
        async with self._operation_lock:
            self._ensure_accepting_commands()
            count = await self._engine.enqueue_manual(batch_id, tracks)
            self._publish(RuntimeEventType.COMMAND)
            return count

    async def control_playback(self, action: PlaybackAction) -> PlaybackResult:
        self._ensure_accepting_commands()
        return await self._shield_command(self._control_playback(action))

    async def _control_playback(self, action: PlaybackAction) -> PlaybackResult:
        async with self._operation_lock:
            self._ensure_accepting_commands()
            result = await self._engine.control_playback(action)
            self._publish(
                RuntimeEventType.COMMAND,
                error=result.message if not result.accepted else None,
            )
            return result

    async def start(self) -> None:
        async with self._lifecycle_lock:
            if self.is_running:
                return
            if self._state != RuntimeState.NEW:
                raise RuntimeError(f"Cannot start a {self._state.value} runtime")

            self._stop_requested.clear()
            self._state = RuntimeState.RUNNING
            self._poll_task = asyncio.create_task(
                self._poll_loop(),
                name="py-scrobbler-runtime",
            )

    async def stop(self, *, process_pending: bool = True) -> ShutdownResult:
        if asyncio.current_task() is self._poll_task:
            raise RuntimeError("The polling task cannot stop its own runtime")

        async with self._lifecycle_lock:
            if self._stop_task is None:
                self._state = RuntimeState.STOPPING
                self._stop_requested.set()
                self._stop_task = asyncio.create_task(
                    self._stop(process_pending=process_pending),
                    name="py-scrobbler-runtime-stop",
                )
            stop_task = self._stop_task

        return await asyncio.shield(stop_task)

    def subscribe(self) -> RuntimeSubscription:
        if self._state in {RuntimeState.STOPPING, RuntimeState.STOPPED}:
            raise RuntimeError(f"Cannot subscribe to a {self._state.value} runtime")

        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(
            maxsize=self._subscriber_queue_size,
        )
        subscription_id = self._next_subscription_id
        self._next_subscription_id += 1
        self._subscriptions[subscription_id] = queue
        return RuntimeSubscription(id=subscription_id, queue=queue)

    def unsubscribe(self, subscription_id: int) -> None:
        self._subscriptions.pop(subscription_id, None)

    async def _stop(self, *, process_pending: bool) -> ShutdownResult:
        try:
            if self._poll_task is not None:
                try:
                    await self._poll_task
                except BaseException:
                    pass

            async with self._operation_lock:
                result = await self._engine.shutdown(
                    process_pending=process_pending,
                )
                self._publish(RuntimeEventType.STOPPED)
            return result
        finally:
            self._state = RuntimeState.STOPPED
            self._poll_task = None
            self._subscriptions.clear()

    async def _poll_loop(self) -> None:
        loop = asyncio.get_running_loop()
        next_deadline = loop.time()
        next_pending_retry = next_deadline + 30

        while not self._stop_requested.is_set():
            async with self._operation_lock:
                if self._stop_requested.is_set():
                    break

                try:
                    updates = await self._engine.poll_once()
                    if loop.time() >= next_pending_retry:
                        processed = 0
                        if self._engine.state.scrobble_enabled and self._engine.state.session.pending:
                            processed = await self._engine.process_pending(max_tracks=1)
                        next_pending_retry = loop.time() + (1 if processed else 30)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    self._publish(
                        RuntimeEventType.POLL_ERROR,
                        error=str(error),
                    )
                else:
                    self._publish(
                        RuntimeEventType.TICK,
                        updates=tuple(updates),
                    )

            if self._stop_requested.is_set():
                break

            next_deadline += self._poll_interval_seconds
            now = loop.time()
            if next_deadline <= now:
                missed_intervals = (
                    int((now - next_deadline) // self._poll_interval_seconds) + 1
                )
                next_deadline += missed_intervals * self._poll_interval_seconds

            try:
                await asyncio.wait_for(
                    self._stop_requested.wait(),
                    timeout=next_deadline - loop.time(),
                )
            except TimeoutError:
                pass

    def _ensure_accepting_commands(self) -> None:
        if self._state != RuntimeState.RUNNING:
            raise RuntimeError(
                f"Cannot execute a command on a {self._state.value} runtime"
            )

    async def _shield_command(
        self,
        command: Coroutine[Any, Any, CommandResult],
    ) -> CommandResult:
        task = asyncio.create_task(command, name="py-scrobbler-command")
        self._command_tasks.add(task)
        task.add_done_callback(self._command_finished)
        return await asyncio.shield(task)

    def _command_finished(self, task: asyncio.Task) -> None:
        self._command_tasks.discard(task)
        if not task.cancelled():
            task.exception()

    def _publish(
        self,
        event_type: RuntimeEventType,
        *,
        updates: tuple[EngineUpdate, ...] = (),
        error: str | None = None,
    ) -> RuntimeEvent:
        self._sequence += 1
        event = RuntimeEvent(
            sequence=self._sequence,
            type=event_type,
            emitted_at=datetime.now(UTC),
            updates=updates,
            error=error,
        )
        self._latest_event = event

        for queue in tuple(self._subscriptions.values()):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

        return event
