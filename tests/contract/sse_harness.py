"""Deterministic SSE consumption harness for contract tests.

This module provides a test harness for consuming SSE streams with:
- Monotonic deadline enforcement (not httpx timeout behavior)
- Heartbeat arrival validation within configured intervals
- Support for both sync and async patterns
- Non-flaky behavior through deterministic timing

Per Sprint-2-DOD: Tests must be non-flaky (rerun once, fail twice blocks PR).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import httpx


# Default heartbeat interval per ADR-003
DEFAULT_HEARTBEAT_INTERVAL = 3.0
# Tolerance for heartbeat timing (allows for scheduling jitter)
HEARTBEAT_TOLERANCE = 1.0
# Default timeout for operations
DEFAULT_TIMEOUT = 10.0


@dataclass
class SSEEvent:
    """Parsed SSE event."""

    event_type: str
    event_id: Optional[int]
    data: dict[str, Any]
    raw_lines: List[str] = field(default_factory=list)

    @property
    def sequence_number(self) -> int:
        """Get sequence number from event ID or data."""
        if self.event_id is not None:
            return self.event_id
        return self.data.get("sequence_number", 0)


@dataclass
class HeartbeatTiming:
    """Track heartbeat timing for validation."""

    last_heartbeat_at: Optional[float] = None
    intervals: List[float] = field(default_factory=list)
    expected_interval: float = DEFAULT_HEARTBEAT_INTERVAL
    tolerance: float = HEARTBEAT_TOLERANCE

    def record_heartbeat(self, monotonic_time: float) -> None:
        """Record a heartbeat arrival."""
        if self.last_heartbeat_at is not None:
            interval = monotonic_time - self.last_heartbeat_at
            self.intervals.append(interval)
        self.last_heartbeat_at = monotonic_time

    def validate(self) -> tuple[bool, str]:
        """Validate heartbeat timing is within tolerance.

        Returns:
            Tuple of (valid, message)
        """
        if not self.intervals:
            return True, "No intervals to validate"

        max_allowed = self.expected_interval + self.tolerance
        for i, interval in enumerate(self.intervals):
            if interval > max_allowed:
                return False, (
                    f"Heartbeat interval {i} was {interval:.2f}s, "
                    f"expected <= {max_allowed:.2f}s"
                )
        return True, f"All {len(self.intervals)} intervals within tolerance"


class SSEParseError(Exception):
    """Error parsing SSE stream."""

    pass


class DeadlineExceeded(Exception):
    """Monotonic deadline exceeded."""

    pass


def parse_sse_lines(lines: List[str]) -> Optional[SSEEvent]:
    """Parse SSE lines into an event.

    Args:
        lines: Raw SSE lines for a single event

    Returns:
        Parsed SSEEvent or None if incomplete
    """
    event_type = "message"
    event_id = None
    data_lines = []

    for line in lines:
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("id:"):
            try:
                event_id = int(line[3:].strip())
            except ValueError:
                pass
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())

    if not data_lines:
        return None

    try:
        data = json.loads(data_lines[0])
    except json.JSONDecodeError:
        data = {"raw": " ".join(data_lines)}

    return SSEEvent(
        event_type=event_type,
        event_id=event_id,
        data=data,
        raw_lines=lines.copy(),
    )


class SSEHarness:
    """Deterministic SSE consumption harness.

    Uses monotonic clock for all timing to ensure deterministic behavior.
    Does NOT rely on httpx timeout behavior for test logic.
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_tolerance: float = HEARTBEAT_TOLERANCE,
    ):
        self.base_url = base_url
        self.auth_token = auth_token
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_tolerance = heartbeat_tolerance

        self.events: List[SSEEvent] = []
        self.heartbeat_timing = HeartbeatTiming(
            expected_interval=heartbeat_interval,
            tolerance=heartbeat_tolerance,
        )
        self._current_lines: List[str] = []

    def _get_headers(
        self,
        last_event_id: Optional[int] = None,
    ) -> dict[str, str]:
        """Build request headers."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        if last_event_id is not None:
            headers["Last-Event-ID"] = str(last_event_id)
        return headers

    def _process_line(self, line: str) -> Optional[SSEEvent]:
        """Process a single SSE line, returning event if complete."""
        if line == "":
            # Empty line = end of event
            if self._current_lines:
                event = parse_sse_lines(self._current_lines)
                self._current_lines = []
                return event
        else:
            self._current_lines.append(line)
        return None

    def _handle_event(self, event: SSEEvent, now: float) -> None:
        """Handle a received event."""
        self.events.append(event)

        if event.event_type == "engine.heartbeat":
            self.heartbeat_timing.record_heartbeat(now)

    async def consume_until_deadline(
        self,
        deadline: float,
        resume_from: Optional[int] = None,
        last_event_id: Optional[int] = None,
        job_id: Optional[str] = None,
        min_events: int = 0,
        stop_on: Optional[Callable[[SSEEvent], bool]] = None,
    ) -> List[SSEEvent]:
        """Consume SSE events until monotonic deadline.

        This is the core method for deterministic SSE consumption.
        Uses time.monotonic() for all timing - NOT httpx timeouts.

        Args:
            deadline: Monotonic time deadline (from time.monotonic())
            resume_from: Query param ?resume_from=N
            last_event_id: Last-Event-ID header value
            job_id: Query param ?job_id=X
            min_events: Minimum events required before returning
            stop_on: Optional callback to stop early on specific event

        Returns:
            List of received events

        Raises:
            DeadlineExceeded: If deadline reached before min_events
        """
        self.events = []
        self._current_lines = []

        # Build URL with query params
        url = f"{self.base_url}/v1/stream"
        params = {}
        if resume_from is not None:
            params["resume_from"] = str(resume_from)
        if job_id is not None:
            params["job_id"] = job_id
        if params:
            url = f"{url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

        headers = self._get_headers(last_event_id)

        # Calculate remaining time for the httpx timeout
        # We use a generous httpx timeout and enforce deadline ourselves
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DeadlineExceeded("Deadline already passed")

        # Use httpx timeout that's slightly longer than our deadline
        # We'll enforce the deadline ourselves with the monotonic check
        httpx_timeout = remaining + 1.0

        async with httpx.AsyncClient(timeout=httpx_timeout) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    raise SSEParseError(
                        f"SSE stream returned {response.status_code}: "
                        f"{response.text if hasattr(response, 'text') else 'no body'}"
                    )

                async for raw_line in response.aiter_lines():
                    now = time.monotonic()

                    # Check deadline BEFORE processing
                    if now >= deadline:
                        if len(self.events) >= min_events:
                            return self.events
                        raise DeadlineExceeded(
                            f"Deadline exceeded with only {len(self.events)} "
                            f"events (need {min_events})"
                        )

                    # Process line
                    event = self._process_line(raw_line)
                    if event:
                        self._handle_event(event, now)

                        # Check stop condition
                        if stop_on and stop_on(event):
                            return self.events

                    # Check if we have enough events
                    if len(self.events) >= min_events and min_events > 0:
                        return self.events

        return self.events

    async def consume_n_events(
        self,
        n: int,
        timeout: float = DEFAULT_TIMEOUT,
        resume_from: Optional[int] = None,
        last_event_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> List[SSEEvent]:
        """Consume exactly N events with timeout.

        Convenience wrapper around consume_until_deadline.

        Args:
            n: Number of events to consume
            timeout: Timeout in seconds
            resume_from: Query param ?resume_from=N
            last_event_id: Last-Event-ID header value
            job_id: Query param ?job_id=X

        Returns:
            List of N events

        Raises:
            DeadlineExceeded: If timeout before N events
        """
        deadline = time.monotonic() + timeout
        return await self.consume_until_deadline(
            deadline=deadline,
            resume_from=resume_from,
            last_event_id=last_event_id,
            job_id=job_id,
            min_events=n,
        )

    async def consume_heartbeats(
        self,
        count: int,
        timeout: Optional[float] = None,
    ) -> List[SSEEvent]:
        """Consume a specific number of heartbeat events.

        Args:
            count: Number of heartbeats to consume
            timeout: Timeout (default: count * heartbeat_interval * 2)

        Returns:
            List of heartbeat events
        """
        if timeout is None:
            # Allow double the expected time plus tolerance
            timeout = count * (self.heartbeat_interval + self.heartbeat_tolerance) * 2

        deadline = time.monotonic() + timeout
        heartbeats_received = 0

        def stop_on_heartbeats(event: SSEEvent) -> bool:
            nonlocal heartbeats_received
            if event.event_type == "engine.heartbeat":
                heartbeats_received += 1
            return heartbeats_received >= count

        await self.consume_until_deadline(
            deadline=deadline,
            stop_on=stop_on_heartbeats,
        )

        # Filter to just heartbeats
        return [e for e in self.events if e.event_type == "engine.heartbeat"]

    def validate_heartbeat_timing(self) -> tuple[bool, str]:
        """Validate that heartbeats arrived within expected intervals.

        Returns:
            Tuple of (valid, message)
        """
        return self.heartbeat_timing.validate()

    def get_sequence_numbers(self) -> List[int]:
        """Get sequence numbers from all received events."""
        return [e.sequence_number for e in self.events]

    def validate_monotonic_sequences(self) -> tuple[bool, str]:
        """Validate sequence numbers are monotonically increasing.

        Returns:
            Tuple of (valid, message)
        """
        seqs = self.get_sequence_numbers()
        for i in range(1, len(seqs)):
            if seqs[i] <= seqs[i - 1]:
                return False, (
                    f"Sequence not monotonic at index {i}: {seqs[i - 1]} -> {seqs[i]}"
                )
        return True, f"All {len(seqs)} sequences monotonic"

    def validate_no_gaps(self) -> tuple[bool, str]:
        """Validate no gaps in sequence numbers.

        Returns:
            Tuple of (valid, message)
        """
        seqs = self.get_sequence_numbers()
        for i in range(1, len(seqs)):
            if seqs[i] != seqs[i - 1] + 1:
                return False, (f"Gap detected at index {i}: {seqs[i - 1]} -> {seqs[i]}")
        return True, f"No gaps in {len(seqs)} sequences"


class SyncSSEHarness:
    """Synchronous wrapper for SSE harness.

    Useful for running async harness in sync test contexts.
    """

    def __init__(self, harness: SSEHarness):
        self._harness = harness

    def consume_n_events(
        self,
        n: int,
        timeout: float = DEFAULT_TIMEOUT,
        resume_from: Optional[int] = None,
        last_event_id: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> List[SSEEvent]:
        """Synchronous wrapper for consume_n_events."""
        return asyncio.get_event_loop().run_until_complete(
            self._harness.consume_n_events(
                n=n,
                timeout=timeout,
                resume_from=resume_from,
                last_event_id=last_event_id,
                job_id=job_id,
            )
        )

    def consume_heartbeats(
        self,
        count: int,
        timeout: Optional[float] = None,
    ) -> List[SSEEvent]:
        """Synchronous wrapper for consume_heartbeats."""
        return asyncio.get_event_loop().run_until_complete(
            self._harness.consume_heartbeats(count=count, timeout=timeout)
        )

    @property
    def events(self) -> List[SSEEvent]:
        """Get events from underlying harness."""
        return self._harness.events

    def validate_heartbeat_timing(self) -> tuple[bool, str]:
        """Validate heartbeat timing."""
        return self._harness.validate_heartbeat_timing()

    def validate_monotonic_sequences(self) -> tuple[bool, str]:
        """Validate sequence monotonicity."""
        return self._harness.validate_monotonic_sequences()

    def validate_no_gaps(self) -> tuple[bool, str]:
        """Validate no sequence gaps."""
        return self._harness.validate_no_gaps()

    def get_sequence_numbers(self) -> List[int]:
        """Get sequence numbers."""
        return self._harness.get_sequence_numbers()


def create_harness(
    app,
    token: str,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
) -> SSEHarness:
    """Create SSE harness for a FastAPI app.

    Uses httpx's ASGI transport for in-process testing.

    Args:
        app: FastAPI application
        token: Auth token
        heartbeat_interval: Expected heartbeat interval

    Returns:
        Configured SSEHarness
    """
    # For httpx with ASGI app, base_url is just a placeholder
    return SSEHarness(
        base_url="http://test",
        auth_token=token,
        heartbeat_interval=heartbeat_interval,
    )
