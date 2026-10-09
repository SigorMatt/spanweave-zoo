"""The stock Collector: the pin, and the one way it is started.

`SPEC.md` §4.1 and §4.6. Everything about running another process lives behind
the `launch` seam defined here, so that `capture.py` never starts one itself
and a test can drive the whole tee with a launcher that starts nothing.

Three refusals are the point of this module (`CLAUDE.md`, "Honest refusal beats
a reassuring pass"):

- no `VERSION` or no `config.yaml` in `--collector-dir`: there is no pin, so
  there is nothing to label a capture with;
- no binary: say so, and name `make collector`;
- a binary whose `--version` is not the pin: a capture labelled with a version
  that did not re-encode it would be worse than one labelled with nothing.

Nothing here reads a clock. The readiness wait is a bounded number of looks
with the injected `sleep` between them (`SPEC.md` §4.8), so a Collector that
never comes up is a refusal rather than a hang, and the waiting is something a
caller chose rather than something this module did.

What a look consists of is the point of `READY_MARKER`. A connection the port
accepts says only that *something* is there: a stranger already holding 4320
accepts it too, and the Collector that could not have the port has meanwhile
exited. So readiness is the Collector's **own** statement that it is running,
read from its own log, **and** a connection its receiver accepts -- both, every
time (`SPEC.md` §4.6). The child's output is piped here and drained by a thread
rather than inherited, so the refusal can quote the Collector's last words
instead of telling an operator to scroll.
"""

from __future__ import annotations

import os
import socket
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Protocol

BINARY_NAME = "otelcol-contrib"
VERSION_NAME = "VERSION"
CONFIG_NAME = "config.yaml"
SHA256SUMS_NAME = "SHA256SUMS"

DEFAULT_DIR = Path("collector")

# `collector/config.yaml`'s three `${env:...}` endpoints (`SPEC.md` §4.2).
ENV_GRPC = "ZOO_COLLECTOR_OTLP_GRPC"
ENV_HTTP = "ZOO_COLLECTOR_OTLP_HTTP"
ENV_JSON_SINK = "ZOO_JSON_SINK"

# How long to wait for the Collector to come up: a bounded number of looks, not
# a deadline, because a deadline needs a clock.
READY_ATTEMPTS = 150
READY_PAUSE = 0.1
READY_CONNECT_TIMEOUT = 0.25

# The line the stock Collector logs, at `info`, once every component in its
# pipeline has started (`service.go`). It is the only thing that says the
# Collector itself is running, which is why `collector/config.yaml` leaves
# `service.telemetry.logs.level` at the stock `info` (`SPEC.md` §4.2): at
# `warn` the Collector says nothing at all on a clean start, and a readiness
# check would have nothing to read.
READY_MARKER = "Everything is ready. Begin running and processing data."

# How many of the Collector's own lines a refusal quotes.
LOG_TAIL = 8


class CollectorRefused(Exception):
    """The Collector cannot be run as pinned, so the capture does not start."""


@dataclass(frozen=True, slots=True)
class Pin:
    """What `collector/` says the Collector is (`SPEC.md` §4.1)."""

    version: str
    config: Path
    binary: Path


def pin(directory: Path = DEFAULT_DIR) -> Pin:
    """Read the pin. Raises `CollectorRefused` if `collector/` is not there.

    The binary is **not** required here: the version and the config are the
    record and are checked in, while the binary is a gitignored download, and a
    caller that only needs the pin (to label a capture) should not need 100 MB
    on disk to get it.
    """
    version_file = directory / VERSION_NAME
    config = directory / CONFIG_NAME
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError as missing:
        raise CollectorRefused(
            f"no {version_file}: there is no pinned Collector version to label "
            f"a capture with (SPEC.md section 4.1). Point --collector-dir at "
            f"the repository's collector/ directory."
        ) from missing
    if not version:
        raise CollectorRefused(f"{version_file} is empty")
    if not config.is_file():
        raise CollectorRefused(
            f"no {config}: the Collector's config is checked in and is what it "
            f"runs (SPEC.md section 4.2)."
        )
    return Pin(version=version, config=config, binary=directory / BINARY_NAME)


