from __future__ import annotations

import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from .events import EventKind, EventStatus, TelemetryEvent, new_id, utc_now_iso
from .exporters.otlp import build_otlp_exporter
from .jsonl import JsonlWriter


_SERVICE_NAME: str = "agent-observability"
_SERVICE_VERSION: str = os.getenv("AGENT_OBS_VERSION", "0.1.0")
_SOURCE: str = "unknown"
_JSONL_WRITER: JsonlWriter | None = None
_CONFIGURED: bool = False

_current_run_id: ContextVar[str | None] = ContextVar("_current_run_id", default=None)
_current_trace_id: ContextVar[str | None] = ContextVar("_current_trace_id", default=None)
_current_span_stack: ContextVar[list[str]] = ContextVar("_current_span_stack", default=[])


def configure_tracing(
    service_name: str = "agent-observability",
    *,
    source: str = "unknown",
    jsonl_path: str | None = None,
    enable_console: bool = False,
    enable_otlp: bool = False,
) -> None:
    global _SERVICE_NAME, _SERVICE_VERSION, _SOURCE, _JSONL_WRITER, _CONFIGURED

    _SERVICE_NAME = service_name
    _SERVICE_VERSION = os.getenv("AGENT_OBS_VERSION", "0.1.0")
    _SOURCE = source

    if jsonl_path:
        _JSONL_WRITER = JsonlWriter(jsonl_path)

    if _CONFIGURED:
        return

    resource = Resource.create(
        {
            "service.name": _SERVICE_NAME,
            "service.version": _SERVICE_VERSION,
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    if enable_console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    if enable_otlp:
        provider.add_span_processor(BatchSpanProcessor(build_otlp_exporter()))

    _CONFIGURED = True


def _redact_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    sensitive_keys = {
        "api_key",
        "authorization",
        "token",
        "password",
        "secret",
        "access_token",
        "refresh_token",
    }

    for key, value in attributes.items():
        key_lower = key.lower()

        if key_lower in sensitive_keys:
            redacted[key] = "[REDACTED]"
            continue

        if isinstance(value, str) and len(value) > 2000:
            redacted[key] = value[:2000] + "...[TRUNCATED]"
            continue

        redacted[key] = value

    return redacted


def _build_event(
    *,
    kind: EventKind,
    event_type: str,
    name: str,
    status: EventStatus = "ok",
    span_id: str | None = None,
    parent_span_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    duration_ms: int | None = None,
    attributes: dict[str, Any] | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> TelemetryEvent:
    return TelemetryEvent(
        kind=kind,
        event_type=event_type,
        name=name,
        status=status,
        source=_SOURCE,
        service_name=_SERVICE_NAME,
        service_version=_SERVICE_VERSION,
        run_id=_current_run_id.get(),
        trace_id=_current_trace_id.get(),
        span_id=span_id,
        parent_span_id=parent_span_id,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        attributes=_redact_attributes(attributes or {}),
        error_type=error_type,
        error_message=error_message,
    )

def _write_event(event: TelemetryEvent) -> None:
    if _JSONL_WRITER is None:
        return

    try:
        _JSONL_WRITER.write_event(event)
    except Exception:
        # Telemetry must never break the caller.
        return


def emit_event(
    name: str,
    *,
    event_type: str = "event",
    status: str = "ok",
    attributes: dict[str, Any] | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    stack = _current_span_stack.get()
    current_span_id = stack[-1] if stack else None
    parent_span_id = stack[-2] if len(stack) >= 2 else None

    event = _build_event(
        kind="event",
        event_type=event_type,
        name=name,
        status=status,
        span_id=current_span_id,
        parent_span_id=parent_span_id,
        attributes=attributes,
        error_type=error_type,
        error_message=error_message,
    )
    _write_event(event)

    current_otel_span = trace.get_current_span()
    if current_otel_span is not None and current_otel_span.is_recording():
        current_otel_span.add_event(
            name,
            attributes=_redact_attributes(attributes or {}),
        )


@contextmanager
def run_context(
    run_id: str,
    *,
    name: str = "run",
    attributes: dict[str, Any] | None = None,
) -> Iterator[None]:
    previous_run_id = _current_run_id.get()
    previous_trace_id = _current_trace_id.get()
    previous_stack = _current_span_stack.get()

    trace_id = new_id("trc")
    start_ts = utc_now_iso()
    start_perf = time.perf_counter()

    run_token = _current_run_id.set(run_id)
    trace_token = _current_trace_id.set(trace_id)
    stack_token = _current_span_stack.set([])

    _write_event(
        _build_event(
            kind="run",
            event_type="run.start",
            name=name,
            status="in_progress",
            start_time=start_ts,
            attributes=attributes,
        )
    )

    try:
        yield

        end_ts = utc_now_iso()
        duration_ms = int((time.perf_counter() - start_perf) * 1000)

        _write_event(
            _build_event(
                kind="run",
                event_type="run.end",
                name=name,
                status="ok",
                start_time=start_ts,
                end_time=end_ts,
                duration_ms=duration_ms,
                attributes=attributes,
            )
        )
    except Exception as exc:
        end_ts = utc_now_iso()
        duration_ms = int((time.perf_counter() - start_perf) * 1000)

        _write_event(
            _build_event(
                kind="run",
                event_type="run.end",
                name=name,
                status="error",
                start_time=start_ts,
                end_time=end_ts,
                duration_ms=duration_ms,
                attributes=attributes,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )
        raise
    finally:
        _current_run_id.reset(run_token)
        _current_trace_id.reset(trace_token)
        _current_span_stack.reset(stack_token)

        if previous_run_id is not None:
            _current_run_id.set(previous_run_id)
        if previous_trace_id is not None:
            _current_trace_id.set(previous_trace_id)
        _current_span_stack.set(previous_stack)


@contextmanager
def span(
    name: str,
    *,
    event_type: str = "span",
    **attrs: object,
) -> Iterator[trace.Span]:
    tracer = trace.get_tracer("agent_observability")

    stack = list(_current_span_stack.get())
    span_id = new_id("spn")
    parent_span_id = stack[-1] if stack else None

    start_perf = time.perf_counter()
    start_ts = utc_now_iso()

    with tracer.start_as_current_span(name) as current_span:
        current_span.set_attribute("agent_observability.span_id", span_id)
        if parent_span_id is not None:
            current_span.set_attribute("agent_observability.parent_span_id", parent_span_id)

        for key, value in _redact_attributes(dict(attrs)).items():
            current_span.set_attribute(key, value)

        stack.append(span_id)
        token = _current_span_stack.set(stack)

        _write_event(
            _build_event(
                kind="span",
                event_type=f"{event_type}.start",
                name=name,
                status="in_progress",
                span_id=span_id,
                parent_span_id=parent_span_id,
                start_time=start_ts,
                attributes=dict(attrs),
            )
        )

        try:
            yield current_span

            end_ts = utc_now_iso()
            duration_ms = int((time.perf_counter() - start_perf) * 1000)

            _write_event(
                _build_event(
                    kind="span",
                    event_type=f"{event_type}.end",
                    name=name,
                    status="ok",
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_ms=duration_ms,
                    attributes=dict(attrs),
                )
            )
        except Exception as exc:
            end_ts = utc_now_iso()
            duration_ms = int((time.perf_counter() - start_perf) * 1000)

            current_span.record_exception(exc)
            current_span.set_attribute("error", True)

            _write_event(
                _build_event(
                    kind="span",
                    event_type=f"{event_type}.end",
                    name=name,
                    status="error",
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_ms=duration_ms,
                    attributes=dict(attrs),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            raise
        finally:
            _current_span_stack.reset(token)