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
"""

from __future__ import annotations

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

BODY_SUFFIX = ".body"
HEADERS_SUFFIX = ".headers.json"


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
        before_record: Callable[[bytes], None] | None = None,
        after_record: Callable[[manifest.BodyEntry], None] | None = None,
    ) -> None:
        self.raw = raw
        self.run = raw.parent
        self.rejected = self.run / REJECTED_DIR
        self._now = now
        self._before_record = before_record
        self._after_record = after_record
        self._lock = threading.Lock()
        self._counters: dict[Path, int] = {self.raw: 0, self.rejected: 0}

        for directory in (self.raw, self.rejected):
            existing = sorted(directory.glob("*" + BODY_SUFFIX))
            if existing:
                raise CaptureExists(
                    f"{directory} already holds {len(existing)} body file(s), "
                    f"starting {existing[0].name}. A run directory is never "
                    f"reused and a capture is never edited (SPEC.md section "
                    f"2.1): use a new run id."
                )
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
        body: bytes,
        accepted: bool,
    ) -> manifest.BodyEntry:
        """Write one request to disk and return its manifest entry."""
        if self._before_record is not None:
            self._before_record(body)

        directory = self.raw if accepted else self.rejected
        with self._lock:
            number = self._counters[directory] + 1
            self._counters[directory] = number
            stem = f"{number:04d}"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / (stem + BODY_SUFFIX)).write_bytes(body)
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
            body_file = directory / (stem + BODY_SUFFIX)
            entry = manifest.BodyEntry(
                file=body_file.relative_to(self.run).as_posix(),
                sha256=manifest.digest(body),
                bytes=len(body),
            )
            manifest.append_body(self.run, entry)

        if self._after_record is not None:
            self._after_record(entry)
        return entry


class _Handler(BaseHTTPRequestHandler):
    """One POST: read the declared bytes, record them, answer.

    `HTTP/1.1` with an explicit `Content-Length: 0` on every answer, so a real
    exporter's keep-alive connection is honoured and no answer is framed by
    closing the socket.
    """

    protocol_version = "HTTP/1.1"
    server_version = "zoo-sink"
    sys_version = ""

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
