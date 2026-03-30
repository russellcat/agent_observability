from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: replay <jsonl-file>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"file not found: {path}")
        return 1

    for line in path.read_text(encoding="utf-8").splitlines():
        print(json.dumps(json.loads(line), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
