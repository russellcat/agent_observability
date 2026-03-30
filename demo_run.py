from pathlib import Path

from agent_observability import configure_tracing, run_context, span, emit_event
from agent_observability.integrations.llm import traced_llm_call
from agent_observability.integrations.subprocess_backend import run_command


def main() -> None:
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)

    trace_file = output_dir / "events.jsonl"

    configure_tracing(
        service_name="agent-observability-demo",
        source="demo-script",
        jsonl_path=str(trace_file),
        enable_console=False,
        enable_otlp=False,
    )

    fake_response = {
        "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 13,
            "total_tokens": 55,
        }
    }

    with run_context(
        "demo-run-001",
        name="demo.benchmark",
        attributes={"backend": "demo", "dataset": "synthetic"},
    ):
        emit_event("demo.start", attributes={"message": "starting demo run"})

        # Step 1: simulate repo clone
        with span("repo.clone", event_type="step", repo="sympy/sympy"):
            run_command(["python3", "-c", "print('cloning repo...')"])

        # Step 2: simulate LLM call
        with span("agent.generate_patch", event_type="step"):
            traced_llm_call(
                provider="openai",
                model="openai/gpt-4o-mini",
                operation="chat.completions.create",
                request_fn=lambda: fake_response,
            )

        # Step 3: simulate artifact write
        with span("artifact.write", event_type="artifact", file="patch.diff"):
            (output_dir / "patch.diff").write_text("diff --git a/file b/file\n...")

        emit_event(
            "demo.complete",
            attributes={"status": "success"},
        )


if __name__ == "__main__":
    main()