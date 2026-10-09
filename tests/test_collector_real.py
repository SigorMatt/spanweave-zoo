"""The real Collector: a protobuf export comes back as JSON (`SPEC.md` §4.9).

This is the A2 row's central claim and the one thing no seam can stand in for:
hand-built OTLP **protobuf** goes into the raw sink, the tee forwards the same
bytes to the stock `otelcol-contrib`, and what lands in `json/0001.json` is
OTLP **JSON carrying the same trace and span ids**.

It needs the pinned binary, which is a ~100 MB gitignored download
(`make collector`). So it is **skipped when the binary is absent**, which is
how it behaves in CI -- nothing in CI fetches it -- and it **runs when it is
present**, which is how `make check` behaves on a machine that has. It skips
loudly rather than passing quietly: a test that reported success without
re-encoding anything would be exactly the reassuring pass this repository
refuses (`CLAUDE.md`).

The waiting here is honest about what it waits on. The Collector is another
process with a batch processor, so the test cannot know when it will POST; it
blocks on a queue fed by the json sink's own `after_record` seam, with a
timeout, rather than polling a directory or sleeping a guessed interval.
"""

from __future__ import annotations

import gzip
import http.client
import json
import queue
import socket
import time
from pathlib import Path

import pytest

from spanweave_zoo import capture, cli, collector, forward, manifest
from tests import otlp

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_DIR = REPO / "collector"
BINARY = COLLECTOR_DIR / collector.BINARY_NAME

needs_collector = pytest.mark.skipif(
    not BINARY.is_file(),
    reason=(
        f"{BINARY} is absent (it is a gitignored ~100MB download): "
        f"run `make collector`. SPEC.md section 4.9."
    ),
)

HOST = "127.0.0.1"
PROTOBUF = otlp.export_trace_service_request()
# A second export, gzipped, with its own ids: the Python OTLP/HTTP exporter can
# compress, the sink never decompresses, and the Collector must therefore get
# the `Content-Encoding` through the tee untouched to read it at all.
SECOND_TRACE_ID = bytes.fromhex("0af7651916cd43dd8448eb211c80319c")
SECOND_SPAN_ID = bytes.fromhex("b7ad6b7169203331")
GZIPPED = gzip.compress(
    otlp.export_trace_service_request(
        trace_id=SECOND_TRACE_ID, span_id=SECOND_SPAN_ID, name="POST /pay"
    ),
    mtime=0,
)

ARRIVAL_TIMEOUT = 60.0


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


def free_port() -> int:
    """A port the Collector can have.

    The Collector must be told its receiver's port before it starts, so this
    cannot be `port=0` the way every sink in the suite is: the number has to
    exist first. Bound on the loopback and released immediately, and if
    something does take it in between, the Collector fails to listen and the
    readiness check refuses -- loudly, rather than hanging.
    """
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def post(port: int, body: bytes, headers: dict[str, str]) -> int:
    connection = http.client.HTTPConnection(HOST, port, timeout=30)
    try:
        connection.request("POST", "/v1/traces", body=body, headers=headers)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def spans_of(document: dict) -> list[dict]:
    return [
        span
        for resource in document["resourceSpans"]
        for scope in resource["scopeSpans"]
        for span in scope["spans"]
    ]


@needs_collector
def test_the_binary_on_disk_is_the_pinned_version():
    pinned = collector.pin(COLLECTOR_DIR)
    launcher = collector.Binary(
        pinned,
        host=HOST,
        http_port=free_port(),
        grpc_port=0,
        sleep=time.sleep,
    )
    assert launcher.version() == pinned.version
    assert launcher.environment("http://127.0.0.1:1") == {
        collector.ENV_GRPC: f"{HOST}:0",
        collector.ENV_HTTP: f"{HOST}:{launcher.http_port}",
        collector.ENV_JSON_SINK: "http://127.0.0.1:1",
    }


