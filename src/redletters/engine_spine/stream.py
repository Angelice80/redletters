"""SSE streaming endpoint with replay per ADR-003."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, AsyncIterator

from starlette.responses import StreamingResponse

if TYPE_CHECKING:
    from redletters.engine_spine.broadcaster import (
        Connection,
        EventBroadcaster,
        ReplayBuffer,
    )

logger = logging.getLogger(__name__)


async def sse_event_generator(
    broadcaster: "EventBroadcaster",
    replay_buffer: "ReplayBuffer",
    resume_from: int | None = None,
    job_id: str | None = None,
) -> AsyncIterator[str]:
    """Generate SSE events for streaming.

    Implements ADR-003 reconnect semantics:
    1. If resume_from specified, replay missed events from SQLite
    2. Seamlessly transition to live stream after replay
    3. Handle disconnect with cleanup

    Args:
        broadcaster: Event broadcaster for live events
        replay_buffer: Replay buffer for historical events
        resume_from: Sequence number to resume from (Last-Event-ID)
        job_id: Optional filter by job ID

    Yields:
        SSE-formatted event strings
    """
    connection: Connection | None = None

    try:
        # Add connection for live events
        connection = await broadcaster.add_connection()
        logger.debug(f"SSE connection established: {connection.id}")

        # Replay missed events if resuming
        if resume_from is not None:
            logger.debug(f"Replaying events from sequence {resume_from}")
            replay_count = 0
            async for event in replay_buffer.replay_events(resume_from, job_id):
                yield format_sse_event(event)
                replay_count += 1

            if replay_count > 0:
                logger.debug(f"Replayed {replay_count} events")

        # Stream live events
        logger.debug("Switching to live event stream")
        async for event in broadcaster.get_events(connection, timeout=30.0):
            # Filter by job_id if specified
            if job_id and event.get("job_id") != job_id:
                continue

            yield format_sse_event(event)

    except asyncio.CancelledError:
        logger.debug(
            f"SSE connection cancelled: {connection.id if connection else 'unknown'}"
        )
        raise
    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        raise
    finally:
        if connection:
            await broadcaster.remove_connection(connection.id)
            logger.debug(f"SSE connection closed: {connection.id}")


def format_sse_event(event: dict[str, Any]) -> str:
    """Format event as SSE message.

    Format per ADR-003:
        event: <event_type>
        id: <sequence_number>
        data: <json>

    Args:
        event: Event dictionary with event_type, sequence_number, and payload

    Returns:
        SSE-formatted string with trailing newlines
    """
    import json

    event_type = event.get("event_type", "message")
    sequence = event.get("sequence_number", 0)
    data = json.dumps(event, default=str)

    lines = [
        f"event: {event_type}",
        f"id: {sequence}",
        f"data: {data}",
        "",  # Empty line to terminate event
        "",  # Extra newline for good measure
    ]
    return "\n".join(lines)


def create_sse_response(
    broadcaster: "EventBroadcaster",
    replay_buffer: "ReplayBuffer",
    resume_from: int | None = None,
    job_id: str | None = None,
) -> StreamingResponse:
    """Create SSE streaming response.

    Args:
        broadcaster: Event broadcaster
        replay_buffer: Replay buffer for historical events
        resume_from: Sequence to resume from (from Last-Event-ID or query param)
        job_id: Optional job filter

    Returns:
        FastAPI StreamingResponse configured for SSE
    """
    return StreamingResponse(
        sse_event_generator(
            broadcaster,
            replay_buffer,
            resume_from=resume_from,
            job_id=job_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def parse_last_event_id(header_value: str | None) -> int | None:
    """Parse Last-Event-ID header.

    Args:
        header_value: Header value (may be None or non-numeric)

    Returns:
        Sequence number or None
    """
    if header_value is None:
        return None

    try:
        return int(header_value)
    except ValueError:
        logger.warning(f"Invalid Last-Event-ID: {header_value}")
        return None


async def send_retry_directive(seconds: int = 3000) -> str:
    """Send SSE retry directive.

    Tells client how long to wait before reconnecting.

    Args:
        seconds: Retry interval in milliseconds

    Returns:
        SSE retry directive string
    """
    return f"retry: {seconds}\n\n"
