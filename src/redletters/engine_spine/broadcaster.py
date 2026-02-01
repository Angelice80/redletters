"""SSE event broadcaster implementing persist-before-send per ADR-003.

CRITICAL: The broadcaster ONLY accepts persisted event row IDs.
It does NOT accept raw event objects. This mechanically enforces
persist-before-send.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from redletters.engine_spine.database import EngineDatabase
    from redletters.engine_spine.models import EventRowId

logger = logging.getLogger(__name__)

# Ring buffer size per connection
MAX_BUFFER_SIZE = 10_000


@dataclass
class Connection:
    """Active SSE connection."""

    id: str
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=MAX_BUFFER_SIZE)
    )
    last_sequence: int = 0
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    is_closed: bool = False


class EventBroadcaster:
    """Broadcasts persisted events to SSE connections.

    Thread-safe. Implements ring buffer per connection with disconnect
    on overflow (clients can replay from SQLite).
    """

    def __init__(self, db: "EngineDatabase"):
        self._db = db
        self._connections: dict[str, Connection] = {}
        self._lock = asyncio.Lock()
        self._connection_counter = 0

    async def add_connection(self, connection_id: str | None = None) -> Connection:
        """Add a new SSE connection.

        Args:
            connection_id: Optional ID, generated if not provided

        Returns:
            Connection object for receiving events
        """
        async with self._lock:
            if connection_id is None:
                self._connection_counter += 1
                connection_id = f"conn_{self._connection_counter}"

            conn = Connection(id=connection_id)
            self._connections[connection_id] = conn
            logger.debug(f"Added connection: {connection_id}")
            return conn

    async def remove_connection(self, connection_id: str) -> None:
        """Remove an SSE connection."""
        async with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].is_closed = True
                del self._connections[connection_id]
                logger.debug(f"Removed connection: {connection_id}")

    async def broadcast_by_id(self, event_id: "EventRowId") -> int:
        """Broadcast a persisted event to all connections.

        This is the ONLY way to send events. The event must already
        be persisted to the database.

        Args:
            event_id: Row ID from job_events table (not raw event!)

        Returns:
            Number of connections that received the event

        Raises:
            ValueError: If event_id is not found in database
        """
        # Fetch the persisted event
        event_data = self._db.get_event_by_id(event_id)
        if event_data is None:
            raise ValueError(f"Event {event_id} not found in database")

        event = event_data["event"]
        sequence = event_data["sequence"]

        # Broadcast to all connections
        delivered = 0
        to_disconnect = []

        async with self._lock:
            for conn_id, conn in self._connections.items():
                if conn.is_closed:
                    continue

                try:
                    # Non-blocking put with timeout
                    conn.queue.put_nowait(event)
                    conn.last_sequence = sequence
                    delivered += 1
                except asyncio.QueueFull:
                    # Ring buffer overflow - mark for disconnect
                    logger.warning(f"Connection {conn_id} buffer full, disconnecting")
                    to_disconnect.append(conn_id)

        # Disconnect overflowed connections outside lock
        for conn_id in to_disconnect:
            await self.remove_connection(conn_id)

        return delivered

    async def send_to_connection(
        self,
        connection_id: str,
        event_id: "EventRowId",
    ) -> bool:
        """Send a persisted event to a specific connection.

        Args:
            connection_id: Target connection
            event_id: Persisted event row ID

        Returns:
            True if sent, False if connection not found or closed
        """
        event_data = self._db.get_event_by_id(event_id)
        if event_data is None:
            raise ValueError(f"Event {event_id} not found")

        async with self._lock:
            conn = self._connections.get(connection_id)
            if conn is None or conn.is_closed:
                return False

            try:
                conn.queue.put_nowait(event_data["event"])
                conn.last_sequence = event_data["sequence"]
                return True
            except asyncio.QueueFull:
                # Mark for disconnect but don't disconnect during iteration
                conn.is_closed = True
                return False

    async def get_events(
        self,
        connection: Connection,
        timeout: float = 30.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Async iterator for connection events.

        Args:
            connection: Connection object
            timeout: Timeout for waiting on events

        Yields:
            Event dictionaries
        """
        while not connection.is_closed:
            try:
                event = await asyncio.wait_for(
                    connection.queue.get(),
                    timeout=timeout,
                )
                yield event
            except asyncio.TimeoutError:
                # Yield None to allow timeout handling
                continue
            except asyncio.CancelledError:
                break

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)

    def get_connection_stats(self) -> dict[str, Any]:
        """Get statistics about connections."""
        return {
            "active_connections": len(self._connections),
            "connections": [
                {
                    "id": conn.id,
                    "last_sequence": conn.last_sequence,
                    "queue_size": conn.queue.qsize(),
                }
                for conn in self._connections.values()
            ],
        }


class ReplayBuffer:
    """Manages event replay for reconnecting clients."""

    def __init__(self, db: "EngineDatabase", chunk_size: int = 1000):
        self._db = db
        self._chunk_size = chunk_size

    async def replay_events(
        self,
        after_sequence: int,
        job_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay events from database.

        Yields events in chunks for memory efficiency.

        Args:
            after_sequence: Resume from this sequence number
            job_id: Optional filter by job

        Yields:
            Event dictionaries
        """
        offset = after_sequence
        total_replayed = 0

        while True:
            events = self._db.get_events_since(
                offset,
                job_id=job_id,
                limit=self._chunk_size,
            )

            if not events:
                break

            for event_data in events:
                yield event_data["event"]
                offset = event_data["sequence"]
                total_replayed += 1

            # If we got less than chunk_size, we're done
            if len(events) < self._chunk_size:
                break

        logger.debug(f"Replayed {total_replayed} events from sequence {after_sequence}")

    def get_max_sequence(self) -> int:
        """Get current maximum sequence number."""
        return self._db.get_current_sequence()
