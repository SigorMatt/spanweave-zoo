"""The sink: it writes down what arrived and answers (`SPEC.md` §3).

Stdlib `http.server`, because the thing that must be believed byte for byte is
better with nothing between it and the socket -- no framework reading the body
for it, no middleware helpfully decompressing, nothing with an opinion about
content types. There are no runtime dependencies here and that is the point
(`CLAUDE.md`, "Architecture invariants").

What this module will not do, ever: decode, decompress, parse or validate a
body; look at a payload at all. It reads the `Content-Length` it was given,
copies that many bytes to disk, writes the request's headers beside them, and
answers `200` (or `404`, on a path that is not `/v1/traces`, having recorded
the bytes anyway). A `200` here means "recorded", never "understood" -- the
sink is not a receiver, and the one way to be a recorder worth trusting is to
have no taste.

Every point where this touches the world is a seam the caller passes in
(`SPEC.md` §3.6): `now` for the receipt time, the listener factory for the
socket, and `before_record` / `after_record` so a test can hold two POSTs in
flight at a chosen point rather than sleeping and hoping. Nothing in this
module reads a clock, sleeps, or draws a random number.

A3b changed where the digest lands and nothing else about recording: the entry
goes into the run's journal, `bodies.jsonl`, as one flushed line, and the
manifest is assembled from it when the run ends (`SPEC.md` §3.5, §5.5). What
that buys is a per-body cost that does not grow with the run: appending a line
is the same work for the sixteen-hundredth body as for the first, where
rewriting a manifest that has an entry per POST in it is not. The digest is
still written as the body is recorded, and there is still exactly one home
for it.

A3c made the octets of the head part of the record (`SPEC.md` §2.3): every
request leaves a `NNNN.headers.raw` -- the request line and the header block as
they arrived, CRLFs intact -- beside the `NNNN.headers.json` that is the
stdlib's parse of those same octets. The parse is a convenience and it loses
things: `email`'s header parser splits a header line on a bare CR and then
stops, so the value is truncated and every header after the split is absent
from it. A recorder whose record was the parse would hold what Python can
represent rather than what arrived, so the octets are kept as they go past
(`_Head`) and the parse is kept beside them.

A3f made `NNNN.headers.json` the zoo's own derivation of those octets rather
than the stdlib's parse of them (`SPEC.md` §2.3): the head split on CRLF and on
nothing else (`split_head`), so a bare CR or LF stays inside the value it
arrived in. The stdlib's parse had done worse than truncate: a value of
`otel\\rX-Injected: yes` came out of it as two headers, one of which no client
sent. The stdlib's parse is still what the sink *handled* the request with --
its `Content-Length`, the content type it echoes, the path that chose the
directory -- and it is no longer what the record says the request carried.

A3g took the parse out of the forward too (`SPEC.md` §4.3): the tee hands the
Collector the recorded octets, with only the `Host` line and the hop-by-hop
lines changed, so `otel\\rContent-Encoding: gzip` cannot reach it as a header
the record says the request never sent.

A2 added one more seam and no new taste (`SPEC.md` §4.3): `forward`, which the
recorder calls with the body **once the body is on disk**, so the Collector can
re-encode the same bytes to JSON beside the record. The order is the point --
the record is made first and the convenience second -- and a forward that fails
is written into the manifest rather than swallowed (§4.4). The forward is still
not a decode: it hands on the bytes and the head octets that were recorded.
"""

from __future__ import annotations

import io
import socketserver
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from spanweave_zoo import manifest

# The one path the sink accepts: the OTLP/HTTP traces endpoint, exactly
# (`EXPORT-CONTRACT.md` §2 told every project to export to `$ENDPOINT/v1/traces`).
TRACES_PATH = "/v1/traces"

# Where a POST to any other path is recorded, beside `raw/` (`SPEC.md` §3.4).
REJECTED_DIR = "rejected"

# The json sink's own, so that two recorders on one run directory cannot share
# a counter and overwrite each other (`SPEC.md` §4.5). A body in here means the
# zoo's own exporter endpoint is wrong, which is worth finding out.
REJECTED_JSON_DIR = "rejected-json"

