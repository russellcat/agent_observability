from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Watchdog:
    timeout_seconds: float
    last_progress_ts: float = field(default_factory=time.monotonic)

    def heartbeat(self) -> None:
        self.last_progress_ts = time.monotonic()

    def is_stalled(self) -> bool:
        return (time.monotonic() - self.last_progress_ts) > self.timeout_seconds
