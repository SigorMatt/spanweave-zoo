"""The test suite's own port picks, and the bounded retry that goes with them.

B1 (`OPEN_QUESTIONS.md` §6, option 4). `zoo capture` picks no port: it binds
the ones it is named, and a port something else holds is the refusal `SPEC.md`
§4.6 specifies. The race the close review registered was the **harness's**:
`test_the_collector_killed_by_hand_mid_capture_is_a_problem` picked a free
port, released it, and something took it before the Collector bound it.

So the harness picks as little as it can and owns what is left of the race:

- the two sinks bind themselves, so they are given `0` and the ports they got
  are read back from what `zoo capture` prints (§4.2) -- nothing to pick;
- the Collector must be told its ports before it exists, so those are still
  picked here, and a start whose refusal names an address in use is **started
  again, whole**, on new picks: at most `ATTEMPTS` times, every port tried
  logged, and the failure after the last naming them all. A refusal for any
  other reason is not retried; it is the test's to see.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from typing import TypeVar

import pytest

from spanweave_zoo import capture, collector

HOST = "127.0.0.1"
ATTEMPTS = 5
# The words both the stock Collector (`bind: address already in use`) and the
# stand-ins (`OSError: [Errno 98] Address already in use`) put in a log the
# refusal quotes (`SPEC.md` §4.6), compared without case.
IN_USE = "address already in use"

T = TypeVar("T")


class PortTaken(Exception):
    """A start refused because a picked port was taken before it was bound."""


def free_port() -> int:
    """A port a child can be told to bind before it exists -- for now.

    Bound on the loopback and released, so something else can take it before
    the child binds it. That is the race `with_picked_ports` retries.
    """
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def in_use(refusal: str) -> bool:
    """Whether a refusal names an address in use."""
    return IN_USE in refusal.lower()


def with_picked_ports(
    start: Callable[[tuple[int, ...]], T],
    *,
    count: int,
    pick: Callable[[], int] = free_port,
    attempts: int = ATTEMPTS,
    log: Callable[[str], object] = print,
) -> T:
    """`start(ports)` on `count` picked ports, again while it raises `PortTaken`.

    Bounded: after `attempts` starts the test fails, naming every port tried.
    `log` gets one line per attempt, so a run that needed a second start says
    so in the captured output rather than passing as if it had not.
    """
    tried: list[tuple[int, ...]] = []
    for attempt in range(1, attempts + 1):
        ports = tuple(pick() for _ in range(count))
        tried.append(ports)
        log(f"harness: start {attempt} of {attempts} on picked ports {ports}")
        try:
            return start(ports)
        except PortTaken as taken:
            log(f"harness: start {attempt} refused, an address in use:\n{taken}")
    pytest.fail(
        f"every one of {attempts} starts was refused on an address in use; "
        f"picked ports tried: {tried}"
    )


def started_capture(
    build: Callable[[int], capture.Capture],
    *,
    pick: Callable[[], int] = free_port,
    attempts: int = ATTEMPTS,
) -> capture.Capture:
    """An in-process `Capture` on a picked Collector port, started.

    `build(port)` makes the capture with its Collector on `port`; a start the
    Collector refuses on an address in use is built and started again.
    """

    def start(ports: tuple[int, ...]) -> capture.Capture:
        (port,) = ports
        started = build(port)
        try:
            started.start()
        except collector.CollectorRefused as refused:
            if in_use(str(refused)):
                raise PortTaken(str(refused)) from refused
            raise
        return started

    return with_picked_ports(start, count=1, pick=pick, attempts=attempts)
