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
import shutil
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
        self.calls: list[tuple[bytes, bytes]] = []

    def __call__(self, head, body):
        self.calls.append((head, body))
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

    The one line a replay is *expected* to differ in (`SPEC.md` §6.2): the
    destination has changed. Written independently of the replayer, on
    §2.3's notion of a line -- split on CRLF and nothing else -- with the name
    kept as sent. Everything else in the head must match octet for octet.
    """
    lines = head.split(b"\r\n")
    return b"\r\n".join(
        line.partition(b":")[0] + f": 127.0.0.1:{port}".encode("latin-1")
        if index and line.partition(b":")[0].lower() == b"host"
        else line
        for index, line in enumerate(lines)
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


# The four differences the run-2 review found (N-6) between a captured head
# and the head a replay put on the wire, plus the hop-by-hop drop, each in a
# head a client could really send. `SPEC.md` §6.2: only the `Host` line moves.
DIFFERENT_HEADS = {
    # `Host` not the first header: the replay moved it to the front.
    "host-not-first": lambda port, body: (
        b"POST /v1/traces HTTP/1.1\r\n"
        + b"User-Agent: otel/1.0\r\n"
        + f"Host: 127.0.0.1:{port}\r\n".encode("latin-1")
        + b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode("latin-1")
    ),
    # No space after the colon, and a tab: the replay wrote `name: value`.
    "value-whitespace": lambda port, body: (
        b"POST /v1/traces HTTP/1.1\r\n"
        + f"Host:127.0.0.1:{port}\r\n".encode("latin-1")
        + b"X-Tight:v\r\nX-Tab:\tv \r\n"
        + b"Content-Type:application/json\r\n"
        + f"Content-Length:{len(body)}\r\n\r\n".encode("latin-1")
    ),
    # An HTTP/1.0 request line: the replay sent HTTP/1.1.
    "http-1.0": lambda port, body: (
        b"POST /v1/traces HTTP/1.0\r\n"
        + f"Host: 127.0.0.1:{port}\r\n".encode("latin-1")
        + b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode("latin-1")
    ),
    # Every line ending a bare LF: the replay sent CRLF. (On §2.3's split
    # this head has no Host *line*, so nothing in it changes at all.)
    "lf-only": lambda port, body: (
        b"POST /v1/traces HTTP/1.1\n"
        + f"Host: 127.0.0.1:{port}\n".encode("latin-1")
        + b"Content-Type: application/json\n"
        + f"Content-Length: {len(body)}\n\n".encode("latin-1")
    ),
    # A hop-by-hop header: the replay dropped it.
    "hop-by-hop": lambda port, body: (
        b"POST /v1/traces HTTP/1.1\r\n"
        + f"Host: 127.0.0.1:{port}\r\n".encode("latin-1")
        + b"Connection: keep-alive\r\nKeep-Alive: timeout=5\r\n"
        + b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode("latin-1")
    ),
}


@pytest.mark.parametrize("shape", sorted(DIFFERENT_HEADS))
def test_a_replayed_head_differs_from_the_captured_one_in_the_host_line_only(
    tmp_path, shape
):
    """`SPEC.md` §6.2 and the decision of 2026-10-11 ("replay").

    Replayed into a fresh `zoo sink`, whose `.headers.raw` is what actually
    crossed the socket, the head is the captured octets with the `Host` line
    substituted and nothing else: not re-ordered, not re-spaced, not upgraded
    to HTTP/1.1, not re-terminated, not stripped of its hop-by-hop headers.
    A replay built on `http.client` fails every one of these, because
    `http.client` writes a head of its own from the pieces it is handed.
    """
    build = DIFFERENT_HEADS[shape]
    source = crafted(
        tmp_path / "source",
        [(lambda port: build(port, JSON_BODY), JSON_BODY)],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    again = tmp_path / "again"
    with destination(again / "raw") as (_, port):
        outcomes = replay.replay(
            source,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert [outcome.status for outcome in outcomes] == [200], outcomes
    assert sent_head(again) == with_host(sent_head(source), port)
    # B5d (`SPEC.md` §3.7): the sink frames by §2.3's split, on which the
    # LF-only head has no `Content-Length` -- so it is unframed, a zero-byte
    # body, when captured and again when replayed.
    body = b"" if shape == "lf-only" else JSON_BODY
    assert sent_body(source) == body
    assert sent_body(again) == body


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


def test_the_replayer_does_not_send_through_http_client(tmp_path, monkeypatch):
    # The decision of 2026-10-11 ("replay"), held structurally as well as by
    # the head-identity tests above: `http.client` writes a head of its own,
    # so the replay must not reach for one to write with.
    import http.client

    def refused(*args, **kwargs):
        raise AssertionError("the replay opened an http.client connection")

    monkeypatch.setattr(http.client.HTTPConnection, "__init__", refused)
    with destination(tmp_path / "again" / "raw") as (_, port):
        outcomes = replay.replay(
            FIXTURE,
            source=replay.RAW,
            send=replay.sender("127.0.0.1", port),
            log=lambda line: None,
        )
    assert [outcome.status for outcome in outcomes] == [200], outcomes


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
    assert [body for _, body in spy.calls] == [b"first", b"second", b"third"]
    assert [head for head, _ in spy.calls] == [
        sent_head(source, number) for number in (1, 2, 3)
    ]


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


def test_retarget_substitutes_the_host_line_and_nothing_else():
    # `SPEC.md` §6.2: the name as sent, one space, the destination; the line's
    # CRLF and every other octet as they were.
    head = b"POST /v1/traces HTTP/1.0\r\nX-A:a\r\nhOsT:\told:1 \r\nX-B: b\r\n\r\n"
    assert replay.retarget(head, "new:2") == (
        b"POST /v1/traces HTTP/1.0\r\nX-A:a\r\nhOsT: new:2\r\nX-B: b\r\n\r\n"
    )


def test_retarget_adds_no_host_to_a_head_that_carried_none():
    # Adding a header is adding something (`CLAUDE.md` §0.6 rule 5).
    head = b"POST /v1/traces HTTP/1.0\r\nContent-Length: 0\r\n\r\n"
    assert replay.retarget(head, "new:2") == head


def test_retarget_names_the_destination_in_every_host_line():
    head = b"POST / HTTP/1.1\r\nHost: a\r\nX: y\r\nHost: b\r\n\r\n"
    assert replay.retarget(head, "n:1") == (
        b"POST / HTTP/1.1\r\nHost: n:1\r\nX: y\r\nHost: n:1\r\n\r\n"
    )


@pytest.mark.parametrize(
    "head",
    [
        # After a bare LF, `Host:` is inside the X-A line on §2.3's split.
        b"POST / HTTP/1.1\r\nX-A: a\nHost: old\r\n\r\n",
        # An LF-only head is one line on §2.3's split: no Host line at all.
        b"POST / HTTP/1.1\nHost: old\n\n",
        # Not a header line: no colon after a token.
        b"POST / HTTP/1.1\r\nHost old\r\n\r\n",
        # The request line is never a header, whatever it says.
        b"Host: old\r\n\r\n",
    ],
)
def test_retarget_touches_no_host_that_is_not_a_header_line(head):
    assert replay.retarget(head, "new:2") == head


@pytest.mark.parametrize(
    "octets, said",
    [
        (b"", "is empty"),
        (b"POST /v1/traces HTTP/1.1\r\nHost: h\r\n", "does not end"),
        (b"POST /v1/traces HTTP/1.1\r\nHost: h", "does not end"),
    ],
)
def test_a_head_that_is_empty_or_unterminated_is_not_sent(tmp_path, octets, said):
    # `SPEC.md` §6.2: a body sent after a head that never ended would arrive
    # as more of the head -- a request no exporter made.
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "0001.body").write_bytes(b"x")
    (tmp_path / "raw" / "0001.headers.raw").write_bytes(octets)
    with pytest.raises(replay.HeadUnreadable) as refused:
        replay.request(tmp_path, "raw/0001.body")
    assert said in str(refused.value)
    assert "0001.headers.raw" in str(refused.value)


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


def test_the_summary_counts_only_the_bodies_that_were_sent(tmp_path, capsys):
    # A3g; run-2b review N-10 (run 2's N-7). With nothing listening, no body
    # is sent -- every connection is refused -- and the summary said "2 sent,
    # 2 that did not answer 2xx". A body that never reached a receiver was
    # not sent, and a reader of the last line must not be told it was.
    source = crafted(
        tmp_path / "source",
        [
            (lambda port: head_octets(port, b"one"), b"one"),
            (lambda port: head_octets(port, b"two"), b"two"),
        ],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed = probe.getsockname()[1]
    status = cli.main(["replay", str(source), "--to", f"http://127.0.0.1:{closed}"])
    assert status == 1
    summary = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("zoo replay: ") and "sent" in line
    ]
    assert summary == ["zoo replay: 0 sent, 0 that did not answer 2xx, 2 not sent"], (
        summary
    )


def test_the_summary_tells_a_refusal_from_a_body_never_sent(tmp_path, capsys):
    # One body answered 415, one whose head is missing and so never left.
    source = crafted(
        tmp_path / "source",
        [
            (lambda port: head_octets(port, b"one"), b"one"),
            (lambda port: head_octets(port, b"two"), b"two"),
        ],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    (source / "raw" / "0002.headers.raw").unlink()
    with scripted(415) as (_, port):
        status = cli.main(["replay", str(source), "--to", f"http://127.0.0.1:{port}"])
    assert status == 1
    out = capsys.readouterr().out
    assert "zoo replay: 1 sent, 1 that did not answer 2xx, 1 not sent" in out


def test_a_head_http_forbids_goes_out_as_it_arrived_and_is_not_tidied(tmp_path):
    """The capture's octets, bare CR and all: `SPEC.md` §6.2.

    The request's `User-Agent` carries a **bare CR**. HTTP forbids it, real
    clients emit it, and `http.client` refuses to put it on a socket -- so
    before A4a this send was refused. The replay now writes the octets itself,
    and they arrived on a socket, so they go out on one: the receiver's answer
    to them is a fact about the receiver. What must never happen is the
    tidied request, `User-Agent: otel`, which no exporter sent.
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
    # The capture really does hold the bare CR, in the octets and the split.
    assert b"otel\rpython/1.0" in sent_head(source)
    parsed = json.loads((source / "raw" / "0001.headers.json").read_text())
    assert ["User-Agent", "otel\rpython/1.0"] in parsed["headers"]

    again = tmp_path / "again"
    with destination(again / "raw") as (_, port):
        status = cli.main(["replay", str(source), "--to", f"http://127.0.0.1:{port}"])
    assert status == 0
    assert sent_head(again, 1) == with_host(sent_head(source, 1), port)
    assert sent_head(again, 2) == with_host(sent_head(source, 2), port)
    assert [sent_body(again, 1), sent_body(again, 2)] == [b"one", b"two"]


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


