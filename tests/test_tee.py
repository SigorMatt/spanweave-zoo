"""The tee: the same bytes again, after they are on disk (`SPEC.md` §4.3).

No Collector here, and that is the design rather than a shortcut: the forward
is a seam (`SPEC.md` §4.8), so every mechanical claim about the tee -- the
bytes are identical, the headers are identical, the body is written first, a
failure is recorded and not swallowed -- is testable without 100 MB of Go on
the machine. What only the real Collector can prove is in
`test_collector_real.py`, and it says so when it skips.

Every sink here binds `127.0.0.1` on port **0** and nothing sleeps, for A1's
reasons (`tests/test_sink.py`).
"""

from __future__ import annotations

import gzip
import http.client
import json
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from spanweave_zoo import cli, forward, manifest, sink
from tests import otlp

PROTOBUF = otlp.export_trace_service_request()
JSON_BODY = b'{"resourceSpans":[]}'
GZIP_BODY = gzip.compress(JSON_BODY, mtime=0)

TIMEOUT = 5.0


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


class Spy:
    """A `forward` that writes down what it was handed, and answers 200.

    It also reads the body back off disk at the moment it is called, which is
    how "the body is on disk before the forward is attempted" (`SPEC.md` §4.3)
    becomes something a test can see rather than something the code claims.
    """

    def __init__(self, run: Path, *, status: int = 200) -> None:
        self.run = run
        self.status = status
        self.calls: list[tuple[str, str, list[tuple[str, str]], bytes]] = []
        self.on_disk: list[bytes | None] = []

    def __call__(self, method, path, headers, body):
        self.calls.append((method, path, list(headers), body))
        written = self.run / "raw" / f"{len(self.calls):04d}.body"
        self.on_disk.append(written.read_bytes() if written.exists() else None)
        return self.status


