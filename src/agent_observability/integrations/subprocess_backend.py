from __future__ import annotations

import subprocess
from pathlib import Path

from agent_observability.tracing import emit_event, span


def run_command(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    with span(
        "tool.call",
        event_type="tool",
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

    emit_event(
        "tool.result",
        event_type="tool.result",
        attributes={
            "tool_name": "subprocess",
            "exit_code": result.returncode,
            "stdout_len": len(result.stdout or ""),
            "stderr_len": len(result.stderr or ""),
        },
    )

    return result