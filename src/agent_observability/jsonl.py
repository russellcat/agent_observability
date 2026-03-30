from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .events import TelemetryEvent


class JsonlWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def write_event(self, event: TelemetryEvent) -> None:
        self.write(event.to_dict())