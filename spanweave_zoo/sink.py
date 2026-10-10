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

A2 added one more seam and no new taste (`SPEC.md` §4.3): `forward`, which the
recorder calls with the body **once the body is on disk**, so the Collector can
re-encode the same bytes to JSON beside the record. The order is the point --
the record is made first and the convenience second -- and a forward that fails
is written into the manifest rather than swallowed (§4.4). The forward is still
not a decode: it hands on the bytes and the headers it was given.
"""

from __future__ import annotations

import io
import threading
from collections.abc import Callable, Sequence
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
# The octets of the head, beside the parse of it (`SPEC.md` §2.3). This name
# lives here and not in `manifest.py` because nothing reads this file: the
# manifest covers it by walking the run directory (`SPEC.md` §5.6), which is
# the point -- a capture is covered whether or not a recorder announced a file.
HEADERS_RAW_SUFFIX = ".headers.raw"
# Both of them, for the startup refusal: either file is a capture's, and a
# `*.json` glob over a json sink's directory also matches `*.headers.json`.
HEADERS_GLOB = "*.headers.*"

# (method, path, headers as received, body) -> the forwarded request's status.
# Raises on a forward that did not happen. `SPEC.md` §4.8.
Forward = Callable[[str, str, Sequence[tuple[str, str]], bytes], int]


class CaptureExists(Exception):
    """`--out` already holds a body: refuse rather than write into a capture.

    A run directory is never reused (`SPEC.md` §2.1) and a capture is never
    edited (`CLAUDE.md`, "Halt points"). Renumbering into an existing capture,
    or overwriting one, is the failure this exception exists to make loud.
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

    def accepts(self, path: str) -> bool:
        """Whether `path` is the traces endpoint, compared exactly.

        The request target is compared verbatim -- a query string makes it a
        different path, and the sink does not parse one off to be helpful.
        """
        return path == TRACES_PATH

    def record(
        self,
        *,
        method: str,
        path: str,
        headers: Sequence[tuple[str, str]],
        head: bytes,
        body: bytes,
        accepted: bool,
    ) -> manifest.BodyEntry:
        """Write one request to disk and return its manifest entry.

        `head` is the request line and the header block as the octets arrived
        (`SPEC.md` §2.3) and `headers` is the stdlib's parse of those same
        octets. Both are written, the octets first: the record is not the
        parse, and a head the parse cannot represent -- a bare CR in a value --
        is still in the capture. `head` is a required argument because every
        recorded request has one, and a recorder that could be handed the parse
        without the octets is a recorder that can write a capture missing its
        own record.
        """
        if self._before_record is not None:
            self._before_record(body)

        directory = self.raw if accepted else self.rejected
        # A rejected body keeps `.body` whichever sink took it (`SPEC.md` §3.4):
        # it is not a re-encoding of anything, it is bytes aimed at the wrong
        # path, and naming it `.json` would be a claim about its contents.
        suffix = self.body_suffix if accepted else BODY_SUFFIX
        with self._lock:
            number = self._counters[directory] + 1
            self._counters[directory] = number
            stem = f"{number:04d}"
            directory.mkdir(parents=True, exist_ok=True)
            body_file = directory / (stem + suffix)
            body_file.write_bytes(body)
            # The unmodified record, then the parse of it (`SPEC.md` §2.3).
            (directory / (stem + HEADERS_RAW_SUFFIX)).write_bytes(head)
            manifest.write_json(
                directory / (stem + HEADERS_SUFFIX),
                {
                    "bytes": len(body),
                    "headers": [[name, value] for name, value in headers],
                    "method": method,
                    "path": path,
                    "received_at": self._now(),
                },
            )
            entry = manifest.BodyEntry(
                file=body_file.relative_to(self.run).as_posix(),
                sha256=manifest.digest(body),
                bytes=len(body),
            )
            manifest.journal_body(self.run, entry)

        if self._after_record is not None:
            self._after_record(entry)
        if accepted:
            self._tee(method, path, headers, body, entry)
        return entry

    def _tee(
        self,
        method: str,
        path: str,
        headers: Sequence[tuple[str, str]],
        body: bytes,
        entry: manifest.BodyEntry,
    ) -> None:
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
            status = self._forward(method, path, headers, body)
        except Exception as failure:
            outcome = manifest.ForwardEntry(
                file=entry.file,
                error=f"{type(failure).__name__}: {failure}",
            )
        else:
            outcome = manifest.ForwardEntry(file=entry.file, status=status)
        with self._lock:
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
    closing the socket.
    """

    protocol_version = "HTTP/1.1"
    server_version = "zoo-sink"
    sys_version = ""

    _stream: _Head
    _head: bytes = b""

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
        body = self._read_body()
        accepted = recorder.accepts(self.path)
        recorder.record(
            method=self.command,
            path=self.path,
            headers=list(self.headers.items()),
            head=self._head,
            body=body,
            accepted=accepted,
        )
        self._answer(HTTPStatus.OK if accepted else HTTPStatus.NOT_FOUND)

    def _read_body(self) -> bytes:
        """Exactly the bytes `Content-Length` declared, and no guessing.

        A request with no `Content-Length` -- a chunked export, or a broken
        one -- is recorded as a zero-byte body (`SPEC.md` §3.7): reading a
        `Transfer-Encoding` means decoding a framing, and the sink decodes
        nothing. What it could see is what the capture says it saw.
        """
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
            return b""
        return self.rfile.read(length)

    def _answer(self, status: HTTPStatus) -> None:
        """Empty body, the request's own content type echoed, nothing else."""
        self.send_response(status)
        content_type = self.headers.get("Content-Type")
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", "0")
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


def make_server(recorder: Recorder, *, host: str, port: int) -> ThreadingHTTPServer:
    """The listener seam (`SPEC.md` §3.6): the only socket bind in the package.

    Binding is the caller's act, not an import's. A test passes `port=0` and
    reads the port the OS chose off `server.server_address`, so the suite never
    collides with something already on 4318 and never races a fixed port.
    """
    return _Server((host, port), recorder)