# --- B5 (b): an IPv6 destination is bracketed in `Host` ----------------------


@contextmanager
def ipv6_listener():
    """A one-request receiver on `[::1]` that keeps the head it was sent.

    Raw octets rather than `http.server`, whose servers bind IPv4. Skipped
    only where the machine has no IPv6 loopback to bind.
    """
    try:
        server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        server.bind(("::1", 0))
    except OSError as unavailable:
        pytest.skip(f"no IPv6 loopback here: {unavailable}")
    server.listen(1)
    server.settimeout(TIMEOUT)
    heads: list[bytes] = []

    def serve() -> None:
        connection, _ = server.accept()
        with connection:
            connection.settimeout(TIMEOUT)
            received = b""
            while b"\r\n\r\n" not in received:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                received += chunk
            heads.append(received.partition(b"\r\n\r\n")[0] + b"\r\n\r\n")
            connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield heads, server.getsockname()[1]
    finally:
        thread.join(timeout=TIMEOUT)
        server.close()


def test_a_replay_to_an_ipv6_literal_sends_a_bracketed_host(tmp_path):
    # B5 (b), Q11, `SPEC.md` §6.2: `--to http://[::1]:<port>` names the
    # destination as RFC 9110 §7.2 writes an IPv6 literal, `[::1]:<port>`.
    # Unbracketed, `::1:<port>` is no host a receiver can read.
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")],
        Clock("2026-10-09T12:00:00+00:00"),
    )
    with ipv6_listener() as (heads, port):
        status = cli.main(["replay", str(source), "--to", f"http://[::1]:{port}"])
    assert status == 0
    assert f"\r\nHost: [::1]:{port}\r\n".encode() in heads[0], heads


