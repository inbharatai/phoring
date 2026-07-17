"""Field-level provenance for simulation agent profiles.

The existing OASIS profile format is intentionally left unchanged. This model
provides an internal, serializable record describing whether each profile value
is verified, derived, inferred, assumed, or unknown before it is adapted to the
legacy Twitter/Reddit exports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar


T = TypeVar("T")


class ProvenanceStatus(str, Enum):
    VERIFIED = "verified"
    DERIVED = "derived"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProvenanceField(Generic[T]):
    """One profile field plus its evidence and uncertainty metadata."""

    value: Optional[T]
    status: ProvenanceStatus
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    method: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.status == ProvenanceStatus.VERIFIED and not self.evidence_ids:
            raise ValueError("verified fields require at least one evidence_id")
        if self.status == ProvenanceStatus.UNKNOWN and self.value is not None:
            raise ValueError("unknown fields must have value=None")

    @classmethod
    def unknown(cls, note: str = "No reliable source available") -> "ProvenanceField":
        return cls(
            value=None,
            status=ProvenanceStatus.UNKNOWN,
            confidence=0.0,
            note=note,
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class ProfileProvenance:
    """Audit record for all factual and behavioural fields of one agent."""

    source_entity_uuid: str
    source_entity_name: str
    source_entity_type: str
    fields: Dict[str, ProvenanceField[Any]] = field(default_factory=dict)
    schema_version: str = "1"

    def set_field(self, name: str, value: ProvenanceField[Any]) -> None:
        if not name or not name.strip():
            raise ValueError("field name cannot be empty")
        self.fields[name.strip()] = value

    def get_value(self, name: str, default: Any = None) -> Any:
        field_value = self.fields.get(name)
        if field_value is None or field_value.value is None:
            return default
        return field_value.value

    def unsupported_assumptions(self) -> List[str]:
        """Return fields that are assumed without evidence."""
        return sorted(
            name
            for name, field_value in self.fields.items()
            if field_value.status == ProvenanceStatus.ASSUMED
            and not field_value.evidence_ids
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_name": self.source_entity_name,
            "source_entity_type": self.source_entity_type,
            "fields": {
                name: value.to_dict()
                for name, value in sorted(self.fields.items())
            },
            "unsupported_assumptions": self.unsupported_assumptions(),
        }