BODY_SUFFIX = ".body"
# The json sink's bodies are `json/NNNN.json`, because `SPEC.md` §2.4 names
# that file: the same number, the other form of one export.
JSON_SUFFIX = ".json"
# One home for the name: `manifest.finish` reads these files to carry each
# body's content headers across (`SPEC.md` §5), so both ends name the same
# constant rather than the same string twice.
HEADERS_SUFFIX = manifest.HEADERS_SUFFIX
# The octets of the head, beside the parse of it (`SPEC.md` §2.3). The manifest
# covers this file by walking the run directory (`SPEC.md` §5.6) rather than by
# being told about it, which is the point -- a capture is covered whether or not
# a recorder announced a file. The name itself now has a reader as well as this
# writer, so it lives beside the parse's in `manifest.py`: A4's replayer sends
# the octets and never the parse (`SPEC.md` §6.2).
HEADERS_RAW_SUFFIX = manifest.HEADERS_RAW_SUFFIX
# Both of them, for the startup refusal: either file is a capture's, and a
# `*.json` glob over a json sink's directory also matches `*.headers.json`.
HEADERS_GLOB = "*.headers.*"

# The characters of an HTTP field name, a `token` (RFC 9110 §5.1, §5.6.2). A
# line of the head is a header only if what precedes its first colon is one.
_TCHAR = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)

# The optional whitespace around a field value (RFC 9110 §5.5), which is not
# part of the value. Space and horizontal tab, and nothing else: a CR or LF in
# a value is the client's, and stays.
_OWS = " \t"


def field_name(line: str) -> str | None:
    """The header name one line of §2.3's split carries, or `None`.

    What precedes the line's first colon, as sent, when that is a non-empty
    field-name token (RFC 9110 §5.6.2); otherwise the line is no header. One
    rule, used by the split below and by the replayer's `Host` substitution
    (`SPEC.md` §6.2), so the two cannot disagree about what a header line is.
    """
    name, colon, _ = line.partition(":")
    if colon and name and all(character in _TCHAR for character in name):
        return name
    return None


def split_head(head: bytes) -> dict[str, object]:
    """What `NNNN.headers.json` says a head carried (`SPEC.md` §2.3).

    The octets are decoded as Latin-1 -- one character per octet, so nothing
    is lost or replaced -- and split on CRLF and on nothing else. A bare CR or
    a bare LF is inside the line it arrived in, and so inside the value: the
    record cannot be made to assert a header the client did not send.

    - The first line is the request line, recorded whole as `request_line`,
      so nothing after the path is dropped: `method` is what precedes its
      first space, `path` what lies between that space and the next (or the
      line's end).
    - Every later line that is not empty is a header if what precedes its
      first colon is a field-name token; the `[name, value]` pair has the name
      as sent and the value with surrounding spaces and tabs removed, in the
      order received.
    - Any other non-empty line -- a continuation line, a line with no colon --
      is no header and part of none: it is listed verbatim under `unparsed`,
      which is absent when there are none.
    - The empty lines are the block's terminator and carry nothing.

    A head with **no CRLF at all** -- every line of it ended by a bare LF,
    which the stdlib's reader accepts -- is one line on this split and holds
    no request line the split can find. It is listed whole, verbatim, as the
    one `unparsed` entry, and `request_line`, `method` and `path` are absent:
    a json that read them out of it would be parsing on LF, and one that
    listed nothing would omit the whole block without saying so (the decision
    of 2026-10-11, "header rule").

    Pure: the same octets give the same document on any machine.
    """
    text = head.decode("latin-1")
    if "\r\n" not in text:
        unsplit: dict[str, object] = {"headers": []}
        if text:
            unsplit["unparsed"] = [text]
        return unsplit
    lines = text.split("\r\n")
    method, _, rest = lines[0].partition(" ")
    path = rest.split(" ", 1)[0]
    headers: list[list[str]] = []
    unparsed: list[str] = []
    for line in lines[1:]:
        if not line:
            continue
        name = field_name(line)
        if name is not None:
            headers.append([name, line[len(name) + 1 :].strip(_OWS)])
        else:
            unparsed.append(line)
    document: dict[str, object] = {
        "headers": headers,
        "method": method,
        "path": path,
        "request_line": lines[0],
    }
    if unparsed:
        document["unparsed"] = unparsed
    return document


# (the head's octets as recorded, the body) -> the forwarded request's status.
# Raises on a forward that did not happen. `SPEC.md` §4.8.
Forward = Callable[[bytes, bytes], int]