class Running(Protocol):
    """A Collector that is up.

    Two things are asked of it: stop, and say whether it is still there. The
    second is what lets `zoo capture` notice a Collector that exited during a
    run and record it rather than finish with a silently empty `json/`
    (`SPEC.md` §4.6).
    """

    def stop(self) -> None: ...

    def returncode(self) -> int | None: ...


class Launcher(Protocol):
    """The `launch` seam (`SPEC.md` §4.8).

    `version()` is what the thing that would run reports -- checked against the
    pin before anything is recorded. `start()` returns once the Collector has
    reported itself ready and its receiver accepts a connection, or raises
    `CollectorRefused`.
    """

    def version(self) -> str: ...

    def start(self, json_endpoint: str) -> Running: ...


class ChildLog:
    """The Collector's own log, read off its pipe as the child writes it.

    A thread drains the pipe because a pipe nobody reads fills up and stops the
    child, and because `start()` has to be able to *ask* what the log says
    without blocking on a read that may never return. Each line is kept and
    echoed, so the operator still sees the Collector's log as it happens and a
    refusal can quote it (`SPEC.md` §4.6).
    """

    def __init__(self, stream: IO[bytes], echo: Callable[[str], None]) -> None:
        self._stream = stream
        self._echo = echo
        self._lines: list[str] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._drain, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _drain(self) -> None:
        for raw in self._stream:
            # `replace`: this is a stranger's process writing bytes, and a log
            # line that is not UTF-8 is a line to show, not a crash.
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            with self._lock:
                self._lines.append(line)
            self._echo(line)

    def says(self, marker: str) -> bool:
        """Whether any line the child has written so far contains `marker`."""
        with self._lock:
            return any(marker in line for line in self._lines)

    def tail(self, count: int = LOG_TAIL) -> str:
        """The child's last few lines, for a refusal to quote."""
        with self._lock:
            lines = self._lines[-count:]
        return "\n".join(lines) if lines else "(it logged nothing)"

    def close(self) -> None:
        self._thread.join(timeout=5)
        self._stream.close()


@dataclass(frozen=True, slots=True)
class _Process:
    """A started `otelcol-contrib`, stopped by asking and then by insisting."""

    process: subprocess.Popen[bytes]
    log: ChildLog = field(compare=False)

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
        self.log.close()

    def returncode(self) -> int | None:
        """The child's exit status, or `None` while it is still running."""
        return self.process.poll()


