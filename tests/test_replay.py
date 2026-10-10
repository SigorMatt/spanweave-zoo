"""The replayer: the same bytes and the same head, again (`SPEC.md` §6).

Two kinds of capture are replayed here, and both are deliberate.

The **committed capture** under `tests/fixtures/capture/` is the replay source
wherever it fits: it is a real one -- a protobuf body through the real tee, both
sides, both headers files and the manifest the run assembled (`SPEC.md` §5.6)
-- so the byte-identity claim is made against bytes a real exporter sent rather
than against bytes a test minted to be easy. It is never written to.

The **crafted** captures are recorded here, through the real sink, by sending
the head octets over a socket: that is the only way to get a head into a
capture that the stdlib's parse cannot represent, and a bare CR in a header
value is exactly the case `NNNN.headers.raw` exists for (`SPEC.md` §2.3). A
test may put octets on a socket; `spanweave_zoo/` may not, outside the seams
the spec names.

Nothing here sleeps. `--timing`'s sleep is an injected seam (`SPEC.md` §6.3),
so the recorded gaps a test asserts are values the test's own clock chose and
the suite waits for none of them.
"""

from __future__ import annotations

import gzip
import json
import socket
import threading
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from spanweave_zoo import cli, manifest, replay, sink

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "capture"

TIMEOUT = 5.0

# What a crafted run's clock says when it ends. The value is the test's.
ENDED = "2026-10-09T12:09:00+00:00"

JSON_BODY = b'{"resourceSpans":[]}'
GZIP_BODY = gzip.compress(JSON_BODY, mtime=0)


class Clock:
    """The receipt times a crafted capture will carry, in order.

    A list and not a counter, because `--timing` asserts the **gaps** between
    them: a clock a test wrote is how a recorded four-second gap becomes
    something the suite can check without waiting four seconds (`SPEC.md` §6.3).
    """

    def __init__(self, *moments: str) -> None:
        self.moments = list(moments)
        self.reads = 0

    def __call__(self) -> str:
        moment = self.moments[min(self.reads, len(self.moments) - 1)]
        self.reads += 1
        return moment


class Sleeps:
    """The `sleep` seam, written down instead of waited through."""

    def __init__(self) -> None:
        self.slept: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept.append(seconds)


class Spy:
    """A `send` that writes down what it was handed and answers in order."""

    def __init__(self, *statuses: int) -> None:
        self.statuses = list(statuses) or [200]
        self.calls: list[tuple[str, str, list[tuple[str, str]], bytes]] = []

    def __call__(self, method, target, headers, body):
        self.calls.append((method, target, list(headers), body))
        return self.statuses[min(len(self.calls) - 1, len(self.statuses) - 1)]


class _Scripted(BaseHTTPRequestHandler):
    """A receiver that answers a list of statuses and keeps every body."""

    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # http.server's own naming
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        server = self.server
        statuses: list[int] = server.statuses  # type: ignore[attr-defined]
        bodies: list[bytes] = server.bodies  # type: ignore[attr-defined]
        bodies.append(body)
        status = statuses[min(len(bodies) - 1, len(statuses) - 1)]
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def scripted(*statuses: int):
    """A receiver on port 0 that answers `statuses`, in order."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Scripted)
    server.statuses = list(statuses) or [200]  # type: ignore[attr-defined]
    server.bodies = []  # type: ignore[attr-defined]
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    try:
        yield server, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=TIMEOUT)


@contextmanager
def destination(raw: Path, clock: Clock | None = None):
    """A real `zoo sink` on port 0: the replay lands in a second capture.

    The zoo's own recorder is the destination on purpose. It keeps the head
    octets of every request it answers (`SPEC.md` §2.3), so "the replayed head
    is the captured head" is checked against what actually went over a socket
    rather than against what the replayer says it sent.
    """
    recorder = sink.Recorder(raw, now=clock or Clock("2026-10-09T13:00:00+00:00"))
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


def head_octets(
    port: int,
    body: bytes,
    *,
    target: str = sink.TRACES_PATH,
    extra: bytes = b"",
) -> bytes:
    """One request's head, as a client would put it on the wire."""
    return (
        f"POST {target} HTTP/1.1\r\n".encode("latin-1")
        + f"Host: 127.0.0.1:{port}\r\n".encode("latin-1")
        + b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n".encode("latin-1")
        + extra
        + b"\r\n"
    )