class CaptureExists(Exception):
    """`--out` already holds a body: refuse rather than write into a capture.

    A run directory is never reused (`SPEC.md` §2.1) and a capture is never
    edited (`CLAUDE.md`, "Halt points"). Renumbering into an existing capture,
    or overwriting one, is the failure this exception exists to make loud.
    """


# What `close()` says of a POST still being handled as the journals close
# (`SPEC.md` §4.2, §5.5): the body it names, or this when it had recorded none.
NOT_YET_RECORDED = "a POST not yet recorded"
STILL_HANDLED = (
    "still being handled when the journals closed; what its handler had not "
    "yet written is not in this capture"
)


class RecorderClosed(Exception):
    """A POST that reached a recorder after its journals were closed.

    The capture is sealed or about to be (`SPEC.md` §5.5): nothing more may be
    written into it, so the body is recorded nowhere, and the handler answers
    nothing rather than a status that would claim it was.
    """


class Recorder:
    """Writes one capture: bodies, headers, and the manifest's digests.

    Thread-safe, and deliberately serialized: a single lock covers assigning
    the sequence number *and* writing the files, so `NNNN` is receipt order and
    the manifest's entries are in that same order however many requests are in
    flight. Writing a body is microseconds of `write_bytes`; the contention is
    not worth a cleverer scheme that could reorder the record.
    """

    def __init__(
        self,
        raw: Path,
        *,
        now: Callable[[], str],
        rejected: Path | None = None,
        body_suffix: str = BODY_SUFFIX,
        forward: Forward | None = None,
        before_record: Callable[[bytes], None] | None = None,
        after_record: Callable[[manifest.BodyEntry], None] | None = None,
        after_forward: Callable[[manifest.ForwardEntry], None] | None = None,
        create_directory: bool = True,
    ) -> None:
        self.raw = raw
        self.run = raw.parent
        # `rejected` is a parameter because `zoo capture` runs two recorders on
        # one run directory (`SPEC.md` §4.5): the raw sink keeps `rejected/`,
        # the json sink is given `rejected-json/`, and the two counters cannot
        # collide. One recorder, as `zoo sink` runs it, keeps A1's default.
        self.rejected = rejected if rejected is not None else self.run / REJECTED_DIR
        self.body_suffix = body_suffix
        self._now = now
        self._forward = forward
        self._before_record = before_record
        self._after_record = after_record
        self._after_forward = after_forward
        self._lock = threading.Lock()
        self._counters: dict[Path, int] = {self.raw: 0, self.rejected: 0}
        self.forwards: list[manifest.ForwardEntry] = []
        # How many POSTs are being handled right now -- read, recorded,
        # forwarded, answered. `settle()` waits for it to reach zero, which is
        # how `zoo capture` lets every forward already under way be answered
        # before it stops the Collector (`SPEC.md` §4.6).
        self._busy = 0
        self._quiet = threading.Condition()
        # The POSTs under way, by handling thread, and the body each has
        # recorded so far (`None` until it has): what `close()` names when a
        # handler is still running as the journals close (`SPEC.md` §5.5). The
        # key is the thread's identity, used for nothing but finding its slot.
        self._open: dict[int, str | None] = {}
        # Set once by `close()`, under `_lock`: from then on nothing this
        # recorder holds is written into the run directory -- no body, no
        # journal line -- so the manifest sealed after it stays true.
        self._closed = False

        for directory, suffix in (
            (self.raw, body_suffix),
            (self.rejected, BODY_SUFFIX),
        ):
            # Either headers file is a capture's (`SPEC.md` §2.3, §3.1), and
            # neither is a body -- while the json sink's bodies are `*.json`
            # (`SPEC.md` §4.5), so `*` + suffix would also match
            # `NNNN.headers.json` and count it as one. Observed in the real
            # flow: a re-used run id refused with "2 body file(s), starting
            # 0001.headers.json", which is a true refusal told wrong, and a
            # refusal nobody can read is most of the way to no refusal.
            headers = sorted(directory.glob(HEADERS_GLOB))
            not_bodies = set(headers)
            bodies = sorted(
                path for path in directory.glob("*" + suffix) if path not in not_bodies
            )
            if bodies or headers:
                raise CaptureExists(
                    f"{directory} already holds {len(bodies)} body file(s) "
                    f"and {len(headers)} headers file(s) from an earlier "
                    f"capture, starting {(bodies or headers)[0].name}. A run "
                    f"directory is never reused and a capture is never edited "
                    f"(SPEC.md section 2.1): use a new run id."
                )
        # `zoo sink` creates `--out` when it starts (`SPEC.md` §3.1) and says
        # so in its banner. `zoo capture` passes `create_directory=False`,
        # because a capture directory exists only once the whole tee is ready
        # (`SPEC.md` §4.6) -- and a refusal before that must leave nothing on
        # disk. Either way `record` makes the directory it writes into, so the
        # two differ in when a directory appears and in nothing else.
        if create_directory:
            self.raw.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def handling(self) -> Iterator[None]:
        """Count one POST as under way for as long as the block runs."""
        handler = threading.get_ident()
        with self._quiet:
            self._busy += 1
            self._open[handler] = None
        try:
            yield
        finally:
            with self._quiet:
                self._busy -= 1
                self._open.pop(handler, None)
                self._quiet.notify_all()

    def settle(self, timeout: float) -> bool:
        """Wait, at most `timeout` seconds, for every POST under way to finish.

        Returns whether they did. Called once the listener has stopped
        accepting, so nothing new can start while it waits.
        """
        with self._quiet:
            return self._quiet.wait_for(lambda: self._busy == 0, timeout=timeout)

    def close(self) -> list[str]:
        """Close the journals: nothing is written into the run after this.

        What `zoo capture` calls once every bounded wait of its shutdown is
        over and before the manifest is sealed (`SPEC.md` §4.6, §5.5). A body
        that arrives afterwards, or a forward that completes afterwards, is
        refused and recorded nowhere -- so a handler the waits gave up on can
        no longer append to a journal the sealed manifest has already hashed.

        Returns one line per POST still being handled at the close, naming the
        body it had recorded, or saying it had recorded none: each is a
        `problems` entry, because what that handler had yet to write -- a
        forward's outcome, or the whole body -- is not in the capture.
        """
        with self._lock, self._quiet:
            self._closed = True
            still = sorted(
                self._open.values(), key=lambda file: (file is None, file or "")
            )
        return [
            f"{file if file is not None else NOT_YET_RECORDED}: {STILL_HANDLED}"
            for file in still
        ]

    def accepts(self, path: str) -> bool:
        """Whether `path` is the traces endpoint, compared exactly.

        The request target is compared verbatim -- a query string makes it a
        different path, and the sink does not parse one off to be helpful.
        """
        return path == TRACES_PATH

    def record(
        self,
        *,
        head: bytes,
        body: bytes,
        accepted: bool,
    ) -> manifest.BodyEntry:
        """Write one request to disk and return its manifest entry.

        `head` is the request line and the header block as the octets arrived
        (`SPEC.md` §2.3). The octets are written, `NNNN.headers.json` is
        derived from them by `split_head`, and a forward is handed them too
        (`SPEC.md` §4.3) -- never the stdlib's parse, which a bare CR can make
        assert a header nobody sent. `accepted` is the one thing the parse
        decided: the path chose the directory. The recorder is not handed the
        parse at all, so nothing it writes or sends can come from it.
        """
        if self._before_record is not None:
            self._before_record(body)

        directory = self.raw if accepted else self.rejected
        # A rejected body keeps `.body` whichever sink took it (`SPEC.md` §3.4):
        # it is not a re-encoding of anything, it is bytes aimed at the wrong
        # path, and naming it `.json` would be a claim about its contents.
        suffix = self.body_suffix if accepted else BODY_SUFFIX
        with self._lock:
            if self._closed:
                raise RecorderClosed(
                    f"{self.run}: the journals are closed; this POST is not recorded"
                )
            number = self._counters[directory] + 1
            self._counters[directory] = number
            stem = f"{number:04d}"
            directory.mkdir(parents=True, exist_ok=True)
            body_file = directory / (stem + suffix)
            body_file.write_bytes(body)
            # The unmodified record, then the zoo's split of it (`SPEC.md`
            # §2.3), and the two facts the octets of a head cannot carry.
            (directory / (stem + HEADERS_RAW_SUFFIX)).write_bytes(head)
            parsed = split_head(head)
            parsed["bytes"] = len(body)
            parsed["received_at"] = self._now()
            manifest.write_json(directory / (stem + HEADERS_SUFFIX), parsed)
            entry = manifest.BodyEntry(
                file=body_file.relative_to(self.run).as_posix(),
                sha256=manifest.digest(body),
                bytes=len(body),
            )
            manifest.journal_body(self.run, entry)
            with self._quiet:
                handler = threading.get_ident()
                if handler in self._open:
                    self._open[handler] = entry.file

        if self._after_record is not None:
            self._after_record(entry)
        if accepted:
            self._tee(head, body, entry)
        return entry

    def _tee(self, head: bytes, body: bytes, entry: manifest.BodyEntry) -> None:
        """Hand the recorded bytes to the Collector (`SPEC.md` §4.3).

        Called **after** the body, its headers and its digest are on disk, and
        outside the recorder's lock: a forward crosses a socket, and holding
        the lock across one would make the record of the next body wait on
        another process. A forward that raises is recorded as a failure
        (`SPEC.md` §4.4) -- never swallowed, and never allowed to change the
        bytes or the answer.

        A rejected POST (`SPEC.md` §3.4) is not forwarded at all: forwarding it
        would invent traffic the exporter never aimed at the Collector.
        """
        if self._forward is None:
            return
        try:
            status = self._forward(head, body)
        except Exception as failure:
            outcome = manifest.ForwardEntry(
                file=entry.file,
                error=f"{type(failure).__name__}: {failure}",
            )
        else:
            outcome = manifest.ForwardEntry(file=entry.file, status=status)
        with self._lock:
            # A forward that outlived every bounded wait of the shutdown
            # completes after the journals closed: its outcome is refused and
            # recorded nowhere, and `close()` already named its body as a
            # problem (`SPEC.md` §5.5). Checked and journalled under one lock,
            # so a close cannot fall between the two.
            if self._closed:
                return
            self.forwards.append(outcome)
            manifest.journal_forward(self.run, outcome)
        if self._after_forward is not None:
            self._after_forward(outcome)

    @property
    def failed_forwards(self) -> list[manifest.ForwardEntry]:
        """Every forward that did not deliver. `zoo capture` exits on these."""
        return [outcome for outcome in self.forwards if outcome.failed]


