"""The replayer: a capture's bytes and head, sent again (`SPEC.md` §6).

`zoo replay` hands a recorded capture to a receiver that was not there when it
was recorded -- the audit (`SPEC.md` §7) is its first caller -- and it **adds
nothing** (`CLAUDE.md` §0.6 rule 5). Three things here are the whole of that
claim, and each is a thing not done:

- the body is the bytes on disk, unread except to send them. Still gzipped if
  it was recorded gzipped, still protobuf if it was recorded as protobuf;
- the method, the target and every header come from `NNNN.headers.raw`, the
  octets of the head as they arrived (`SPEC.md` §2.3) -- **never** from
  `NNNN.headers.json`, which is what Python could represent of them. A
  replayer built on the parse would send a tidied request no exporter sent,
  with the capture that says otherwise sitting on disk beside it;
- the send itself is `forward.HttpForward`, the tee's own forward (`SPEC.md`
  §4.3) pointed somewhere else. Re-sending captured bytes is one act, and a
  second implementation of it would be a second chance to improve them.

What cannot be sent is **not tidied into what can**: a head with no request
line, or a value the wire refuses -- a bare CR, which RFC 9110 forbids and
`http.client` will not put on a socket -- is one printed line and a non-zero
exit, with the rest of the capture still sent (`SPEC.md` §6.4).

Nothing here sleeps, reads a clock or parses a body: `--timing`'s sleep is an
injected seam (`SPEC.md` §6.3) and the receipt times it works from are values
the sink wrote down.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from spanweave_zoo import capture, forward, manifest

# Which side of a capture to send (`SPEC.md` §6.1): the exporter's own bytes,
# or the Collector's re-encoding of them (`SPEC.md` §2.4).
RAW = capture.RAW_DIR
JSON = capture.JSON_DIR
SOURCES = (RAW, JSON)

# The one scheme. The replayer speaks the protocol the capture was recorded
# over and no other; a receiver behind TLS is a tunnel somebody else terminates.
SCHEME = "http"
DEFAULT_PORT = 80


class ReplayRefused(Exception):
    """Nothing was sent, and the command says so and exits 2.

    `SPEC.md` §6.1, on §5.6's rule: a path the operator typed that is not a
    capture, a manifest that cannot be read, a capture with no body in the
    chosen directory, a `--to` that is not an `http://host[:port]`. A replay
    that sent nothing must not read as a replay that worked (`CLAUDE.md`,
    "Honest refusal beats a reassuring pass").
    """


class HeadUnreadable(Exception):
    """One request's head octets are not a head this can re-send.

    Per body, never per capture: the rest of the capture is still sent and the
    exit status says afterwards (`SPEC.md` §6.4).
    """


@dataclass(frozen=True, slots=True)
class Request:
    """One recorded request, as it will go back out (`SPEC.md` §6.2)."""

    file: str
    """The body's path relative to the run directory: `raw/0001.body`."""

    method: str
    target: str
    headers: tuple[tuple[str, str], ...]
    """Every header as the octets had them, in order, repeats included."""

    body: bytes
    received_at: str | None
    """The sink's note of when it landed, or `None`. `--timing` reads it."""


@dataclass(frozen=True, slots=True)
class Outcome:
    """What happened to one body: an answer, or why there was none."""

    file: str
    status: int | None = None
    error: str | None = None
    slept: float | None = None
    """The gap `--timing` slept before this body, or `None` for no sleep."""

    @property
    def delivered(self) -> bool:
        """A 2xx and nothing else. `SPEC.md` §6.4's exit 1 is every other."""
        return self.status is not None and 200 <= self.status < 300


def destination(url: str) -> tuple[str, int]:
    """`--to` as a host and a port. `SPEC.md` §6: `http://host[:port]`.

    No path, because the request target comes from the capture and a replayer
    that joined one onto it would be sending a request the exporter never made.
    """
    split = urlsplit(url)
    if split.scheme != SCHEME:
        raise ReplayRefused(
            f"--to must be an {SCHEME}:// URL (SPEC.md section 6): {url!r}"
        )
    if split.path not in ("", "/") or split.query or split.fragment:
        raise ReplayRefused(
            f"--to carries a path, a query or a fragment, and the request "
            f"target comes from the capture (SPEC.md section 6.2): {url!r}"
        )
    try:
        host, port = split.hostname, split.port
    except ValueError as bad_port:
        raise ReplayRefused(
            f"--to has no readable port: {url!r} ({bad_port})"
        ) from None
    if not host:
        raise ReplayRefused(f"--to names no host: {url!r}")
    return host, port if port is not None else DEFAULT_PORT