def crafted(run: Path, requests, clock: Clock) -> Path:
    """Record a capture from head octets, through the real sink.

    `requests` is a sequence of `(head, body)`; `head` is called with the port
    the sink got, because a request's `Host` names the destination it was
    actually sent to. Returns the run directory, manifest assembled.
    """
    with destination(run / "raw", clock) as (recorder, port):
        for build_head, body in requests:
            connection = socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT)
            try:
                connection.sendall(build_head(port) + body)
                assert connection.recv(64).startswith(b"HTTP/1.1 200"), (
                    "the sink did not answer the crafted request"
                )
            finally:
                connection.close()
        assert recorder.raw.is_dir()
    manifest.label(
        run, kind="recorded", collector_version="0.162.0", started_at=clock.moments[0]
    )
    manifest.finish(run, ended_at=ENDED)
    return run


def sent_head(run: Path, number: int = 1) -> bytes:
    return (run / "raw" / f"{number:04d}.headers.raw").read_bytes()


def sent_body(run: Path, number: int = 1) -> bytes:
    return (run / "raw" / f"{number:04d}.body").read_bytes()


def with_host(head: bytes, port: int) -> bytes:
    """`head` with its `Host` line pointing at `port` instead.

    The one line a replay is *expected* to differ in: the destination has
    changed, and `SPEC.md` §4.3 names `Host` as one of the two exceptions to
    byte-identity. Everything else in the head must match octet for octet.
    """
    lines = head.split(b"\r\n")
    return b"\r\n".join(
        f"Host: 127.0.0.1:{port}".encode("latin-1")
        if line.lower().startswith(b"host:")
        else line
        for line in lines
    )


# --- the committed capture, replayed -----------------------------------------


