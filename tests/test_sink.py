"""The sink records bytes and nothing else (`SPEC.md` §3).

Every test here drives a real `http.server` over a real socket, because the
thing under test is what arrives on a socket. Two rules make that deterministic
rather than flaky:

- the listener binds `127.0.0.1` on **port 0**, so the OS picks a free port and
  the suite can never collide with something already listening on 4318;
- nothing sleeps. The one concurrency test holds two POSTs in flight through
  the `before_record` / `after_record` seams (`SPEC.md` §3.6) and an
  `Event`/`Barrier` pair, so receipt order is *forced* rather than hoped for. A
  `time.sleep` in a concurrency test is a race with whatever machine runs it
  next.

The receipt time is always a value a test chose, through the injected `now`.
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

from spanweave_zoo import cli, manifest, sink

# Deliberately binary, with a NUL and a 0xff in it: a protobuf export is not
# text, and a sink that round-trips only text is broken in the one case that
# matters (the Python OTLP/HTTP exporter sends protobuf).
PROTOBUF = bytes.fromhex("0a8a010a4c0a2b0a0d736572766963652e6e616d65") + bytes(
    [0x00, 0xFF, 0x1F, 0x8B, 0x0A]
)
JSON_BODY = b'{"resourceSpans":[{"resource":{"attributes":[]},"scopeSpans":[]}]}'
# `mtime=0` so the compressed bytes are the same on every machine and run.
GZIP_BODY = gzip.compress(JSON_BODY, mtime=0)

TIMEOUT = 5.0

# What the test's own clock would have said when the run ended. The manifest is
# assembled at the end of a run (`SPEC.md` §5.5), and in a test that moment is
# a value the test chose, like every other timestamp here.
ENDED = "2026-10-09T12:09:00+00:00"


class Clock:
    """The injected `now`: a counter, so a recorded time is a chosen value."""

    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


@contextmanager
def running(raw: Path, **kwargs):
    """A sink on a port the OS picked, shut down and joined on the way out."""
    recorder = sink.Recorder(raw, now=kwargs.pop("now", None) or Clock(), **kwargs)
    server = sink.make_server(recorder, host="127.0.0.1", port=0)
    # A short poll interval so `shutdown()` returns promptly: the default half
    # second is a tenth of this suite's runtime, not a correctness matter.
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
        # The run is over, so the manifest is assembled from the journal --
        # exactly as `zoo sink` does it in its own `finally` (`SPEC.md` §5.5).
        # A capture is complete or it is not verified, and these tests verify.
        manifest.finish(recorder.run, ended_at=ENDED)


def post(port: int, path: str, body: bytes, headers: dict[str, str] | None = None):
    """One POST, with the connection closed before we look at the result."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.request("POST", path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        connection.close()


def send_octets(port: int, head: bytes, body: bytes = b"") -> bytes:
    """One request written to the socket as octets, and the answer read back.

    `post` goes through `http.client`, which composes the head itself and
    refuses a header value it considers illegal -- so it cannot send the heads
    these tests are about. Here the test chooses every octet, which is the
    only way to assert what the recorder wrote is what the client sent. Each
    head below says `Connection: close`, so the read ends at EOF rather than
    on a timeout.
    """
    with socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT) as client:
        client.sendall(head + body)
        answer = b""
        while chunk := client.recv(4096):
            answer += chunk
    return answer


def body_of(raw: Path, number: int = 1) -> bytes:
    return (raw / f"{number:04d}.body").read_bytes()


def headers_of(raw: Path, number: int = 1):
    return json.loads((raw / f"{number:04d}.headers.json").read_text())


def head_of(raw: Path, number: int = 1) -> bytes:
    return (raw / f"{number:04d}.headers.raw").read_bytes()


# --- the bytes come back byte for byte -------------------------------------


