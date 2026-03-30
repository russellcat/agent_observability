from __future__ import annotations

import os

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


def build_otlp_exporter() -> OTLPSpanExporter:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    headers_raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

    headers: dict[str, str] = {}
    if headers_raw:
        for item in headers_raw.split(","):
            if "=" in item:
                key, value = item.split("=", 1)
                headers[key.strip()] = value.strip()

    if endpoint:
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)
    return OTLPSpanExporter(headers=headers)