def test_a_replayed_body_is_the_bytes_the_capture_recorded(tmp_path):
    # `SPEC.md` §6.1 against a real capture: a protobuf body the Python
    # exporter actually sent, re-sent and recorded again by the zoo's own sink.
    with destination(tmp_path / "again" / "raw") as (_, port):
        outcomes = replay.replay(
            FIXTURE,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert [outcome.status for outcome in outcomes] == [200]
    assert sent_body(tmp_path / "again") == sent_body(FIXTURE)
    assert all(outcome.delivered for outcome in outcomes)


def test_a_replayed_head_is_the_captured_octets_with_only_the_host_changed(tmp_path):
    """`SPEC.md` §6.2: the head goes out as the octets had it.

    This is the test that fails if the replayer is built on
    `NNNN.headers.json` -- the stdlib's parse -- rather than on the octets
    beside it. Here the two agree, which is why the bare-CR capture below
    exists; what this one holds is that nothing else in the head moved:
    not the order, not the request line, not a single value.
    """
    with destination(tmp_path / "again" / "raw") as (_, port):
        replay.replay(
            FIXTURE,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert sent_head(tmp_path / "again") == with_host(sent_head(FIXTURE), port)


def test_the_json_side_sends_the_collectors_re_encoding(tmp_path):
    # `SPEC.md` §6.1: `--json` is the other form of the same export (§2.4).
    again = tmp_path / "again"
    with destination(again / "raw") as (_, port):
        outcomes = replay.replay(
            FIXTURE,
            source=replay.JSON,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert [outcome.file for outcome in outcomes] == ["json/0001.json"]
    assert sent_body(again) == (FIXTURE / "json" / "0001.json").read_bytes()
    assert sent_head(again) == with_host(
        (FIXTURE / "json" / "0001.headers.raw").read_bytes(), port
    )


def test_the_replayer_sends_through_the_tees_own_forward(tmp_path):
    # `SPEC.md` §6.2: re-sending captured bytes is one act, and the replayer
    # does not get a second implementation of it to improve.
    from spanweave_zoo import forward

    assert isinstance(replay.sender("127.0.0.1", 1), forward.HttpForward)


# --- order, encoding, and the bytes in between -------------------------------


def test_the_bodies_go_out_in_the_order_the_capture_recorded_them(tmp_path):
    # `SPEC.md` §6.1: receipt order, read out of the manifest rather than
    # re-derived by sorting a directory.
    source = crafted(
        tmp_path / "source",
        [
            (lambda port: head_octets(port, b"first"), b"first"),
            (lambda port: head_octets(port, b"second"), b"second"),
            (lambda port: head_octets(port, b"third"), b"third"),
        ],
        Clock(
            "2026-10-09T12:00:00+00:00",
            "2026-10-09T12:00:04+00:00",
            "2026-10-09T12:00:06+00:00",
        ),
    )
    spy = Spy(200)
    outcomes = replay.replay(source, source=replay.RAW, send=spy, log=lambda line: None)
    assert [outcome.file for outcome in outcomes] == [
        "raw/0001.body",
        "raw/0002.body",
        "raw/0003.body",
    ]
    assert [body for _, _, _, body in spy.calls] == [b"first", b"second", b"third"]
    assert [target for _, target, _, _ in spy.calls] == [sink.TRACES_PATH] * 3


def test_a_gzipped_body_goes_out_gzipped_with_the_encoding_it_declared(tmp_path):
    """`SPEC.md` §6.1: nothing here decompresses, and nothing here drops a
    header that says what the bytes are.

    A replayer that decoded the body, or that sent it without its
    `Content-Encoding`, would be handing the receiver something no exporter
    sent -- and the receiver would have no way to know.
    """
    source = crafted(
        tmp_path / "source",
        [
            (
                lambda port: head_octets(
                    port, GZIP_BODY, extra=b"Content-Encoding: gzip\r\n"
                ),
                GZIP_BODY,
            )
        ],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    with destination(tmp_path / "again" / "raw") as (_, port):
        replay.replay(
            source,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    again = tmp_path / "again"
    assert sent_body(again) == GZIP_BODY
    assert b"Content-Encoding: gzip\r\n" in sent_head(again)
    assert sent_head(again) == with_host(sent_head(source), port)


def test_head_joins_a_folded_value_as_it_arrived(tmp_path):
    # `SPEC.md` §6.2: a value that arrived folded arrived folded.
    method, target, headers = replay.head(
        b"POST /v1/traces HTTP/1.1\r\nX-Folded: one\r\n\ttwo\r\nHost: h\r\n\r\n"
    )
    assert (method, target) == ("POST", "/v1/traces")
    assert headers == [("X-Folded", "one\r\n\ttwo"), ("Host", "h")]


def test_head_keeps_every_header_in_order_repeats_included():
    # `SPEC.md` §4.3's rule, which §6.2 re-sends by: a dict would keep one.
    _, _, headers = replay.head(
        b"POST /v1/traces HTTP/1.1\r\nX-Twice: a\r\nX-Twice: b\r\n\r\n"
    )
    assert headers == [("X-Twice", "a"), ("X-Twice", "b")]


# --- `--timing` --------------------------------------------------------------


def test_timing_sleeps_the_recorded_gaps_through_the_injected_sleep(tmp_path):
    # `SPEC.md` §6.3: the gap before each body after the first, and no sleep
    # before the first. Four seconds then two, on a clock the test wrote.
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 3,
        Clock(
            "2026-10-09T12:00:00+00:00",
            "2026-10-09T12:00:04+00:00",
            "2026-10-09T12:00:06+00:00",
        ),
    )
    sleeps = Sleeps()
    outcomes = replay.replay(
        source,
        source=replay.RAW,
        send=Spy(200),
        timing=True,
        sleep=sleeps,
        log=lambda line: None,
    )
    assert sleeps.slept == [4.0, 2.0]
    assert [outcome.slept for outcome in outcomes] == [None, 4.0, 2.0]


def test_without_timing_nothing_sleeps(tmp_path):
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 2,
        Clock("2026-10-09T12:00:00+00:00", "2026-10-09T12:00:04+00:00"),
    )
    sleeps = Sleeps()
    replay.replay(
        source,
        source=replay.RAW,
        send=Spy(200),
        sleep=sleeps,
        log=lambda line: None,
    )
    assert sleeps.slept == []


def test_a_gap_it_cannot_compute_is_not_slept_and_is_said(tmp_path):
    """`SPEC.md` §6.3: not slept, not guessed, and not silent.

    The second body's `received_at` is not an ISO-8601 moment -- the sink wrote
    down what its clock said, and a capture carries what was written -- so
    there is no gap to sleep and the replay says so. The send still happens:
    the replayer's claim is about the bytes, and they went out as captured.
    """
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 3,
        Clock(
            "2026-10-09T12:00:00+00:00",
            "when the kettle boiled",
            "2026-10-09T12:00:06+00:00",
        ),
    )
    sleeps = Sleeps()
    lines: list[str] = []
    outcomes = replay.replay(
        source,
        source=replay.RAW,
        send=Spy(200),
        timing=True,
        sleep=sleeps,
        log=lines.append,
    )
    assert sleeps.slept == []
    assert all(outcome.status == 200 for outcome in outcomes)
    said = [line for line in lines if "no gap was slept" in line]
    assert len(said) == 2, said
    assert "raw/0002.body" in said[0] and "raw/0003.body" in said[1]


def test_a_receipt_time_that_went_backwards_is_not_slept(tmp_path):
    # `SPEC.md` §6.3: a negative gap is not one this invents a shape for.
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 2,
        Clock("2026-10-09T12:00:09+00:00", "2026-10-09T12:00:04+00:00"),
    )
    sleeps = Sleeps()
    lines: list[str] = []
    replay.replay(
        source,
        source=replay.RAW,
        send=Spy(200),
        timing=True,
        sleep=sleeps,
        log=lines.append,
    )
    assert sleeps.slept == []
    assert any("is before" in line for line in lines)


# --- a send that does not succeed, and the ones after it ---------------------


def test_a_non_2xx_does_not_stop_the_rest_and_exits_non_zero(tmp_path, capsys):
    """The degenerate case `SPEC.md` §6.4 is built around.

    A receiver that refuses the first export of a capture is a fact about that
    receiver -- a `415` on protobuf is the audit's first expected finding
    (`SPEC.md` §7) -- and a replay that stopped there would hide what it would
    have done with the second and the third.
    """
    source = crafted(
        tmp_path / "source",
        [
            (lambda port: head_octets(port, b"one"), b"one"),
            (lambda port: head_octets(port, b"two"), b"two"),
            (lambda port: head_octets(port, b"three"), b"three"),
        ],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    with scripted(415, 200, 200) as (server, port):
        status = cli.main(["replay", str(source), "--to", f"http://127.0.0.1:{port}"])
        received = list(server.bodies)
    assert received == [b"one", b"two", b"three"], (
        "a refused send stopped the rest of the capture"
    )
    assert status == 1
    printed = capsys.readouterr().out
    assert "raw/0001.body  415" in printed
    assert "1 that did not answer 2xx" in printed


def test_a_head_the_wire_refuses_is_not_tidied_into_one_it_accepts(tmp_path, capsys):
    """The capture's octets, or nothing: `SPEC.md` §6.2.

    The first request's `User-Agent` carries a **bare CR**. HTTP forbids it,
    real clients emit it, `email`'s parser truncates the value at it (so
    `NNNN.headers.json` says `otel`) and `http.client` refuses to put the real
    value on a socket. A replayer reading the parse would cheerfully send
    `User-Agent: otel` and exit 0, having sent a request no exporter made with
    the capture that says otherwise on disk beside it. So the send is refused,
    named, and the second body still goes out.
    """
    source = crafted(
        tmp_path / "source",
        [
            (
                lambda port: head_octets(
                    port, b"one", extra=b"User-Agent: otel\rpython/1.0\r\n"
                ),
                b"one",
            ),
            (lambda port: head_octets(port, b"two"), b"two"),
        ],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    # The capture really does hold the two, and they really do differ.
    assert b"otel\rpython/1.0" in sent_head(source)
    parsed = json.loads((source / "raw" / "0001.headers.json").read_text())
    assert ["User-Agent", "otel"] in parsed["headers"]

    with scripted(200) as (server, port):
        status = cli.main(["replay", str(source), "--to", f"http://127.0.0.1:{port}"])
        received = list(server.bodies)
    assert received == [b"two"], "a head the wire refuses was tidied and sent"
    assert status == 1
    printed = capsys.readouterr().out
    assert "raw/0001.body  not sent" in printed
    assert "ValueError" in printed


def test_a_body_the_manifest_lists_that_is_not_on_disk_is_named(tmp_path):
    # `SPEC.md` §6.4: per body, never per capture -- and never silent.
    with pytest.raises(replay.HeadUnreadable) as refused:
        replay.request(tmp_path, "raw/0001.body")
    assert "raw/0001.body" in str(refused.value)


def test_a_head_file_that_is_missing_is_named(tmp_path):
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "0001.body").write_bytes(b"x")
    with pytest.raises(replay.HeadUnreadable) as refused:
        replay.request(tmp_path, "raw/0001.body")
    assert "0001.headers.raw" in str(refused.value)


# --- nothing was sent: exit 2 ------------------------------------------------


def test_a_path_that_is_not_a_capture_sends_nothing_and_exits_2(tmp_path, capsys):
    status = cli.main(["replay", str(tmp_path), "--to", "http://127.0.0.1:1"])
    assert status == 2
    assert "Nothing was sent" in capsys.readouterr().err


def test_a_capture_with_no_body_on_the_chosen_side_exits_2(tmp_path, capsys):
    # `SPEC.md` §6.1: `--json` on a capture whose Collector never ran (§2.4).
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    status = cli.main(["replay", str(source), "--json", "--to", "http://127.0.0.1:1"])
    assert status == 2
    assert "holds no body under json/" in capsys.readouterr().err


@pytest.mark.parametrize(
    "to",
    [
        "https://127.0.0.1:4318",
        "127.0.0.1:4318",
        "http://127.0.0.1:4318/v1/traces",
        "http://",
    ],
)
def test_a_to_that_is_not_an_http_host_port_exits_2(to, capsys):
    status = cli.main(["replay", str(FIXTURE), "--to", to])
    assert status == 2
    assert "refusing to send" in capsys.readouterr().err


def test_the_default_side_is_raw():
    # The exporter's own bytes are the record; the re-encoding is a
    # convenience (`SPEC.md` §2.4), so the default sends the record.
    args = cli._parser().parse_args(["replay", "x", "--to", "http://h:1"])
    assert args.source == replay.RAW
    assert (
        cli._parser().parse_args(["replay", "x", "--to", "http://h:1", "--json"]).source
        == replay.JSON
    )


def test_the_committed_capture_is_untouched_by_being_replayed(tmp_path):
    # A capture is immutable (`CLAUDE.md` §0.6 rule 2) and the replayer writes
    # nothing: `make verify` would catch this later, and this catches it here.
    before = {
        path: path.read_bytes() for path in sorted(FIXTURE.rglob("*")) if path.is_file()
    }
    with destination(tmp_path / "again" / "raw") as (_, port):
        replay.replay(
            FIXTURE,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    after = {
        path: path.read_bytes() for path in sorted(FIXTURE.rglob("*")) if path.is_file()
    }
    assert after == before


def test_a_replay_answers_with_what_the_receiver_said_and_nothing_more(tmp_path):
    # `SPEC.md` §6.5: the status, and not the response body or anything about
    # what the receiver made of the bytes.
    with scripted(HTTPStatus.ACCEPTED) as (_, port):
        outcomes = replay.replay(
            FIXTURE,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert [outcome.status for outcome in outcomes] == [202]
    assert all(outcome.delivered for outcome in outcomes)
    assert all(outcome.error is None for outcome in outcomes)
