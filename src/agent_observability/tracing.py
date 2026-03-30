from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

from .exporters.otlp import build_otlp_exporter
from .jsonl import JsonlWriter


def configure_tracing(
    service_name: str = "agent-observability",
    jsonl_path: str | None = None,
    enable_console: bool = False,
    enable_otlp: bool = False,
) -> None:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("AGENT_OBS_VERSION", "0.1.0"),
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    if enable_console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    if enable_otlp:
        provider.add_span_processor(BatchSpanProcessor(build_otlp_exporter()))

    if jsonl_path:
        _JSONL_WRITER["writer"] = JsonlWriter(jsonl_path)


_JSONL_WRITER: dict[str, JsonlWriter] = {}


from datetime import datetime, UTC
import time


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def span(name: str, **attrs: object) -> Iterator[trace.Span]:
    tracer = trace.get_tracer("agent_observability")

    start_time = time.perf_counter()
    start_ts = _utc_now_iso()

    with tracer.start_as_current_span(name) as current_span:
        for key, value in attrs.items():
            current_span.set_attribute(key, value)

        writer = _JSONL_WRITER.get("writer")
        if writer:
            writer.write(
                {
                    "kind": "span_start",
                    "name": name,
                    "ts": start_ts,
                    "attributes": attrs,
                }
            )

        try:
            yield current_span

            end_time = time.perf_counter()
            end_ts = _utc_now_iso()
            duration_ms = int((end_time - start_time) * 1000)

            if writer:
                writer.write(
                    {
                        "kind": "span_end",
                        "name": name,
                        "ts": end_ts,
                        "duration_ms": duration_ms,
                        "status": "ok",
                    }
                )

        except Exception as exc:
            end_time = time.perf_counter()
            end_ts = _utc_now_iso()
            duration_ms = int((end_time - start_time) * 1000)

            current_span.record_exception(exc)
            current_span.set_attribute("error", True)

            if writer:
                writer.write(
                    {
                        "kind": "span_end",
                        "name": name,
                        "ts": end_ts,
                        "duration_ms": duration_ms,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
            raise