class Binary:
    """The real launcher: the pinned `otelcol-contrib`, with the checked-in config.

    The config is passed unedited and the ports arrive through the environment
    (`SPEC.md` §4.2), so the file that is checked in is the file that runs.
    """

    def __init__(
        self,
        pinned: Pin,
        *,
        host: str,
        http_port: int,
        grpc_port: int,
        sleep: Callable[[float], None],
        attempts: int = READY_ATTEMPTS,
        pause: float = READY_PAUSE,
        log: Callable[[str], None] = print,
    ) -> None:
        self.pin = pinned
        self.host = host
        self.http_port = http_port
        self.grpc_port = grpc_port
        self._sleep = sleep
        self._attempts = attempts
        self._pause = pause
        # Where the child's own log goes. It is piped rather than inherited so
        # that a refusal can quote it; echoing each line keeps the operator's
        # view of it unchanged, verbatim and as it happens.
        self._log = log

    def version(self) -> str:
        """What the binary says it is: `otelcol-contrib version 0.162.0`."""
        if not self.pin.binary.is_file():
            raise CollectorRefused(
                f"no {self.pin.binary}: the pinned Collector is a gitignored "
                f"download (SPEC.md section 4.1). Run `make collector`."
            )
        try:
            reported = subprocess.run(
                [str(self.pin.binary), "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as broken:
            raise CollectorRefused(
                f"{self.pin.binary} --version failed: {broken}"
            ) from broken
        words = (reported.stdout + reported.stderr).split()
        return words[-1] if words else ""

    def environment(self, json_endpoint: str) -> dict[str, str]:
        """The three endpoints `collector/config.yaml` reads (`SPEC.md` §4.2)."""
        return {
            ENV_GRPC: f"{self.host}:{self.grpc_port}",
            ENV_HTTP: f"{self.host}:{self.http_port}",
            ENV_JSON_SINK: json_endpoint,
        }

    def start(self, json_endpoint: str) -> Running:
        # The child inherits this process's environment -- it needs a PATH and
        # a HOME like any other program -- with the three endpoints overridden.
        environment = dict(os.environ)
        environment.update(self.environment(json_endpoint))
        process = subprocess.Popen(
            [str(self.pin.binary), "--config", str(self.pin.config)],
            env=environment,
            stdin=subprocess.DEVNULL,
            # One pipe for both, so the log reads in the order the Collector
            # wrote it. It is drained by `ChildLog`'s thread from here on.
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stream = process.stdout
        if stream is None:  # pragma: no cover - `stdout=PIPE` always gives one
            process.kill()
            raise CollectorRefused("the Collector's output could not be read")
        child_log = ChildLog(stream, self._log)
        child_log.start()
        running = _Process(process=process, log=child_log)
        try:
            self._wait_until_ready(running)
        except CollectorRefused:
            running.stop()
            raise
        return running

    def _wait_until_ready(self, running: _Process) -> None:
        """Wait for the Collector to say it is ready, a bounded number of looks.

        Two conditions, both required (`SPEC.md` §4.6):

        - the Collector's **own** ready line is in its log. Only the Collector
          can say that every component in its pipeline started; a port that
          accepts a connection cannot say it, because a stranger already
          holding that port accepts one too;
        - the receiver accepts a connection, which is the one question the tee
          actually asks of it -- can a forward reach this port -- and is asked
          by connecting and closing, so nothing is sent that could end up in a
          capture.

        A child that has exited is the refusal that matters most: it is what
        happens when the port is held, when the config is bad, and when the
        binary cannot run at all. Its own last lines say which.
        """
        for _ in range(self._attempts):
            code = running.returncode()
            if code is not None:
                raise CollectorRefused(
                    f"the Collector exited with {code} before it reported "
                    f"ready on {self.host}:{self.http_port}. The config it "
                    f"was given is {self.pin.config}. Its own log says:\n"
                    f"{running.log.tail()}"
                )
            if running.log.says(READY_MARKER) and self._accepts():
                return
            self._sleep(self._pause)
        raise CollectorRefused(
            f"the Collector did not report ready on "
            f"{self.host}:{self.http_port} after {self._attempts} attempts: "
            f"it never logged {READY_MARKER!r}. Something else may be holding "
            f"that port -- a connection it accepts is not the Collector saying "
            f"it is running. Refusing rather than recording a run whose json/ "
            f"would be empty (SPEC.md section 4.6). Its own log says:\n"
            f"{running.log.tail()}"
        )

    def _accepts(self) -> bool:
        """Whether the receiver accepts a connection, which is then closed."""
        try:
            probe = socket.create_connection(
                (self.host, self.http_port), timeout=READY_CONNECT_TIMEOUT
            )
        except OSError:
            return False
        probe.close()
        return True


def check_version(launcher: Launcher, pinned: Pin) -> str:
    """The pin, having confirmed that what will run reports it (`SPEC.md` §4.5)."""
    reported = launcher.version()
    if reported != pinned.version:
        raise CollectorRefused(
            f"the Collector reports version {reported!r} but the pin is "
            f"{pinned.version!r} (collector/VERSION). A capture labelled with "
            f"a version that did not re-encode it would be worse than one "
            f"labelled with nothing: refusing. Run `make collector` to fetch "
            f"the pinned release."
        )
    return pinned.version