def planned(run: Path, source: str) -> list[str]:
    """The bodies to send, in the order the capture recorded them.

    From the manifest's `bodies` list, which is the journal's order, which is
    receipt order (`SPEC.md` §2.2, §3.5). Read from the record rather than
    recovered by sorting the directory: `NNNN` is receipt order *because* a
    recorder assigned it in receipt order, and re-deriving that here would be
    deciding it again.
    """
    try:
        recorded = manifest.recorded_bodies(run)
    except (OSError, ValueError) as unreadable:
        raise ReplayRefused(
            f"{run} is not a capture this can replay: its "
            f"{manifest.MANIFEST_NAME} could not be read ({unreadable}). "
            f"Nothing was sent (SPEC.md section 6.1)."
        ) from None
    prefix = source + "/"
    files = [file for file in recorded if file.startswith(prefix)]
    if not files:
        raise ReplayRefused(
            f"{run} holds no body under {prefix} to send: its manifest lists "
            f"{len(recorded)} body/bodies and none of them is one. Nothing was "
            f"sent (SPEC.md section 6.1)."
        )
    return files


def _lines(octets: bytes) -> list[tuple[bytes, bytes]]:
    """The head's lines as `(content, line ending)`, split on LF alone.

    On LF and not on CR, which is the point: `bytes.splitlines` would split a
    **bare CR inside a header value** into two lines and so lose exactly the
    thing `NNNN.headers.raw` was kept for (`SPEC.md` §2.3). A line's own ending
    is carried with it so that a folded value can be rejoined as it arrived,
    and a last line with no LF at all -- a truncated head -- is a line with no
    ending rather than something dropped.
    """
    pieces = octets.split(b"\n")
    lines: list[tuple[bytes, bytes]] = []
    for piece in pieces[:-1]:
        if piece.endswith(b"\r"):
            lines.append((piece[:-1], b"\r\n"))
        else:
            lines.append((piece, b"\n"))
    if pieces[-1]:
        lines.append((pieces[-1], b""))
    return lines


def head(octets: bytes) -> tuple[str, str, list[tuple[str, str]]]:
    """The method, the target and the headers the octets carried.

    `SPEC.md` §6.2. Latin-1 throughout, which is what `http.client` puts a
    header on the wire as, so a value decoded here and re-encoded there is the
    same octets. A line beginning with a space or a tab continues the one
    before it (RFC 9110's deprecated `obs-fold`) and is joined to it with the
    ending kept: a value that arrived folded arrived folded.
    """
    lines = _lines(octets)
    if not lines:
        raise HeadUnreadable("the head is empty")
    request_line = lines[0][0].decode("latin-1")
    parts = request_line.split(" ")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise HeadUnreadable(f"the first line is not a request line: {request_line!r}")
    method, target = parts[0], parts[1]
    headers: list[tuple[str, str]] = []
    for content, ending in lines[1:]:
        if not content:
            break
        if content[:1] in (b" ", b"\t"):
            if not headers:
                raise HeadUnreadable(
                    "the header block begins with a continuation line: "
                    f"{content.decode('latin-1')!r}"
                )
            name, value = headers[-1]
            headers[-1] = (
                name,
                value + ending.decode("latin-1") + content.decode("latin-1"),
            )
            continue
        if b":" not in content:
            raise HeadUnreadable(
                f"a header line carries no colon: {content.decode('latin-1')!r}"
            )
        name_bytes, _, value_bytes = content.partition(b":")
        headers.append(
            (
                name_bytes.decode("latin-1"),
                value_bytes.decode("latin-1").strip(" \t"),
            )
        )
    return method, target, headers


def _head_file(run: Path, body_file: str) -> Path:
    """`raw/0001.body` -> `raw/0001.headers.raw`: the octets beside the body."""
    body = Path(body_file)
    return run / body.with_name(body.stem + manifest.HEADERS_RAW_SUFFIX)


