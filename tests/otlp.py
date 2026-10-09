"""A hand-built OTLP protobuf export, for the tests that need real bytes.

The zoo parses nothing (`SPEC.md` §1.1) and so cannot *construct* an OTLP
payload either -- there is no protobuf library here and there is not going to
be one. So this encodes one by hand, in sixty lines of varints, from
`opentelemetry/proto/trace/v1/trace.proto` and
`opentelemetry/proto/collector/trace/v1/trace_service.proto`.

Which is the right shape for a test anyway: the bytes a test asserts on are
bytes the test wrote, field number by field number, and the trace and span ids
are values the test chose. When the integration test (`test_collector_real.py`)
reads `TRACE_ID` back out of the Collector's JSON, nothing in between could
have agreed with itself about what a span is.

This is test scaffolding and lives in `tests/`. Nothing under
`spanweave_zoo/` imports it, and nothing here is shipped.
"""

from __future__ import annotations

# Chosen, not generated: W3C trace-context's own example ids, which are also
# the ones every OTLP document uses, so a mismatch is easy to read.
TRACE_ID = bytes.fromhex("4bf92f3577b34da6a3ce929d0e0e4736")
SPAN_ID = bytes.fromhex("00f067aa0ba902b7")
SPAN_NAME = "GET /checkout"
SERVICE_NAME = "zoo-synthetic"

START_UNIX_NANO = 1_700_000_000_000_000_000
END_UNIX_NANO = 1_700_000_000_500_000_000


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        seven = value & 0x7F
        value >>= 7
        out.append(seven | 0x80 if value else seven)
        if not value:
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _bytes_field(field: int, payload: bytes) -> bytes:
    """Wire type 2: length-delimited -- a message, a string or bytes."""
    return _tag(field, 2) + _varint(len(payload)) + payload


def _string(field: int, text: str) -> bytes:
    return _bytes_field(field, text.encode("utf-8"))


def _fixed64(field: int, value: int) -> bytes:
    return _tag(field, 1) + value.to_bytes(8, "little")


def _varint_field(field: int, value: int) -> bytes:
    return _tag(field, 0) + _varint(value)


def export_trace_service_request(
    *,
    trace_id: bytes = TRACE_ID,
    span_id: bytes = SPAN_ID,
    name: str = SPAN_NAME,
    service_name: str = SERVICE_NAME,
) -> bytes:
    """One `ExportTraceServiceRequest` carrying one resource, scope and span."""
    # Span: trace_id=1, span_id=2, name=5, kind=6, start=7, end=8.
    span = (
        _bytes_field(1, trace_id)
        + _bytes_field(2, span_id)
        + _string(5, name)
        + _varint_field(6, 2)  # SPAN_KIND_SERVER
        + _fixed64(7, START_UNIX_NANO)
        + _fixed64(8, END_UNIX_NANO)
    )
    # InstrumentationScope: name=1, version=2. ScopeSpans: scope=1, spans=2.
    scope_spans = _bytes_field(
        1, _string(1, "zoo.synthetic") + _string(2, "0.0.1")
    ) + _bytes_field(2, span)
    # KeyValue: key=1, value=2. AnyValue: string_value=1. Resource: attributes=1.
    attribute = _bytes_field(
        1, _string(1, "service.name") + _bytes_field(2, _string(1, service_name))
    )
    # ResourceSpans: resource=1, scope_spans=2.
    resource_spans = _bytes_field(1, attribute) + _bytes_field(2, scope_spans)
    # ExportTraceServiceRequest: resource_spans=1.
    return _bytes_field(1, resource_spans)