def test_a_protobuf_body_round_trips_byte_for_byte(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, answer, answer_headers = post(
            port,
            "/v1/traces",
            PROTOBUF,
            {"Content-Type": "application/x-protobuf"},
        )
    assert status == 200
    assert answer == b""
    assert answer_headers["Content-Type"] == "application/x-protobuf"
    assert body_of(raw) == PROTOBUF
    assert headers_of(raw)["bytes"] == len(PROTOBUF)


def test_a_json_body_round_trips_byte_for_byte(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, answer_headers = post(
            port, "/v1/traces", JSON_BODY, {"Content-Type": "application/json"}
        )
    assert status == 200
    assert answer_headers["Content-Type"] == "application/json"
    assert body_of(raw) == JSON_BODY


def test_a_gzip_body_is_written_still_compressed(tmp_path):
    # THE case. `SPEC.md` §2.2: a gzipped body is stored gzipped. A sink that
    # decompresses on the way in is "improving" the capture, and the capture
    # then no longer says what the exporter sent.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, _ = post(
            port,
            "/v1/traces",
            GZIP_BODY,
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
        )
    assert status == 200
    written = body_of(raw)
    assert written == GZIP_BODY, "the gzip bytes were not stored as received"
    assert written != JSON_BODY, "the sink decompressed the body before writing"
    assert written[:2] == b"\x1f\x8b", "the stored body is not a gzip stream"
    # And the capture says it is gzip, because the request did.
    assert ["Content-Encoding", "gzip"] in headers_of(raw)["headers"]
    # It is still readable as gzip -- by whoever decides to decode it, which
    # is never the sink.
    assert gzip.decompress(written) == JSON_BODY


# --- the header octets are the record (`SPEC.md` §2.3) ----------------------

# A well-formed head, written by the test octet by octet. `Content-Length`
# and `Connection` come before anything else a test adds, so a head the stdlib
# stops parsing part-way through still frames its body and still closes.
HEAD = (
    b"POST /v1/traces HTTP/1.1\r\n"
    b"Host: 127.0.0.1\r\n"
    b"Content-Type: application/x-protobuf\r\n"
    b"Content-Length: 5\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)

# The same head with a **bare CR** inside a header value -- one legal-looking
# `X-Weird: a\rb` line that HTTP forbids and real clients still emit. The
# stdlib's parse cannot represent it: `email`'s header parser splits on a bare
# CR, so it sees `X-Weird: a` and then a line that is not a header at all.
BARE_CR_HEAD = HEAD[: -len(b"\r\n")] + b"X-Weird: a\rb\r\n" + b"\r\n"


def test_the_headers_raw_file_is_the_octets_the_client_sent(tmp_path):
    # `SPEC.md` §2.3: `NNNN.headers.raw` is the unmodified record -- the
    # request line and the header block as received, CRLFs intact, up to and
    # including the blank line that ends them.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        answer = send_octets(port, HEAD, b"hello")
    assert answer.startswith(b"HTTP/1.1 200"), answer
    assert head_of(raw) == HEAD
    assert body_of(raw) == b"hello"


def test_a_bare_cr_in_a_header_value_is_in_raw_and_not_in_json(tmp_path):
    # The degenerate head, and the reason the raw file exists. The octets are
    # kept; the stdlib's parse beside them cannot carry them, and says so by
    # not carrying them -- rather than the capture quietly becoming a record of
    # what Python could represent.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        answer = send_octets(port, BARE_CR_HEAD, b"hello")
    assert answer.startswith(b"HTTP/1.1 200"), answer

    recorded = head_of(raw)
    assert recorded == BARE_CR_HEAD, "the head was reconstructed, not recorded"
    assert b"X-Weird: a\rb\r\n" in recorded

    parsed = headers_of(raw)["headers"]
    assert ["X-Weird", "a"] in parsed, "the stdlib's parse is not what it was"
    assert ["X-Weird", "a\rb"] not in parsed
    assert all("\r" not in value for _, value in parsed)
    # And the bytes after the head are still the body: recording the octets
    # reads nothing the request parser did not already read.
    assert body_of(raw) == b"hello"


def test_each_request_on_one_connection_gets_its_own_head(tmp_path):
    # A keep-alive connection carries several requests, so the recording is
    # per request and not per connection: head 2 is head 2, not heads 1 and 2
    # concatenated, and no body is in either.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    bodies = (b"one", b"a longer second body")
    with running(raw) as (_, port):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
        try:
            for body in bodies:
                connection.request(
                    "POST",
                    "/v1/traces",
                    body=body,
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                assert response.status == 200
                assert response.read() == b""
        finally:
            connection.close()

    first, second = head_of(raw, 1), head_of(raw, 2)
    assert first != second, "both requests recorded the same head"
    paired = zip((first, second), bodies, strict=True)
    for number, (head, body) in enumerate(paired, start=1):
        assert head.startswith(b"POST /v1/traces HTTP/1.1\r\n")
        assert head.endswith(b"\r\n\r\n")
        assert head.count(b"POST /v1/traces") == 1
        assert head.count(b"\r\n\r\n") == 1
        assert body not in head, "the body landed in the head"
        assert body_of(raw, number) == body
        assert f"Content-Length: {len(body)}\r\n".encode() in head


def test_a_rejected_post_keeps_its_head_too(tmp_path):
    # `SPEC.md` §3.4: a POST aimed at another path is recorded anyway, and the
    # octets of its head are as much of that record as its bytes are.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        answer = send_octets(
            port, HEAD.replace(b"/v1/traces", b"/v1/metrics"), b"hello"
        )
    assert answer.startswith(b"HTTP/1.1 404"), answer
    rejected = raw.parent / sink.REJECTED_DIR
    assert head_of(rejected) == HEAD.replace(b"/v1/traces", b"/v1/metrics")
    assert body_of(rejected) == b"hello"


def test_the_manifest_covers_the_head_it_was_never_told_about(tmp_path):
    # The carry-over from A3b: `files` is a walk of the run directory, so a
    # file no recorder announced is covered all the same -- and a capture whose
    # head octets nobody hashed would be a capture `zoo verify` could not check
    # (`SPEC.md` §5.6).
    raw = _capture(tmp_path)
    listed = {entry["file"] for entry in manifest.read(raw.parent)[manifest.FILES]}
    assert "raw/0001.headers.raw" in listed
    assert "rejected/0001.headers.raw" in listed
    assert manifest.problems(raw.parent) == []


# --- receipt order, with two POSTs genuinely in flight ----------------------


def test_two_posts_in_flight_are_numbered_in_receipt_order(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    first_body, second_body = b"first-in", b"second-in"

    both_in_flight = threading.Barrier(2, timeout=TIMEOUT)
    first_recorded = threading.Event()

    def before_record(body: bytes) -> None:
        # Both requests reach here before either is numbered: the barrier is
        # what proves they were in flight at the same time.
        both_in_flight.wait()
        if body == second_body:
            # ... and the second may not be numbered until the first is on
            # disk. Only the first can set this, so the order is forced.
            assert first_recorded.wait(TIMEOUT), "the first POST was never recorded"

    def after_record(entry: manifest.BodyEntry) -> None:
        first_recorded.set()

    results: dict[bytes, int] = {}
    with running(raw, before_record=before_record, after_record=after_record) as (
        _,
        port,
    ):

        def send(body: bytes) -> None:
            results[body] = post(port, "/v1/traces", body)[0]

        threads = [
            threading.Thread(target=send, args=(b,)) for b in (first_body, second_body)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=TIMEOUT)
            assert not thread.is_alive()

    assert results == {first_body: 200, second_body: 200}
    assert body_of(raw, 1) == first_body
    assert body_of(raw, 2) == second_body
    # The manifest carries the same order, and no body is listed twice.
    listed = [entry["file"] for entry in manifest.read(raw.parent)["bodies"]]
    assert listed == ["raw/0001.body", "raw/0002.body"]


# --- `zoo verify` on what the sink wrote ------------------------------------


def _capture(tmp_path: Path) -> Path:
    """One capture of three bodies, written by the sink itself."""
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        post(port, "/v1/traces", PROTOBUF, {"Content-Type": "application/x-protobuf"})
        post(port, "/v1/traces", GZIP_BODY, {"Content-Encoding": "gzip"})
        post(port, "/v1/metrics", JSON_BODY, {"Content-Type": "application/json"})
    return raw


def test_verify_passes_on_a_capture_the_sink_wrote(tmp_path, capsys):
    _capture(tmp_path)
    assert cli.verify(tmp_path / "captures") == 0
    assert "3 body" in capsys.readouterr().out


def test_verify_fails_after_one_byte_of_one_body_changes(tmp_path, capsys):
    raw = _capture(tmp_path)
    target = raw / "0001.body"
    tampered = bytearray(target.read_bytes())
    tampered[0] ^= 0x01  # one bit of one byte
    target.write_bytes(bytes(tampered))

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "raw/0001.body" in out
    assert "sha256" in out


def test_verify_fails_when_a_listed_body_is_missing(tmp_path, capsys):
    raw = _capture(tmp_path)
    (raw / "0002.body").unlink()
    assert cli.verify(tmp_path / "captures") == 1
    assert "raw/0002.body" in capsys.readouterr().out


def test_verify_refuses_a_run_whose_manifest_is_unreadable(tmp_path, capsys):
    raw = _capture(tmp_path)
    (raw.parent / manifest.MANIFEST_NAME).write_text("{not json")
    assert cli.verify(tmp_path / "captures") == 1
    assert "MANIFEST.json" in capsys.readouterr().out


# --- any other path: 404, and still recorded --------------------------------


def test_an_unknown_path_is_404_and_still_recorded(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, answer, answer_headers = post(
            port, "/v1/metrics", JSON_BODY, {"Content-Type": "application/json"}
        )
    assert status == 404
    assert answer == b""
    assert answer_headers["Content-Type"] == "application/json"

    rejected = raw.parent / "rejected"
    assert body_of(rejected) == JSON_BODY, "a 404 threw the exporter's bytes away"
    assert headers_of(rejected)["path"] == "/v1/metrics"
    # Rejected bodies get their own counter, so `raw/NNNN` stays the
    # contiguous sequence `json/NNNN` is paired with (`SPEC.md` §3.4).
    assert not (raw / "0001.body").exists()
    assert manifest.read(raw.parent)["bodies"][0]["file"] == "rejected/0001.body"


def test_the_two_counters_are_independent(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        post(port, "/v1/logs", b"a")
        post(port, "/v1/traces", b"b")
        post(port, "/v1/logs", b"c")
        post(port, "/v1/traces", b"d")
    assert body_of(raw, 1) == b"b"
    assert body_of(raw, 2) == b"d"
    assert body_of(raw.parent / "rejected", 1) == b"a"
    assert body_of(raw.parent / "rejected", 2) == b"c"


def test_a_path_with_a_query_string_is_not_the_traces_path(tmp_path):
    # `SPEC.md` §3.2: that exact path, no other. The target is recorded
    # verbatim rather than parsed into pieces.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, _ = post(port, "/v1/traces?compress=gzip", b"x")
    assert status == 404
    assert headers_of(raw.parent / "rejected")["path"] == "/v1/traces?compress=gzip"


# --- the headers are the record ---------------------------------------------


def test_the_headers_file_keeps_every_header_in_order_with_repeats(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    connection = None
    with running(raw) as (_, port):
        # `http.client` keeps repeated headers, which a JSON object could not.
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
        connection.putrequest("POST", "/v1/traces")
        connection.putheader("Content-Type", "application/x-protobuf")
        connection.putheader("X-Zoo", "one")
        connection.putheader("X-Zoo", "two")
        connection.putheader("Content-Length", str(len(PROTOBUF)))
        connection.endheaders()
        connection.send(PROTOBUF)
        assert connection.getresponse().status == 200
        connection.close()

    recorded = headers_of(raw)
    assert recorded["method"] == "POST"
    assert recorded["path"] == "/v1/traces"
    pairs = [tuple(pair) for pair in recorded["headers"]]
    assert pairs.count(("X-Zoo", "one")) == 1
    assert pairs.count(("X-Zoo", "two")) == 1
    assert pairs.index(("X-Zoo", "one")) < pairs.index(("X-Zoo", "two"))
    assert ("Content-Type", "application/x-protobuf") in pairs


def test_the_receipt_time_is_the_injected_clocks_value(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    clock = Clock()
    with running(raw, now=clock) as (_, port):
        post(port, "/v1/traces", b"one")
        post(port, "/v1/traces", b"two")
    assert headers_of(raw, 1)["received_at"] == "2026-10-09T12:00:01+00:00"
    assert headers_of(raw, 2)["received_at"] == "2026-10-09T12:00:02+00:00"
    assert clock.ticks == 2, "the sink read its clock more than once per request"


def test_every_file_the_sink_writes_is_sorted_json(tmp_path):
    raw = _capture(tmp_path)
    for path in [raw / "0001.headers.json", raw.parent / manifest.MANIFEST_NAME]:
        text = path.read_text()
        assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"


# --- degenerate requests ----------------------------------------------------


def test_an_empty_body_is_recorded_like_any_other(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, _ = post(
            port, "/v1/traces", b"", {"Content-Type": "application/json"}
        )
    assert status == 200
    assert body_of(raw) == b""
    assert headers_of(raw)["bytes"] == 0
    assert manifest.read(raw.parent)["bodies"][0]["bytes"] == 0


def test_a_post_with_no_content_length_is_recorded_as_zero_bytes(tmp_path):
    # `SPEC.md` §3.7: the sink reads the framing it was given and does not
    # guess one it was not. What it could see is what the capture says it saw.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with (
        running(raw) as (_, port),
        socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT) as client,
    ):
        client.sendall(
            b"POST /v1/traces HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: application/x-protobuf\r\n"
            b"Connection: close\r\n"
            b"\r\n"
        )
        answer = b""
        while chunk := client.recv(4096):
            answer += chunk
    assert answer.startswith(b"HTTP/1.1 200"), answer
    assert body_of(raw) == b""
    recorded = headers_of(raw)
    assert recorded["bytes"] == 0
    assert all(name != "Content-Length" for name, _ in recorded["headers"])


def test_a_request_with_no_content_type_gets_none_echoed_back(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, answer_headers = post(port, "/v1/traces", b"anything")
    assert status == 200
    assert "Content-Type" not in answer_headers
    assert body_of(raw) == b"anything"


def test_a_body_that_lies_about_its_encoding_is_still_recorded(tmp_path):
    # `Content-Encoding: gzip` on bytes that are not gzip. A receiver would
    # refuse this; the sink records it, and the audit (§7) reports the refusal.
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    with running(raw) as (_, port):
        status, _, _ = post(
            port, "/v1/traces", b"not gzip at all", {"Content-Encoding": "gzip"}
        )
    assert status == 200
    assert body_of(raw) == b"not gzip at all"


# --- the sink never edits a capture -----------------------------------------


def test_the_sink_refuses_an_out_directory_that_already_holds_a_body(tmp_path):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    raw.mkdir(parents=True)
    (raw / "0001.body").write_bytes(b"an earlier run's bytes")
    with pytest.raises(sink.CaptureExists):
        sink.Recorder(raw, now=Clock())
    assert (raw / "0001.body").read_bytes() == b"an earlier run's bytes"


def test_the_sink_command_refuses_without_binding(tmp_path, capsys):
    raw = tmp_path / "captures" / "z4" / "run-1" / "raw"
    raw.mkdir(parents=True)
    (raw / "0004.body").write_bytes(b"bytes")
    # Port 1 would need privileges to bind: reaching the bind at all fails.
    assert cli.main(["sink", "--port", "1", "--out", str(raw)]) != 0
    assert "refus" in capsys.readouterr().err.lower()
