from __future__ import annotations

import subprocess
import time
from pathlib import Path

from agent_observability.tracing import span


def run_command(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    start = time.perf_counter()
    with span(
        "tool.call",
        tool_name="subprocess",
        command=" ".join(cmd),
        cwd=str(cwd) if cwd else "",
        timeout_s=timeout,
    ):
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    duration_ms = int((time.perf_counter() - start) * 1000)

    with span(
        "tool.result",
        exit_code=result.returncode,
        duration_ms=duration_ms,
        stdout_len=len(result.stdout or ""),
        stderr_len=len(result.stderr or ""),
    ):
        pass

    return result
