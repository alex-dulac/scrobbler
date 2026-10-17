import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from library.dependencies import get_scrobbler_runtime
from services.scrobbler_runtime import (
    RuntimeEvent,
    RuntimeEventType,
    ScrobblerRuntime,
)


runtime_router = APIRouter(prefix="/runtime", tags=["runtime"])


def _encode_event(event: RuntimeEvent) -> str:
    payload = json.dumps(
        jsonable_encoder(event),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"id: {event.sequence}\n"
        f"event: {event.type.value}\n"
        f"data: {payload}\n\n"
    )


@runtime_router.get("/events/")
async def stream_runtime_events(
    request: Request,
    last_event_id_header: Annotated[
        str | None,
        Header(alias="Last-Event-ID"),
    ] = None,
    runtime: ScrobblerRuntime = Depends(get_scrobbler_runtime),
) -> StreamingResponse:
    last_event_id: int | None = None
    if last_event_id_header is not None:
        try:
            last_event_id = int(last_event_id_header)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last-Event-ID must be an integer",
            ) from error
        if last_event_id < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last-Event-ID must not be negative",
            )

    try:
        subscription = runtime.subscribe()
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    replay_event = runtime.latest_event

    async def event_stream() -> AsyncIterator[str]:
        last_sent = 0
        try:
            if replay_event is not None:
                if last_event_id != replay_event.sequence:
                    if await request.is_disconnected():
                        return
                    yield _encode_event(replay_event)
                    last_sent = replay_event.sequence
                    if replay_event.type == RuntimeEventType.STOPPED:
                        return
                else:
                    last_sent = last_event_id

            while True:
                if await request.is_disconnected():
                    return

                try:
                    event = await asyncio.wait_for(
                        subscription.queue.get(),
                        timeout=15.0,
                    )
                except TimeoutError:
                    if await request.is_disconnected():
                        return
                    yield ": heartbeat\n\n"
                    continue

                if event.sequence <= last_sent:
                    continue

                yield _encode_event(event)
                last_sent = event.sequence
                if event.type == RuntimeEventType.STOPPED:
                    return
        except asyncio.CancelledError:
            raise
        finally:
            runtime.unsubscribe(subscription.id)

    try:
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except BaseException:
        runtime.unsubscribe(subscription.id)
        raise