class Refusing:
    """A Collector that is not there."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, method, path, headers, body):
        self.calls += 1
        raise ConnectionRefusedError(111, "Connection refused")


@contextmanager
def tee(raw: Path, forwarder, **kwargs):
    recorder = sink.Recorder(raw, now=Clock(), forward=forwarder, **kwargs)
    server = sink.make_server(recorder, host="127.0.0.1", port=0)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    try:
        yield recorder, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=TIMEOUT)
        assert not thread.is_alive(), "the sink's thread outlived the test"


def post(port: int, path: str, body: bytes, headers: dict[str, str] | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.request("POST", path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        connection.close()


# --- the forward is byte-identical ------------------------------------------


def test_the_forwarded_body_is_the_bytes_that_arrived(tmp_path):
    # `SPEC.md` §4.3: still gzipped if it arrived gzipped. A tee that
    # decompressed, re-encoded or re-framed on the way out would hand the
    # Collector something the exporter never sent.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(
            port,
            "/v1/traces",
            GZIP_BODY,
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
        )
    assert len(spy.calls) == 1
    _, _, _, forwarded = spy.calls[0]
    assert forwarded == GZIP_BODY
    assert forwarded != JSON_BODY, "the tee decompressed on the way out"
    assert (raw / "0001.body").read_bytes() == forwarded


def test_a_protobuf_body_is_forwarded_as_protobuf(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"})
    assert spy.calls[0][3] == PROTOBUF


def test_the_body_is_on_disk_before_the_forward_is_attempted(tmp_path):
    # `SPEC.md` §4.3: the record is made first and the convenience second, so
    # there is no arrangement of failures in which the zoo forwarded something
    # it did not record.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"})
    assert spy.on_disk == [PROTOBUF], (
        "the body was not on disk, or not complete, when the forward happened"
    )


def test_every_header_is_forwarded_in_order_with_repeats(tmp_path):
    # `SPEC.md` §4.3: the headers are what the Collector needs in order to read
    # the bytes, and a repeated header is part of the record (`SPEC.md` §2.3).
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
        connection.putrequest("POST", "/v1/traces")
        connection.putheader("Content-Type", "application/x-protobuf")
        connection.putheader("Content-Encoding", "gzip")
        connection.putheader("X-Zoo", "one")
        connection.putheader("X-Zoo", "two")
        connection.putheader("Content-Length", str(len(GZIP_BODY)))
        connection.endheaders(GZIP_BODY)
        connection.getresponse().read()
        connection.close()
    _, _, headers, _ = spy.calls[0]
    assert ("X-Zoo", "one") in headers
    assert ("X-Zoo", "two") in headers
    assert [value for name, value in headers if name == "X-Zoo"] == ["one", "two"]
    assert ("Content-Type", "application/x-protobuf") in headers
    assert ("Content-Encoding", "gzip") in headers
    # The seam is handed the headers **as received**, `Host` included: the
    # record is what arrived. Dropping `Host` and the hop-by-hop headers is
    # `HttpForward`'s business, because it is the thing that has a new
    # destination (`SPEC.md` §4.3) -- asserted by
    # `test_forwardable_drops_the_connection_headers_and_keeps_the_rest` and,
    # over a real socket, by
    # `test_the_http_forward_delivers_the_same_bytes_to_a_real_listener`.
    assert [name for name, _ in headers if name.lower() == "host"] == ["Host"]
    assert forward.forwardable(headers) == [
        pair for pair in headers if pair[0].lower() != "host"
    ]


def test_the_method_and_the_path_are_forwarded_as_received(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(port, "/v1/traces", PROTOBUF)
    method, path, _, _ = spy.calls[0]
    assert (method, path) == ("POST", "/v1/traces")


def test_forwardable_drops_the_connection_headers_and_keeps_the_rest():
    headers = [
        ("Host", "127.0.0.1:4318"),
        ("Connection", "keep-alive"),
        ("Transfer-Encoding", "chunked"),
        ("TE", "trailers"),
        ("Upgrade", "h2c"),
        ("Keep-Alive", "timeout=5"),
        ("Content-Type", "application/x-protobuf"),
        ("Content-Encoding", "gzip"),
        ("Content-Length", "12"),
        ("User-Agent", "OTel-OTLP-Exporter-Python/1.37.0"),
    ]
    assert forward.forwardable(headers) == headers[6:]


# --- the answer, and what is not forwarded ----------------------------------


def test_a_rejected_post_is_recorded_and_not_forwarded(tmp_path):
    # `SPEC.md` §4.3: forwarding it would invent traffic the exporter never
    # aimed at the Collector.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        status, _, _ = post(port, "/v1/metrics", JSON_BODY)
    assert status == 404
    assert spy.calls == []
    assert (raw.parent / "rejected" / "0001.body").read_bytes() == JSON_BODY


def test_the_answer_does_not_depend_on_the_forward(tmp_path):
    # `SPEC.md` §4.3: the sink's 200 means "recorded". It has never meant
    # "understood" and it must not start meaning "re-encoded".
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    refusing = Refusing()
    with tee(raw, refusing) as (_, port):
        status, answer, answer_headers = post(
            port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"}
        )
    assert (status, answer) == (200, b"")
    assert answer_headers["Content-Type"] == "application/x-protobuf"
    assert refusing.calls == 1


# --- a forward that fails loses nothing and is not silent -------------------


def test_a_failed_forward_is_recorded_in_the_manifest_and_the_capture_stands(
    tmp_path, capsys
):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    seen: list[manifest.ForwardEntry] = []
    with tee(raw, Refusing(), after_forward=seen.append) as (recorder, port):
        post(port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"})

    # The bytes are untouched and still verify.
    assert (raw / "0001.body").read_bytes() == PROTOBUF
    assert cli.verify(tmp_path / "captures") == 0
    capsys.readouterr()

    # The failure is in the manifest, naming the body it concerned.
    document = manifest.read(raw.parent)
    assert document[manifest.FORWARDS] == [
        {
            "error": "ConnectionRefusedError: [Errno 111] Connection refused",
            "file": "raw/0001.body",
        }
    ]
    # And visible through the seam, which is how `zoo capture` prints it.
    assert [entry.file for entry in seen] == ["raw/0001.body"]
    assert recorder.failed_forwards == seen


def test_a_collector_that_answers_an_error_status_is_a_failed_forward(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent, status=503)
    with tee(raw, spy) as (recorder, port):
        post(port, "/v1/traces", PROTOBUF)
    assert manifest.read(raw.parent)[manifest.FORWARDS] == [
        {"file": "raw/0001.body", "status": 503}
    ]
    assert [entry.status for entry in recorder.failed_forwards] == [503]


def test_a_forward_that_succeeded_is_recorded_too(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (recorder, port):
        post(port, "/v1/traces", PROTOBUF)
        post(port, "/v1/traces", JSON_BODY)
    assert manifest.read(raw.parent)[manifest.FORWARDS] == [
        {"file": "raw/0001.body", "status": 200},
        {"file": "raw/0002.body", "status": 200},
    ]
    assert recorder.failed_forwards == []


def test_a_sink_with_no_forward_at_all_records_as_before(tmp_path):
    # `zoo sink` is A1's sink and stays A1's sink: no forward, no `forwards`.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with tee(raw, None) as (_, port):
        post(port, "/v1/traces", PROTOBUF)
    document = manifest.read(raw.parent)
    assert manifest.FORWARDS not in document
    assert document["bodies"] == [
        {
            "bytes": len(PROTOBUF),
            "file": "raw/0001.body",
            "sha256": manifest.digest(PROTOBUF),
        }
    ]


# --- the real forward, over a real socket ------------------------------------


def test_the_http_forward_delivers_the_same_bytes_to_a_real_listener(tmp_path):
    """`HttpForward` into a second sink: no Collector, but a real socket.

    The second sink is the json sink's recorder (`SPEC.md` §4.5) with the
    Collector taken out of the middle, so what lands in `json/0001.json` is the
    protobuf rather than JSON. That is deliberate: what is under test here is
    that `HttpForward` moves bytes and headers unchanged, and the thing that
    proves the re-encoding is `test_collector_real.py`.
    """
    run = tmp_path / "captures" / "z4" / "run-1"
    downstream = sink.Recorder(
        run / "json",
        now=Clock(),
        rejected=run / sink.REJECTED_JSON_DIR,
        body_suffix=sink.JSON_SUFFIX,
    )
    server = sink.make_server(downstream, host="127.0.0.1", port=0)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    try:
        forwarder = forward.HttpForward("127.0.0.1", server.server_address[1])
        assert forwarder.endpoint.endswith(str(server.server_address[1]))
        with tee(run / "raw", forwarder) as (_, port):
            post(
                port,
                "/v1/traces",
                GZIP_BODY,
                {
                    "Content-Type": "application/json",
                    "Content-Encoding": "gzip",
                    "User-Agent": "OTel-OTLP-Exporter-Python/1.37.0",
                },
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=TIMEOUT)
        assert not thread.is_alive()

    assert (run / "json" / "0001.json").read_bytes() == GZIP_BODY
    delivered = json.loads((run / "json" / "0001.headers.json").read_text())
    pairs = {name.lower(): value for name, value in delivered["headers"]}
    assert pairs["content-type"] == "application/json"
    assert pairs["content-encoding"] == "gzip"
    assert pairs["user-agent"] == "OTel-OTLP-Exporter-Python/1.37.0"
    assert pairs["host"] == f"127.0.0.1:{server.server_address[1]}"
    assert delivered["path"] == "/v1/traces"
    # One manifest for the run, carrying both sinks' bodies (`SPEC.md` §4.5).
    assert [entry["file"] for entry in manifest.read(run)["bodies"]] == [
        "raw/0001.body",
        "json/0001.json",
    ]
    assert manifest.read(run)[manifest.FORWARDS] == [
        {"file": "raw/0001.body", "status": 200}
    ]
    assert cli.verify(tmp_path / "captures") == 0


def test_the_http_forward_raises_when_nothing_is_listening(tmp_path):
    # Bind a port, learn its number, give it back: nothing is there now.
    server = sink.make_server(
        sink.Recorder(tmp_path / "raw", now=Clock()), host="127.0.0.1", port=0
    )
    port = server.server_address[1]
    server.server_close()
    with pytest.raises(OSError):
        forward.HttpForward("127.0.0.1", port, timeout=1.0)(
            "POST", "/v1/traces", [], b"x"
        )
