from __future__ import annotations

import time
from dataclasses import dataclass, field

from agent_observability.tracing import emit_event


@dataclass
class Watchdog:
    timeout_seconds: float
    last_progress_ts: float = field(default_factory=time.monotonic)

    def heartbeat(self) -> None:
        self.last_progress_ts = time.monotonic()
        emit_event(
            "watchdog.heartbeat",
            event_type="watchdog.heartbeat",
            attributes={"timeout_seconds": self.timeout_seconds},
        )

    def is_stalled(self) -> bool:
        stalled_for = time.monotonic() - self.last_progress_ts
        is_stalled = stalled_for > self.timeout_seconds

        if is_stalled:
            emit_event(
                "watchdog.stalled",
                event_type="watchdog.stalled",
                status="error",
                attributes={
                    "timeout_seconds": self.timeout_seconds,
                    "stalled_for_seconds": stalled_for,
                },
            )

        return is_stalled