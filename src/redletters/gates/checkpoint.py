"""Gate checkpoint logic.

Defines gate structure and checkpoint validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from redletters.gates.detector import GateTrigger


class GateType(Enum):
    """Types of acknowledgement gates."""

    VARIANT = "variant"
    GRAMMAR = "grammar"
    ESCALATION = "escalation"
    EXPORT = "export"


@dataclass
class GateOption:
    """An option presented at a gate."""

    id: str
    label: str
    description: str
    is_default: bool = False
    reading_index: int | None = None


@dataclass
class Gate:
    """An acknowledgement gate requiring user decision."""

    gate_id: str
    gate_type: GateType
    trigger: GateTrigger
    title: str
    message: str
    ref: str | None = None
    options: list[GateOption] = field(default_factory=list)
    requires_acknowledgement: bool = True
    metadata: dict = field(default_factory=dict)

    @classmethod
    def for_variant(
        cls,
        variant_ref: str,
        readings: list[dict],
        sblgnt_index: int = 0,
    ) -> "Gate":
        """Create a variant acknowledgement gate."""
        options = []
        for i, r in enumerate(readings):
            witnesses = r.get("witnesses", [])
            witness_str = ", ".join(witnesses[:5]) if witnesses else "Unknown"
            options.append(
                GateOption(
                    id=f"reading_{i}",
                    label=r.get("surface_text", f"Reading {i + 1}"),
                    description=f"Witnesses: {witness_str}",
                    is_default=(i == sblgnt_index),
                    reading_index=i,
                )
            )

        options.append(
            GateOption(
                id="view_full",
                label="View full apparatus",
                description="See complete witness data",
            )
        )

        return cls(
            gate_id=f"variant_{variant_ref}_{datetime.now().timestamp()}",
            gate_type=GateType.VARIANT,
            trigger=GateTrigger.VARIANT_DEPENDENCY,
            title="Variant Dependency Detected",
            message=f"Your interpretation depends on the reading at {variant_ref}",
            ref=variant_ref,
            options=options,
        )

    @classmethod
    def for_escalation(
        cls,
        claim_type_label: str,
        from_mode: str = "readable",
        to_mode: str = "traceable",
    ) -> "Gate":
        """Create an escalation gate."""
        return cls(
            gate_id=f"escalation_{claim_type_label}_{datetime.now().timestamp()}",
            gate_type=GateType.ESCALATION,
            trigger=GateTrigger.CLAIM_ESCALATION,
            title="Claim Requires Traceable Mode",
            message=f"{claim_type_label} claims require {to_mode.title()} mode",
            options=[
                GateOption(
                    id="switch_mode",
                    label=f"Switch to {to_mode.title()} Mode",
                    description="Make this claim with full dependency tracking",
                    is_default=True,
                ),
                GateOption(
                    id="rewrite",
                    label="Rewrite as lower-level claim",
                    description="Modify claim to fit current mode",
                ),
                GateOption(
                    id="cancel",
                    label="Cancel",
                    description="Abandon this claim",
                ),
            ],
            metadata={"from_mode": from_mode, "to_mode": to_mode},
        )

    def to_dict(self) -> dict:
        """Serialize for API/UI."""
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "trigger": self.trigger.value,
            "title": self.title,
            "message": self.message,
            "ref": self.ref,
            "options": [
                {
                    "id": o.id,
                    "label": o.label,
                    "description": o.description,
                    "is_default": o.is_default,
                }
                for o in self.options
            ],
            "metadata": self.metadata,
        }


@dataclass
class GateResponse:
    """User response to a gate."""

    gate_id: str
    option_selected: str
    acknowledged: bool
    timestamp: datetime = field(default_factory=datetime.now)
    reading_index: int | None = None
    notes: str | None = None


class GateCheckpoint:
    """Checkpoint for validating gate acknowledgements."""

    def validate_response(self, gate: Gate, response: GateResponse) -> bool:
        """Validate a gate response."""
        if gate.gate_id != response.gate_id:
            return False

        if gate.requires_acknowledgement and not response.acknowledged:
            return False

        valid_options = {o.id for o in gate.options}
        if response.option_selected not in valid_options:
            return False

        if response.option_selected == "cancel":
            return False

        return True