class _Head(io.BufferedIOBase):
    """The request stream, with the octets of one head kept as they are read.

    The only way to hold what a client actually sent is to keep the bytes on
    their way past: `http.server` reads the request line and then
    `http.client.parse_headers` reads the header block, both by `readline` off
    this stream, and what that parse hands back is already a lossy view of
    them: `email`'s header parser splits a header line on a bare CR and then
    stops, so a head reconstructed from `self.headers` is a record of what
    Python could represent and not of what arrived.

    Recording is per *request*, not per connection: a keep-alive connection
    carries several, and `begin` is called for each. It stops the moment the
    header block has been parsed, so the body -- read by `read`, not
    `readline` -- is never in the head. Nothing here interprets an octet; it
    delegates every call and appends to a buffer.
    """

    def __init__(self, stream: io.BufferedIOBase) -> None:
        super().__init__()
        self._stream = stream
        self._head = bytearray()
        self._recording = False

    def begin(self) -> None:
        """Start one head: the next readlines are this request's octets."""
        self._head = bytearray()
        self._recording = True

    def end(self) -> bytes:
        """The head as received, and stop recording. Idempotent."""
        self._recording = False
        return bytes(self._head)

    def readline(self, size: int | None = -1, /) -> bytes:
        """The one call the head arrives by, so the one call that records."""
        line = self._stream.readline(size)
        if self._recording:
            self._head += line
        return line

    def read(self, size: int | None = -1, /) -> bytes:
        """The body's call: never recorded, because a body is not a head."""
        return self._stream.read(size)

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        self._stream.close()