@needs_collector
def test_a_protobuf_export_through_the_tee_comes_back_as_json_with_the_same_ids(
    tmp_path,
):
    run = tmp_path / "captures" / "z4" / "real-1"
    pinned = collector.pin(COLLECTOR_DIR)
    collector_port = free_port()
    arrived: queue.Queue[str] = queue.Queue()

    started = capture.Capture(
        run,
        now=Clock(),
        launcher=collector.Binary(
            pinned,
            host=HOST,
            http_port=collector_port,
            grpc_port=0,
            sleep=time.sleep,
        ),
        forward=forward.HttpForward(HOST, collector_port, timeout=30.0),
        pin=pinned,
        host=HOST,
        raw_port=0,
        json_port=0,
        on_record=lambda entry: (
            arrived.put(entry.file) if entry.file.startswith("json/") else None
        ),
    )
    started.start()
    try:
        assert (
            post(
                started.raw.port,
                PROTOBUF,
                {"Content-Type": "application/x-protobuf"},
            )
            == 200
        )
        assert arrived.get(timeout=ARRIVAL_TIMEOUT) == "json/0001.json"

        # Only after the first has landed, so the batch processor cannot
        # coalesce the two and `SPEC.md` §4.7's honest caveat does not bite.
        assert (
            post(
                started.raw.port,
                GZIPPED,
                {
                    "Content-Type": "application/x-protobuf",
                    "Content-Encoding": "gzip",
                },
            )
            == 200
        )
        assert arrived.get(timeout=ARRIVAL_TIMEOUT) == "json/0002.json"
    finally:
        started.stop()

    # The raw bytes are the record, and they are the bytes that were sent.
    assert (run / "raw" / "0001.body").read_bytes() == PROTOBUF
    assert (run / "raw" / "0002.body").read_bytes() == GZIPPED, (
        "the gzipped export was stored decompressed"
    )

    # And the Collector's re-encoding is beside them, with the same ids.
    first = json.loads((run / "json" / "0001.json").read_text(encoding="utf-8"))
    [span] = spans_of(first)
    assert span["traceId"] == otlp.TRACE_ID.hex()
    assert span["spanId"] == otlp.SPAN_ID.hex()
    assert span["name"] == otlp.SPAN_NAME
    assert first["resourceSpans"][0]["resource"]["attributes"] == [
        {"key": "service.name", "value": {"stringValue": otlp.SERVICE_NAME}}
    ]

    second = json.loads((run / "json" / "0002.json").read_text(encoding="utf-8"))
    [other] = spans_of(second)
    assert other["traceId"] == SECOND_TRACE_ID.hex()
    assert other["spanId"] == SECOND_SPAN_ID.hex()

    # The JSON arrived uncompressed, because the exporter is configured not to
    # compress and the sink would not have decompressed it (`SPEC.md` §4.2).
    delivered = json.loads(
        (run / "json" / "0001.headers.json").read_text(encoding="utf-8")
    )
    pairs = {name.lower(): value for name, value in delivered["headers"]}
    assert pairs["content-type"] == "application/json"
    assert "content-encoding" not in pairs

    # Both forwards delivered, the manifest says so, and it all re-hashes.
    document = manifest.read(run)
    assert document[manifest.FORWARDS] == [
        {"file": "raw/0001.body", "status": 200},
        {"file": "raw/0002.body", "status": 200},
    ]
    assert document[manifest.COLLECTOR_VERSION] == pinned.version
    assert [entry["file"] for entry in document["bodies"]] == [
        "raw/0001.body",
        "json/0001.json",
        "raw/0002.body",
        "json/0002.json",
    ]
    assert started.failed_forwards == []
    assert cli.verify(tmp_path / "captures") == 0


@needs_collector
def test_the_collector_refuses_rather_than_hangs_when_it_cannot_listen(tmp_path):
    """A readiness budget that runs out is a refusal (`SPEC.md` §4.6).

    Driven by giving the Collector a port it cannot have -- 1, which needs
    privileges -- and one attempt, so the refusal is the only outcome and the
    test cannot wait on anything.
    """
    pinned = collector.pin(COLLECTOR_DIR)
    launcher = collector.Binary(
        pinned,
        host=HOST,
        http_port=1,
        grpc_port=0,
        sleep=lambda seconds: None,
        attempts=1,
    )
    with pytest.raises(collector.CollectorRefused) as refused:
        launcher.start("http://127.0.0.1:1")
    assert "127.0.0.1:1" in str(refused.value)
