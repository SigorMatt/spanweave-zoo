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
import socket
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

# What the test's own clock would have said when the run ended (`SPEC.md` §5.5).
ENDED = "2026-10-09T12:09:00+00:00"


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
        self.calls: list[tuple[bytes, bytes]] = []
        self.on_disk: list[bytes | None] = []

    def __call__(self, head, body):
        self.calls.append((head, body))
        written = self.run / "raw" / f"{len(self.calls):04d}.body"
        self.on_disk.append(written.read_bytes() if written.exists() else None)
        return self.status


class Refusing:
    """A Collector that is not there."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, head, body):
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
        # The run is over: the manifest is assembled from the journals, the
        # way `zoo sink` and `zoo capture` assemble it (`SPEC.md` §5.5).
        manifest.finish(recorder.run, ended_at=ENDED)


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
    _, forwarded = spy.calls[0]
    assert forwarded == GZIP_BODY
    assert forwarded != JSON_BODY, "the tee decompressed on the way out"
    assert (raw / "0001.body").read_bytes() == forwarded


def test_a_protobuf_body_is_forwarded_as_protobuf(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"})
    assert spy.calls[0][1] == PROTOBUF


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


def test_the_forward_is_handed_the_recorded_head_octets(tmp_path):
    # A3g; run-2b review N-7 (F-b1). The seam is handed the head **as
    # recorded** -- the octets of `NNNN.headers.raw`, request line, `Host`,
    # repeats and all -- and never the stdlib's parse of it: what the
    # Collector is sent is decided from the record (`SPEC.md` §4.3).
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
    head, body = spy.calls[0]
    assert head == (raw / "0001.headers.raw").read_bytes()
    assert head.startswith(b"POST /v1/traces HTTP/1.1\r\n")
    assert b"X-Zoo: one\r\nX-Zoo: two\r\n" in head
    assert body == GZIP_BODY


# A head with hop-by-hop headers, a repeat, no space after one colon, a bare CR
# with header-shaped text after it, and `Host` not first: everything the
# forward must either keep octet for octet or change by `SPEC.md` §4.3's two
# rules and no others.
AWKWARD_HEAD = (
    b"POST /v1/traces HTTP/1.1\r\n"
    b"Content-Type: application/x-protobuf\r\n"
    b"Host: 127.0.0.1:4318\r\n"
    b"Connection: close\r\n"
    b"X-Zoo:one\r\n"
    b"X-Zoo: two\r\n"
    b"User-Agent: otel\rContent-Encoding: gzip\r\n"
    b"Keep-Alive: timeout=5\r\n"
    b"Content-Length: 5\r\n"
    b"\r\n"
)


def test_the_collectors_head_is_the_record_with_host_and_hop_by_hop_changed():
    assert forward.collector_head(AWKWARD_HEAD, "127.0.0.1:4320") == (
        b"POST /v1/traces HTTP/1.1\r\n"
        b"Content-Type: application/x-protobuf\r\n"
        b"Host: 127.0.0.1:4320\r\n"
        b"X-Zoo:one\r\n"
        b"X-Zoo: two\r\n"
        b"User-Agent: otel\rContent-Encoding: gzip\r\n"
        b"Content-Length: 5\r\n"
        b"\r\n"
    )


@pytest.mark.parametrize("name", sorted(forward.HOP_BY_HOP))
def test_every_hop_by_hop_header_line_is_dropped_in_any_case(name):
    head = (
        b"POST /v1/traces HTTP/1.1\r\nHost: a\r\n"
        + name.upper().encode()
        + b": x\r\nContent-Length: 0\r\n\r\n"
    )
    assert forward.collector_head(head, "b:1") == (
        b"POST /v1/traces HTTP/1.1\r\nHost: b:1\r\nContent-Length: 0\r\n\r\n"
    )


def test_a_head_with_no_crlf_goes_to_the_collector_as_it_arrived():
    # An LF-only head is one line on `SPEC.md` §2.3's split: it has no `Host`
    # line to substitute and no hop-by-hop line to drop, so it goes as it
    # came -- exactly as `NNNN.headers.json` lists no header in it and the
    # replay changes nothing in it (§6.2).
    head = b"POST /v1/traces HTTP/1.1\nHost: a\nConnection: close\n\n"
    assert forward.collector_head(head, "b:1") == head


def test_the_request_line_is_forwarded_as_received(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    spy = Spy(raw.parent)
    with tee(raw, spy) as (_, port):
        post(port, "/v1/traces", PROTOBUF)
    head, _ = spy.calls[0]
    assert head.startswith(b"POST /v1/traces HTTP/1.1\r\n")


def test_a_cr_injected_header_does_not_reach_the_collector_as_a_header(tmp_path):
    """`SPEC.md` §4.3, A3g; run-2b review N-7 (F-b1), red before A3g.

    The tee used to forward the stdlib's parse, which splits
    `User-Agent: otel<CR>Content-Encoding: gzip` into two headers -- so a
    Collector was told the body was gzipped when the record (A3f's split) says
    the request declared no encoding at all, and its `400` was recorded
    against a body whose record has none. The forward now sends the recorded
    octets: what the downstream receiver gets is the captured head with only
    the `Host` line and the hop-by-hop lines changed, and the injected text is
    still inside the `User-Agent` value it arrived in.
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
    collector_port = server.server_address[1]
    try:
        forwarder = forward.HttpForward("127.0.0.1", collector_port)
        with tee(run / "raw", forwarder) as (_, port):
            with socket.create_connection(
                ("127.0.0.1", port), timeout=TIMEOUT
            ) as client:
                client.sendall(AWKWARD_HEAD + b"hello")
                answer = b""
                while chunk := client.recv(4096):
                    answer += chunk
            assert answer.startswith(b"HTTP/1.1 200"), answer
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=TIMEOUT)

    recorded = (run / "raw" / "0001.headers.raw").read_bytes()
    assert recorded == AWKWARD_HEAD
    delivered = (run / "json" / "0001.headers.raw").read_bytes()
    assert b"\r\nContent-Encoding: gzip\r\n" not in delivered
    assert b"User-Agent: otel\rContent-Encoding: gzip\r\n" in delivered
    split = json.loads((run / "json" / "0001.headers.json").read_text())
    names = [name.lower() for name, _ in split["headers"]]
    assert "content-encoding" not in names
    assert names.count("user-agent") == 1
    assert (run / "json" / "0001.json").read_bytes() == b"hello"
    assert delivered == forward.collector_head(recorded, f"127.0.0.1:{collector_port}")


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
    assert not (raw.parent / manifest.FORWARD_JOURNAL_NAME).exists()
    assert document["bodies"] == [
        {
            "bytes": len(PROTOBUF),
            # This POST declared neither, and the zoo has none of its own to
            # invent (`SPEC.md` §5.4).
            "content_encoding": None,
            "content_type": None,
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
            b"POST /v1/traces HTTP/1.1\r\nContent-Length: 1\r\n\r\n", b"x"
        )
