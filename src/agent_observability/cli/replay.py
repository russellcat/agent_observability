from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_observability.events import TelemetryEvent


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: replay <jsonl-file>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"file not found: {path}")
        return 1

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
            event = TelemetryEvent.model_validate(payload)
            print(json.dumps(event.to_dict(), indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"invalid event on line {line_number}: {exc}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())