def test_the_destination_host_is_bracketed_only_for_an_ipv6_literal():
    # B5 (b): one rule for the replay and the tee (`forward.authority`).
    from spanweave_zoo import forward

    assert forward.authority("::1", 4318) == "[::1]:4318"
    assert forward.authority("fe80::1%eth0", 80) == "[fe80::1%eth0]:80"
    assert forward.authority("127.0.0.1", 4318) == "127.0.0.1:4318"
    assert forward.authority("collector", 4318) == "collector:4318"


def test_the_tee_names_an_ipv6_collector_bracketed(monkeypatch):
    # B5 (b), `SPEC.md` §4.3: `HttpForward`'s `Host` follows the same rule.
    from spanweave_zoo import forward

    sent: list[bytes] = []

    def spy(host, port, head, body, *, timeout):
        sent.append(head)
        return 200

    monkeypatch.setattr(forward, "send_head", spy)
    head = b"POST /v1/traces HTTP/1.1\r\nHost: 127.0.0.1:4318\r\n\r\n"
    assert forward.HttpForward("::1", 4319)(head, b"") == 200
    assert sent == [b"POST /v1/traces HTTP/1.1\r\nHost: [::1]:4319\r\n\r\n"]


# --- B5 (c): `--timing` measures from the body before, sent or not -----------


