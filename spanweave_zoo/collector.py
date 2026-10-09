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

Nothing here reads a clock. The readiness wait is a bounded number of
connection attempts with the injected `sleep` between them (`SPEC.md` §4.8),
so a Collector that never listens is a refusal rather than a hang, and the
waiting is something a caller chose rather than something this module did.
"""

from __future__ import annotations

import os
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

BINARY_NAME = "otelcol-contrib"
VERSION_NAME = "VERSION"
CONFIG_NAME = "config.yaml"
SHA256SUMS_NAME = "SHA256SUMS"

DEFAULT_DIR = Path("collector")

# `collector/config.yaml`'s three `${env:...}` endpoints (`SPEC.md` §4.2).
ENV_GRPC = "ZOO_COLLECTOR_OTLP_GRPC"
ENV_HTTP = "ZOO_COLLECTOR_OTLP_HTTP"
ENV_JSON_SINK = "ZOO_JSON_SINK"

# How long to wait for the receiver to accept a connection: a bounded number of
# attempts, not a deadline, because a deadline needs a clock.
READY_ATTEMPTS = 150
READY_PAUSE = 0.1
READY_CONNECT_TIMEOUT = 0.25


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
    """A Collector that is up. Stopping it is the only thing asked of it."""

    def stop(self) -> None: ...


class Launcher(Protocol):
    """The `launch` seam (`SPEC.md` §4.8).

    `version()` is what the thing that would run reports -- checked against the
    pin before anything is recorded. `start()` returns once the receiver is
    accepting connections, or raises `CollectorRefused`.
    """

    def version(self) -> str: ...

    def start(self, json_endpoint: str) -> Running: ...


@dataclass(frozen=True, slots=True)
class _Process:
    """A started `otelcol-contrib`, stopped by asking and then by insisting."""

    process: subprocess.Popen[bytes]

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)


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
    ) -> None:
        self.pin = pinned
        self.host = host
        self.http_port = http_port
        self.grpc_port = grpc_port
        self._sleep = sleep
        self._attempts = attempts
        self._pause = pause

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
        )
        running = _Process(process=process)
        try:
            self._wait_until_listening(process)
        except CollectorRefused:
            running.stop()
            raise
        return running

    def _wait_until_listening(self, process: subprocess.Popen[bytes]) -> None:
        """Connect to the receiver until it answers, a bounded number of times.

        A connection that is accepted and immediately closed is the cheapest
        honest readiness check there is: it asks the one question that matters
        -- can the raw sink's forward reach this port -- without sending the
        Collector anything that would end up in a capture.
        """
        for _ in range(self._attempts):
            if process.poll() is not None:
                raise CollectorRefused(
                    f"the Collector exited with {process.returncode} before it "
                    f"listened on {self.host}:{self.http_port}. Its own log is "
                    f"above: the config it was given is {self.pin.config}."
                )
            try:
                probe = socket.create_connection(
                    (self.host, self.http_port), timeout=READY_CONNECT_TIMEOUT
                )
            except OSError:
                self._sleep(self._pause)
                continue
            probe.close()
            return
        raise CollectorRefused(
            f"the Collector did not accept a connection on "
            f"{self.host}:{self.http_port} after {self._attempts} attempts. "
            f"Refusing rather than recording a run whose json/ would be empty "
            f"(SPEC.md section 4.6)."
        )


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
