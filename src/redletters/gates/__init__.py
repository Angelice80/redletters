"""Gates module: Acknowledgement gating mechanism.

This module implements ADR-008 acknowledgement gates.

Key concepts:
- Gate: A checkpoint requiring user decision
- GateTrigger: Conditions that trigger gates
- AcknowledgementState: User acknowledgement tracking
"""

from redletters.gates.detector import GateDetector, GateTrigger, DetectionResult
from redletters.gates.checkpoint import (
    Gate,
    GateOption,
    GateResponse,
    GateType,
    GateCheckpoint,
)
from redletters.gates.state import (
    AcknowledgementState,
    VariantAcknowledgement,
    AcknowledgementStore,
)

__all__ = [
    # Detection
    "GateDetector",
    "GateTrigger",
    "DetectionResult",
    # Checkpoint
    "Gate",
    "GateOption",
    "GateResponse",
    "GateType",
    "GateCheckpoint",
    # State
    "AcknowledgementState",
    "VariantAcknowledgement",
    "AcknowledgementStore",
]