def _unreadable_head(run: Path, number: int) -> None:
    """Empty one recorded head, so that body is not sent (`SPEC.md` §6.2)."""
    (run / "raw" / f"{number:04d}.headers.raw").write_bytes(b"")


# Receipts four seconds then two seconds apart, as a test's clock says.
THREE_RECEIPTS = (
    "2026-10-09T12:00:00+00:00",
    "2026-10-09T12:00:04+00:00",
    "2026-10-09T12:00:06+00:00",
)


def test_a_skipped_first_body_still_starts_the_next_gap(tmp_path):
    # B5 (c), Q3, `SPEC.md` §6.3: the first body's head is unreadable and it
    # is not sent, but it was received at 12:00:00, so the second waits the
    # four seconds after it, as the exporter's did.
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 3,
        Clock(*THREE_RECEIPTS),
    )
    _unreadable_head(source, 1)
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
    assert [outcome.status for outcome in outcomes] == [None, 200, 200]
    assert sleeps.slept == [4.0, 2.0]
    assert [outcome.slept for outcome in outcomes] == [None, 4.0, 2.0]
    assert not any("no gap was slept" in line for line in lines), lines


def test_a_skipped_middle_body_still_ends_the_gap_before_it(tmp_path):
    # B5 (c): the second body is not sent; the third's gap is measured from
    # the second's receipt (two seconds), not from the first's (six).
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 3,
        Clock(*THREE_RECEIPTS),
    )
    _unreadable_head(source, 2)
    sleeps = Sleeps()
    outcomes = replay.replay(
        source,
        source=replay.RAW,
        send=Spy(200),
        timing=True,
        sleep=sleeps,
        log=lambda line: None,
    )
    assert [outcome.status for outcome in outcomes] == [200, None, 200]
    assert sleeps.slept == [2.0]
    assert [outcome.slept for outcome in outcomes] == [None, None, 2.0]


def test_a_skipped_body_with_no_receipt_time_leaves_no_gap_to_guess(tmp_path):
    # B5 (c), degenerate: the skipped body's `headers.json` is gone too, so
    # its receipt is unknown. The next gap is not measured from the body
    # before it -- that would be guessing -- and the replay says so.
    source = crafted(
        tmp_path / "source",
        [(lambda port: head_octets(port, b"x"), b"x")] * 3,
        Clock(*THREE_RECEIPTS),
    )
    _unreadable_head(source, 2)
    (source / "raw" / "0002.headers.json").unlink()
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
    said = [line for line in lines if "no gap was slept" in line]
    assert len(said) == 1 and "raw/0003.body" in said[0], lines


# --- B4a: a manifest path outside the run is a refusal, nothing sent --------


def _outside_files(beside: Path) -> None:
    """Bodies and a head outside the run, so a replayer that followed the
    manifest there would find something to send -- and a test that it did not
    is a test of the refusal, not of a missing file."""
    beside.mkdir(parents=True, exist_ok=True)
    # Copies of the capture's own bytes, so each head's `Content-Length` is
    # true and a replayer that followed the entry would send it and be
    # answered: the parent of B4a did, for a `..` entry under `raw/`.
    for side, name, stem in (
        ("raw", "0001.body", "outside"),
        ("json", "0001.json", "elsewhere"),
    ):
        suffix = Path(name).suffix
        shutil.copyfile(FIXTURE / side / name, beside / f"{stem}{suffix}")
        shutil.copyfile(
            FIXTURE / side / "0001.headers.raw", beside / f"{stem}.headers.raw"
        )


