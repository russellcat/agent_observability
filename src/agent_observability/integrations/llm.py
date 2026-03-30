from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_observability.tracing import emit_event, span


def traced_llm_call(
    *,
    provider: str,
    model: str,
    operation: str,
    request_fn: Callable[[], Any],
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    extra_attrs: dict[str, object] | None = None,
) -> Any:
    attrs: dict[str, object] = {
        "provider": provider,
        "model": model,
        "operation": operation,
    }

    if prompt_tokens is not None:
        attrs["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        attrs["completion_tokens"] = completion_tokens
    if extra_attrs:
        attrs.update(extra_attrs)

    with span("llm.call", event_type="llm", **attrs):
        response = request_fn()

    usage = None
    if hasattr(response, "usage"):
        usage = getattr(response, "usage")
    elif isinstance(response, dict):
        usage = response.get("usage")

    result_attrs: dict[str, object] = {}

    if usage is not None:
        if hasattr(usage, "prompt_tokens"):
            result_attrs["prompt_tokens"] = usage.prompt_tokens
        elif isinstance(usage, dict) and "prompt_tokens" in usage:
            result_attrs["prompt_tokens"] = usage["prompt_tokens"]

        if hasattr(usage, "completion_tokens"):
            result_attrs["completion_tokens"] = usage.completion_tokens
        elif isinstance(usage, dict) and "completion_tokens" in usage:
            result_attrs["completion_tokens"] = usage["completion_tokens"]

        if hasattr(usage, "total_tokens"):
            result_attrs["total_tokens"] = usage.total_tokens
        elif isinstance(usage, dict) and "total_tokens" in usage:
            result_attrs["total_tokens"] = usage["total_tokens"]

    emit_event(
        "llm.result",
        event_type="llm.result",
        attributes=result_attrs,
    )

    return response