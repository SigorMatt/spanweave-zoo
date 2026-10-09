"""The tee's forward: the same bytes again, to the Collector (`SPEC.md` §4.3).

The raw sink writes a body and then hands those same bytes to the Collector so
that it can re-encode them to JSON *beside* the record. This module is the
`forward` seam's one real implementation and the only outbound socket in the
package -- `sink.make_server` binds one, this connects one, and `SPEC.md` names
both.

It is byte-identical on purpose, and that is a stronger claim than it looks:

- the body goes out as it came in. Still gzipped if it arrived gzipped, still
  protobuf if it arrived as protobuf. Nothing here decompresses, decodes,
  re-encodes or re-frames, exactly as nothing in the sink does;
- every header goes out as it came in, **in order, repeats included**, which is
  why this uses `putrequest` / `putheader` rather than `request(headers=dict)`:
  a dict would silently keep one of two repeated headers, and the headers are
  part of the record (`SPEC.md` §2.3).

The two exceptions name the connection rather than the payload: `Host`, because
the destination has changed, and the hop-by-hop headers of RFC 9110 §7.6.1,
because they describe a connection this is not. `Content-Type`,
`Content-Encoding`, `Content-Length` and `User-Agent` go through untouched --
they are what the Collector needs in order to read what the exporter sent.

Nothing here parses a body, and nothing here looks at the Collector's answer
beyond its status: a forward's outcome belongs in the manifest (`SPEC.md`
§4.5), and the Collector's own response body is not part of the capture.
"""

from __future__ import annotations

import http.client
from collections.abc import Sequence

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

# Plus `Host`, which names the destination -- and the destination has changed.
NOT_FORWARDED = HOP_BY_HOP | {"host"}

DEFAULT_TIMEOUT = 5.0


def forwardable(
    headers: Sequence[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Every header as received, in order, minus the ones about the connection.

    Repeats survive, because a header may legally repeat and the capture kept
    both (`SPEC.md` §2.3). Names and values are untouched.
    """
    return [
        (name, value) for name, value in headers if name.lower() not in NOT_FORWARDED
    ]


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

    def __call__(
        self,
        method: str,
        path: str,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> int:
        connection = http.client.HTTPConnection(
            self.host, self.port, timeout=self.timeout
        )
        try:
            # `skip_host` and `skip_accept_encoding`: `http.client` would
            # otherwise add a `Host` and an `Accept-Encoding: identity` of its
            # own, and this forward sends the exporter's headers, not ours.
            connection.putrequest(
                method, path, skip_host=True, skip_accept_encoding=True
            )
            connection.putheader("Host", f"{self.host}:{self.port}")
            for name, value in forwardable(headers):
                connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()