def _misplaced_copy(tmp_path: Path, case: str) -> tuple[Path, str]:
    """A copy of the committed capture with one `file` entry pointing out of
    it (`SPEC.md` §5.4), and the entry as the refusal must name it.

    A copy, never the capture: a capture is immutable (`CLAUDE.md` §0.6
    rule 2). The seal is not recomputed -- the replayer does not check it
    (`SPEC.md` §6.5), so a test that resealed would prove nothing more.
    """
    run = tmp_path / "capture" / "run"
    shutil.copytree(FIXTURE, run)
    beside = run.parent
    _outside_files(beside)
    document = json.loads((run / manifest.MANIFEST_NAME).read_text("utf-8"))
    files = {entry["file"]: entry for entry in document["files"]}
    if case == "raw-absolute":
        entry = str(beside / "outside.body")
        document["bodies"][0]["file"] = entry
    elif case == "raw-dotdot":
        entry = "raw/../../outside.body"
        document["bodies"][0]["file"] = entry
    elif case == "json-absolute":
        entry = str(beside / "elsewhere.json")
        document["bodies"][1]["file"] = entry
    elif case == "json-dotdot":
        entry = "json/../../elsewhere.json"
        document["bodies"][1]["file"] = entry
    elif case == "files-dotdot":
        entry = "raw/../../outside.headers.raw"
        files["raw/0001.headers.raw"]["file"] = entry
    elif case == "raw-symlink":
        entry = "raw/0001.body"
        (run / entry).unlink()
        (run / entry).symlink_to(beside / "outside.body")
    elif case == "raw-loop":
        entry = "raw/0001.body"
        (run / entry).unlink()
        (run / entry).symlink_to(run / entry)
    else:  # pragma: no cover - a typo in the parametrization
        raise AssertionError(case)
    (run / manifest.MANIFEST_NAME).write_text(
        json.dumps(document, sort_keys=True), encoding="utf-8"
    )
    return run, entry


@pytest.mark.parametrize("side", ["--raw", "--json"])
@pytest.mark.parametrize(
    "case",
    [
        "raw-absolute",
        "raw-dotdot",
        "json-absolute",
        "json-dotdot",
        "files-dotdot",
        "raw-symlink",
    ],
)
def test_a_manifest_path_outside_the_run_is_refused_and_nothing_sent(
    tmp_path, capsys, case, side
):
    # B4a, `SPEC.md` §6.1: replay trusts a manifest's paths only as far as
    # `verify` would (§5.4). An entry on the side being sent and one on the
    # side that is not are the same refusal: the manifest is one document,
    # and one claim pointing out of the run makes all of it untrusted.
    run, entry = _misplaced_copy(tmp_path, case)
    with scripted(200) as (server, port):
        status = cli.main(
            ["replay", str(run), side, "--to", f"http://127.0.0.1:{port}"]
        )
    err = capsys.readouterr().err
    assert status == 2, err
    assert repr(entry) in err, err
    assert "Nothing was sent" in err
    assert server.bodies == []


@pytest.mark.parametrize("side", ["--raw", "--json"])
def test_a_manifest_entry_that_cannot_be_resolved_is_refused_and_nothing_sent(
    tmp_path, capsys, side
):
    # Qodo 3 on PR #2 (decisions-zoo-2026-10-14b, commit 3): a `bodies` entry
    # naming a symlink to itself cannot be resolved -- `RuntimeError` on 3.11
    # and 3.12, `OSError` from a strict resolve on 3.13+. It is a refusal
    # naming the entry, exit 2, on both sides (`SPEC.md` §5.4, §6.1), never a
    # traceback.
    run, entry = _misplaced_copy(tmp_path, "raw-loop")
    with scripted(200) as (server, port):
        status = cli.main(
            ["replay", str(run), side, "--to", f"http://127.0.0.1:{port}"]
        )
    err = capsys.readouterr().err
    assert status == 2, err
    assert repr(entry) in err, err
    assert "cannot be resolved" in err, err
    assert "Nothing was sent" in err
    assert server.bodies == []


def test_planned_refuses_before_anything_is_read(tmp_path, monkeypatch):
    # The check precedes every read of a body or a head: `replay.replay` and
    # the audit's `serve` both go through `planned` (`SPEC.md` §6.1, §7.3).
    run, entry = _misplaced_copy(tmp_path, "raw-dotdot")
    read: list[Path] = []
    original = Path.read_bytes

    def watched(self: Path) -> bytes:
        read.append(self)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", watched)
    with pytest.raises(replay.ReplayRefused) as refused:
        replay.replay(run, source=replay.RAW, send=Spy(200), log=lambda line: None)
    assert repr(entry) in str(refused.value)
    assert [path for path in read if path.name != manifest.MANIFEST_NAME] == []


def test_the_committed_capture_has_no_entry_outside_itself():
    # The clean case: the check refuses nothing a real capture holds.
    assert manifest.misplaced(FIXTURE) == []
