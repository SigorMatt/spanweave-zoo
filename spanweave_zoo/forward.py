"""The package's outbound sockets: the tee's forward, and the replay's send.

The raw sink writes a body and then hands those same bytes to the Collector so
that it can re-encode them to JSON *beside* the record (`SPEC.md` §4.3). This
module holds the `forward` seam's one real implementation and the `send`
seam's (`SPEC.md` §6.2) -- the only outbound sockets in the package.
`sink.make_server` binds one, this connects them, and `SPEC.md` names all
three.

It is byte-identical on purpose, and that is a stronger claim than it looks:

- the body goes out as it came in. Still gzipped if it arrived gzipped, still
  protobuf if it arrived as protobuf. Nothing here decompresses, decodes,
  re-encodes or re-frames, exactly as nothing in the sink does;
- the head goes out as it was **recorded** -- the octets of `NNNN.headers.raw`
  (`SPEC.md` §2.3), request line, order, repeats, spacing and line endings
  as they arrived -- and is written onto the socket here rather than handed to
  `http.client` in pieces. Before A3g the forward sent the stdlib's parse of
  the head through `http.client`, and a bare CR in a value made that parse
  assert a header no client sent: `otel\\rContent-Encoding: gzip` reached the
  Collector as a `Content-Encoding` the record says the request never
  carried (run-2b review, N-7).

The two exceptions name the connection rather than the payload, and each is a
whole line of §2.3's split (`collector_head`): the `Host` line, substituted,
because the destination has changed, and the hop-by-hop header lines of RFC
9110 §7.6.1, dropped, because they describe a connection this is not.
`Content-Type`, `Content-Encoding`, `Content-Length` and `User-Agent` go
through untouched -- they are what the Collector needs in order to read what
the exporter sent.

Nothing here parses a body, and nothing here looks at the Collector's answer
beyond its status: a forward's outcome belongs in the manifest (`SPEC.md`
§4.5), and the Collector's own response body is not part of the capture.
"""

from __future__ import annotations

import http.client
import socket

from spanweave_zoo import sink

# RFC 9110 §7.6.1. A hop-by-hop header describes the connection it arrived on,
# and the forward is a different connection: passing them on would be passing
# on a claim about something that no longer exists.
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

DEFAULT_TIMEOUT = 5.0


def rewrite_head(
    octets: bytes, host: str, *, drop: frozenset[str] = frozenset()
) -> bytes:
    """The head with its `Host` lines naming `host`, and the `drop` lines gone.

    The lines are `SPEC.md` §2.3's -- the octets split on CRLF and on nothing
    else -- and a header line is a line after the request line, before the
    empty line, whose field name (`sink.field_name`) is a token. A `Host`
    line, in any case, becomes the name as sent, a colon, one space and
    `host`; its CRLF stays. A header line whose name, in any case, is in
    `drop` is removed with its CRLF. Every other octet is as it was: a head
    that carried no `Host` gets none, a `Host:` after a bare LF is inside
    another line and is not touched, and a head with no CRLF at all is one
    line and comes back unchanged. One rule for the replay (`SPEC.md` §6.2,
    nothing dropped) and the tee's forward (§4.3, the hop-by-hop lines
    dropped), so the two cannot disagree about what a line is.
    """
    lines = octets.split(b"\r\n")
    kept = lines[:1]
    for index in range(1, len(lines)):
        line = lines[index]
        if not line:
            kept.extend(lines[index:])
            break
        name = sink.field_name(line.decode("latin-1"))
        if name is not None:
            folded = name.lower()
            if folded in drop:
                continue
            if folded == "host":
                line = name.encode("latin-1") + b": " + host.encode("latin-1")
        kept.append(line)
    return b"\r\n".join(kept)


def collector_head(octets: bytes, host: str) -> bytes:
    """What the tee sends the Collector for a recorded head (`SPEC.md` §4.3).

    The recorded octets with the `Host` line naming the Collector and the
    hop-by-hop header lines dropped; nothing else changed.
    """
    return rewrite_head(octets, host, drop=HOP_BY_HOP)


class HttpForward:
    """POST the same bytes to the Collector, and return its status.

    Raises whatever the socket raises -- `ConnectionRefusedError` when the
    Collector is not there, `TimeoutError` when it does not answer. The caller
    (`sink.Recorder`) records the failure rather than swallowing it: the body is
    already on disk and a forward that failed is a fact about the capture
    (`SPEC.md` §4.4).
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __call__(self, head: bytes, body: bytes) -> int:
        """Send `head` as `collector_head` makes it, then `body`; the status."""
        return send_head(
            self.host,
            self.port,
            collector_head(head, f"{self.host}:{self.port}"),
            body,
            timeout=self.timeout,
        )


def send_head(
    host: str,
    port: int,
    head: bytes,
    body: bytes,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> int:
    """Put `head` and then `body` on one connection, and return the status.

    The replay's `send` (`SPEC.md` §6.2) and the tee's forward (§4.3): the
    octets go out as they are handed over, so nothing here re-forms a request
    line, re-orders, re-spaces or re-terminates a header, adds one or drops
    one -- which is what `http.client` does to every head it writes, and why
    neither writes through it. The caller has already rewritten the head
    (`rewrite_head`).

    The answer is read by the stdlib's response parser, which frames it (a
    `Content-Length`, chunks, or the connection's close) so the connection
    ends cleanly; nothing but its status is kept (`SPEC.md` §6.5). Raises
    whatever the socket raises; `HttpForward`'s caller records it.
    """
    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.sendall(head + body)
        response = http.client.HTTPResponse(connection)
        try:
            response.begin()
            response.read()
            return response.status
        finally:
            response.close()