class _Handler(BaseHTTPRequestHandler):
    """One POST: read the declared bytes, record them, answer.

    `HTTP/1.1` with an explicit `Content-Length: 0` on every answer, so a real
    exporter's keep-alive connection is honoured and no answer is framed by
    closing the socket. The one exception is a request the sink could not
    frame (`SPEC.md` §3.3, B5): answered the same way, with `Connection:
    close`, and its connection closed after the answer.
    """

    protocol_version = "HTTP/1.1"
    server_version = "zoo-sink"
    sys_version = ""

    _stream: _Head
    _head: bytes = b""
    # Whether the request being answered gave no framing the sink can read
    # (`_read_body`); if so its connection is closed after the answer.
    _unframed: bool = False

    def setup(self) -> None:
        """Wrap the request stream before anything reads a byte off it."""
        super().setup()
        self._stream = _Head(self.rfile)
        self.rfile = self._stream

    def handle_one_request(self) -> None:
        """One request on this connection, so one head (`SPEC.md` §2.3)."""
        self._head = b""
        self._stream.begin()
        super().handle_one_request()

    def parse_request(self) -> bool:
        """The stdlib's parse, and the octets it was made from, kept both.

        `super()` has read the request line and the header block by the time
        it returns, and nothing after it is part of the head -- so this is
        where recording stops, whether the parse succeeded or not.
        """
        parsed = super().parse_request()
        self._head = self._stream.end()
        return parsed

    @property
    def _recorder(self) -> Recorder:
        recorder = getattr(self.server, "recorder", None)
        assert isinstance(recorder, Recorder)
        return recorder

    def do_POST(self) -> None:  # http.server's own naming, not ours
        recorder = self._recorder
        with recorder.handling():
            body = self._read_body()
            accepted = recorder.accepts(self.path)
            try:
                recorder.record(
                    head=self._head,
                    body=body,
                    accepted=accepted,
                )
            except RecorderClosed:
                # The capture is sealed (`SPEC.md` §5.5): no answer, and the
                # connection closed, because any status would say the body
                # was received into a capture that does not hold it.
                self.close_connection = True
                return
            self._answer(HTTPStatus.OK if accepted else HTTPStatus.NOT_FOUND)

    def _read_body(self) -> bytes:
        """Exactly the bytes `Content-Length` declared, and no guessing.

        A request with no `Content-Length` -- a chunked export, or a broken
        one -- is recorded as a zero-byte body (`SPEC.md` §3.7): reading a
        `Transfer-Encoding` means decoding a framing, and the sink decodes
        nothing. What it could see is what the capture says it saw.

        B5 (a): such a request is also **unframed** -- the sink does not know
        where its body ends, so it cannot know where the next request on the
        connection begins -- and `_answer` closes the connection after it
        rather than read whatever follows (a chunked body's chunks) as a
        request. Unframed is: no `Content-Length`, one that is not a number,
        or one that is not positive with a `Transfer-Encoding` beside it.
        """
        self._unframed = True
        declared = self.headers.get("Content-Length")
        if declared is None:
            return b""
        try:
            length = int(declared)
        except ValueError:
            # A `Content-Length` that is not a number is itself a recorded
            # fact: it stays in `headers.json`, and the body is what we could
            # read, which is nothing.
            return b""
        if length <= 0:
            self._unframed = self.headers.get("Transfer-Encoding") is not None
            return b""
        self._unframed = False
        return self.rfile.read(length)

    def _answer(self, status: HTTPStatus) -> None:
        """Empty body, the request's own content type echoed, nothing else.

        After a request the sink could not frame (`_read_body`), the answer
        also says `Connection: close` and the connection is closed once it is
        sent (`SPEC.md` §3.3): the sink decodes no framing, so it refuses to
        guess where the next request begins (decision of 2026-10-12, B5(a)).
        """
        self.send_response(status)
        content_type = self.headers.get("Content-Type")
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", "0")
        if self._unframed:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Silence. The sink's own record is `after_record`, not a log line."""

    def log_error(self, format: str, *args: object) -> None:
        """Silence, for the same reason: `http.server` logs to stderr."""


class _Server(ThreadingHTTPServer):
    """A `ThreadingHTTPServer` that carries the recorder for its handlers."""

    daemon_threads = True
    # A recorder is useless if the port cannot be re-bound after a run.
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], recorder: Recorder) -> None:
        self.recorder = recorder
        super().__init__(address, _Handler)

    def server_bind(self) -> None:
        """Bind, and resolve no name (`SPEC.md` §3.7).

        `http.server.HTTPServer.server_bind` follows the bind with
        `socket.getfqdn(host)` -- a reverse lookup of the address it was given,
        whose answer only a CGI or WSGI environment ever reads. On a macOS CI
        runner the first such lookup in a process took tens of seconds and,
        being a C call, held off the process's own signal handlers while it
        ran; a sink is a bind and nothing else, so the name is the address it
        was given.
        """
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


def make_server(recorder: Recorder, *, host: str, port: int) -> ThreadingHTTPServer:
    """The listener seam (`SPEC.md` §3.6): the only socket bind in the package.

    Binding is the caller's act, not an import's. A test passes `port=0` and
    reads the port the OS chose off `server.server_address`, so the suite never
    collides with something already on 4318 and never races a fixed port.
    """
    return _Server((host, port), recorder)
