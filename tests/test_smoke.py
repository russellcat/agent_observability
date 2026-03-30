from pathlib import Path

from agent_observability import configure_tracing, run_context, span
from agent_observability.integrations.llm import traced_llm_call
from agent_observability.integrations.subprocess_backend import run_command


def test_smoke(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"

    configure_tracing(
        service_name="agent-observability-test",
        source="test-suite",
        jsonl_path=str(trace_file),
        enable_console=False,
        enable_otlp=False,
    )

    fake_response = {
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 6,
            "total_tokens": 16,
        }
    }

    with run_context(
        "smoke-run",
        name="benchmark.run",
        attributes={"instance_id": "demo-1"},
    ):
        with span("benchmark.step", event_type="step", instance_id="demo-1"):
            result = run_command(["python3", "-c", "print('hello')"], timeout=30)
            assert result.returncode == 0

            response = traced_llm_call(
                provider="openai",
                model="openai/gpt-4o-mini",
                operation="chat.completions.create",
                request_fn=lambda: fake_response,
            )
            assert response == fake_response

    assert trace_file.exists()

    text = trace_file.read_text(encoding="utf-8")
    assert "benchmark.run" in text
    assert "benchmark.step" in text
    assert "llm.call" in text
    assert "tool.call" in text
    assert "smoke-run" in text