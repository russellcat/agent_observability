from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Event:
    event_type: str
    ts: str = field(default_factory=utc_now_iso)
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
