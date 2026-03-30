from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "0.1.0"

EventStatus = Literal["ok", "error", "in_progress"]
EventKind = Literal["run", "span", "event"]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    timestamp: str = Field(default_factory=utc_now_iso)

    kind: EventKind
    event_type: str
    name: str
    status: EventStatus = "ok"

    source: str
    service_name: str
    service_version: str

    run_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int | None = None

    attributes: dict[str, Any] = Field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")