def request(run: Path, body_file: str) -> Request:
    """One recorded request, read off disk. Raises `HeadUnreadable`.

    The body is read whole and not looked at; the head is read from the octets
    and the receipt time from the parse beside them, which is the one thing in
    that file the request did not say (`SPEC.md` §6.3).
    """
    body_path = run / body_file
    try:
        body = body_path.read_bytes()
    except OSError as missing:
        raise HeadUnreadable(
            f"the manifest lists {body_file} and it is not readable: {missing}"
        ) from None
    try:
        octets = _head_file(run, body_file).read_bytes()
    except OSError as missing:
        raise HeadUnreadable(
            f"{_head_file(run, body_file).name} is not readable ({missing}), so "
            f"nothing here says what request {body_file} arrived in"
        ) from None
    method, target, headers = head(octets)
    return Request(
        file=body_file,
        method=method,
        target=target,
        headers=tuple(headers),
        body=body,
        received_at=manifest.received_at(run, body_file),
    )


def gap(earlier: str | None, later: str | None) -> tuple[float | None, str | None]:
    """The seconds between two recorded receipt times, and why there are none.

    `SPEC.md` §6.3. Not slept and not guessed when either value is missing, is
    not an ISO-8601 moment with an offset (§5.3's bound, for §5.3's reason), or
    when the later one is the earlier: each is a line, and the send still
    happens.
    """
    before, after = manifest.moment_of(earlier), manifest.moment_of(later)
    if before is None or after is None:
        return None, (
            f"no gap was slept: a receipt time is missing or is not an "
            f"ISO-8601 moment with an offset ({earlier!r} -> {later!r})"
        )
    seconds = (after - before).total_seconds()
    if seconds < 0:
        return None, (
            f"no gap was slept: {later} is before {earlier}, and a negative "
            f"gap is not one this invents a shape for"
        )
    return seconds, None


Send = Callable[[str, str, Sequence[tuple[str, str]], bytes], int]
Log = Callable[[str], None]


def replay(
    run: Path,
    *,
    source: str,
    send: Send,
    timing: bool = False,
    sleep: Callable[[float], None] | None = None,
    log: Log,
) -> list[Outcome]:
    """Send every body of `run`'s chosen side, and say what happened to each.

    Returns one `Outcome` per planned body, in receipt order. **A send that
    does not succeed never stops the rest** (`SPEC.md` §6.4): a receiver that
    refuses the third export of a capture is a fact about that receiver, and a
    replay that stopped there would hide what it would have done with the
    fourth.
    """
    files = planned(run, source)
    outcomes: list[Outcome] = []
    previous: str | None = None
    for position, file in enumerate(files):
        try:
            recorded = request(run, file)
        except HeadUnreadable as unreadable:
            outcomes.append(Outcome(file=file, error=str(unreadable)))
            log(f"  {file}  not sent: {unreadable}")
            continue
        slept: float | None = None
        if timing and position:
            seconds, why = gap(previous, recorded.received_at)
            if why is not None:
                log(f"  ! {file}: {why}")
            elif seconds is not None and sleep is not None:
                sleep(seconds)
                slept = seconds
        previous = recorded.received_at
        try:
            status = send(
                recorded.method, recorded.target, recorded.headers, recorded.body
            )
        except Exception as failure:
            outcomes.append(
                Outcome(
                    file=file,
                    error=f"{type(failure).__name__}: {failure}",
                    slept=slept,
                )
            )
            log(f"  {file}  not sent: {type(failure).__name__}: {failure}")
            continue
        outcomes.append(Outcome(file=file, status=status, slept=slept))
        log(f"  {file}  {status}  {len(recorded.body)} bytes")
    return outcomes


def sender(host: str, port: int, *, timeout: float = forward.DEFAULT_TIMEOUT) -> Send:
    """The tee's forward, pointed at `--to` (`SPEC.md` §4.3, §6.2).

    The same object, so the two differences between the exporter's request and
    this one are the two that function already names: `Host` is the new
    destination, and the headers that described a connection that no longer
    exists are gone.
    """
    return forward.HttpForward(host, port, timeout=timeout)
