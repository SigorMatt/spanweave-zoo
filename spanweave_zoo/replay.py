"""The replayer: a capture's bytes and head, sent again (`SPEC.md` §6).

`zoo replay` hands a recorded capture to a receiver that was not there when it
was recorded -- the audit (`SPEC.md` §7) is its first caller -- and it **adds
nothing** (`CLAUDE.md` §0.6 rule 5). Three things here are the whole of that
claim, and each is a thing not done:

- the body is the bytes on disk, unread except to send them. Still gzipped if
  it was recorded gzipped, still protobuf if it was recorded as protobuf;
- the head is `NNNN.headers.raw`, the octets as they arrived (`SPEC.md`
  §2.3), put back on a socket as they are with **one** line substituted: the
  `Host` line, because the destination has changed (the decision of
  2026-10-11, "replay"). Never `NNNN.headers.json`, and never `http.client`:
  both hand over the pieces of a head and get back a head of their own --
  re-ordered, re-spaced, upgraded to HTTP/1.1, re-terminated in CRLF, minus
  its hop-by-hop headers. A replayer built on either would send a tidied
  request no exporter sent, with the capture that says otherwise on disk;
- the send itself is the `send` seam (`SPEC.md` §6.2), whose one real
  implementation is `forward.send_head`, next to the tee's forward.

What cannot be sent is **not tidied into what can**: a head that is empty, or
that does not end with the empty line that closes a header block, is one
printed line and a non-zero exit, with the rest of the capture still sent
(`SPEC.md` §6.4). A head HTTP forbids -- a bare CR in a value -- is not one of
them: it arrived on a socket, and it goes out on one.

Nothing here sleeps, reads a clock or parses a body: `--timing`'s sleep is an
injected seam (`SPEC.md` §6.3) and the receipt times it works from are values
the sink wrote down.
"""

from __future__ import annotations

from collections.abc import Callable
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

    head: bytes
    """`NNNN.headers.raw`'s octets, as recorded: `Host` not yet substituted."""

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


# The empty line that ends a header block, after the line ending before it:
# CRLF, or the bare LF some clients send and the sink's reader accepts.
_TERMINATORS = (b"\n\r\n", b"\n\n")


def terminated(octets: bytes) -> bool:
    """Whether the octets end with the empty line that closes a header block.

    `SPEC.md` §6.2. A head without it is not one a receiver could tell apart
    from the body sent after it: the body's bytes would arrive as header
    lines, a request no exporter made. The sink never records such a head (it
    records one only when it read a block to its end); a capture holding one
    has been made some other way, and the replay says so instead of sending.
    """
    return octets.endswith(_TERMINATORS)


def retarget(octets: bytes, host: str) -> bytes:
    """The head with its `Host` line naming `host`, and nothing else changed.

    `SPEC.md` §6.2. The lines are §2.3's -- the octets split on CRLF and on
    nothing else -- and a `Host` line is a line after the request line, before
    the empty line, whose field name (`sink.field_name`) is `Host` in any
    case. It becomes the name as sent, a colon, one space and `host`; its
    CRLF stays. Every such line is substituted, so a head that carried two
    names the destination in both; a head that carried none gets none, because
    adding a header is adding something. A `Host:` after a bare LF is inside
    another line, as it is in `NNNN.headers.json`, and is not touched. The
    rule is `forward.rewrite_head`'s, which the tee's forward uses too, with
    nothing dropped here.
    """
    return forward.rewrite_head(octets, host)


def _head_file(run: Path, body_file: str) -> Path:
    """`raw/0001.body` -> `raw/0001.headers.raw`: the octets beside the body."""
    body = Path(body_file)
    return run / body.with_name(body.stem + manifest.HEADERS_RAW_SUFFIX)


def request(run: Path, body_file: str) -> Request:
    """One recorded request, read off disk. Raises `HeadUnreadable`.

    The body is read whole and not looked at; the head is the octets, read
    whole and checked only for being a head (`terminated`), and the receipt
    time comes from the parse beside them, which is the one thing in that file
    the request did not say (`SPEC.md` §6.3).
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
    if not octets:
        raise HeadUnreadable(
            f"{_head_file(run, body_file).name} is empty, so nothing here says "
            f"what request {body_file} arrived in"
        )
    if not terminated(octets):
        raise HeadUnreadable(
            f"{_head_file(run, body_file).name} does not end with the empty "
            f"line that closes a header block, and the body sent after it "
            f"would arrive as more of the head"
        )
    return Request(
        file=body_file,
        head=octets,
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


# (the captured head octets, the body) -> the answer's status. Raises on a
# send that did not happen. `SPEC.md` §6.2.
Send = Callable[[bytes, bytes], int]
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
            # B5 (c), `SPEC.md` §6.3: the body was still received when the
            # sink says it was, so the next gap is measured from this receipt
            # -- or from none, when this one is not on record either.
            previous = manifest.received_at(run, file)
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
            status = send(recorded.head, recorded.body)
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
    """The real `send`, pointed at `--to` (`SPEC.md` §6.2).

    The captured head with its `Host` line naming `host:port` (`retarget`),
    an IPv6 literal bracketed (`forward.authority`, B5),
    then the body, on one connection of `forward.send_head`'s. That is the
    only difference between the request the exporter made and this one.
    """
    destination_host = forward.authority(host, port)

    def send(head: bytes, body: bytes) -> int:
        return forward.send_head(
            host, port, retarget(head, destination_host), body, timeout=timeout
        )

    return send
