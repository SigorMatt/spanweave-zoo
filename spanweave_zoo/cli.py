"""The `zoo` command line.

Three subcommands today:

- `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` records what an
  exporter POSTs, byte for byte (`SPEC.md` §3, A1);
- `zoo capture --project z4 --run-id <id>` runs the whole tee: the raw sink the
  exporter talks to, the stock Collector behind it, and the json sink the
  Collector's JSON re-encoding lands in (`SPEC.md` §4, A2);
- `zoo verify [path]` re-hashes every capture against its manifest
  (`SPEC.md` §3.5; the rest of `MANIFEST.json` is §5, A3).

`replay` (A4) and `audit` (A5) are not here and are not stubbed; `SPEC.md` §§6
and 7 are the headings they will fill.

This module is also where the **clock** lives, and the **sleep**. No other
module under `spanweave_zoo/` reads either: the sink takes `now` as an argument
(`SPEC.md` §3.6) and the Collector's readiness wait takes `sleep`
(`SPEC.md` §4.8), so a recorded timestamp in a test is a value the test chose,
and `_system_clock` below is the single place the real time enters the package.

`verify` refuses rather than reassures. A run with no readable `MANIFEST.json`
has nothing to re-hash against, and saying so with a non-zero exit is the one
failure mode this command exists to prevent (`CLAUDE.md`, "Honest refusal
beats a reassuring pass").
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

from spanweave_zoo import __version__, capture, collector, forward, manifest, sink

# What `zoo capture` stops on. `SIGINT` is the operator's Ctrl-C; `SIGTERM` is
# whatever supervises the process when a pet project's run ends.
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)

# `captures/<project>/<run-id>/` -- `SPEC.md` §2. A run directory is what
# `verify` counts; the project level carries nothing of its own.
CAPTURES = Path("captures")
_RUN_DEPTH = 2

DEFAULT_PORT = 4318
DEFAULT_HOST = "127.0.0.1"


def _system_clock() -> str:
    """The real clock, in UTC, ISO-8601 -- the sink's `now` seam in production.

    The one clock read in `spanweave_zoo/`, passed in rather than reached for,
    so that every other module can be run on a clock a test chose.
    """
    return datetime.now(UTC).isoformat()


def _system_sleep(seconds: float) -> None:
    """The real `sleep`, the Collector's readiness seam (`SPEC.md` §4.8).

    Here for the same reason as the clock: nothing under `spanweave_zoo/`
    sleeps on its own, so a test never waits for anything it did not choose to
    wait for.
    """
    time.sleep(seconds)


def _run_directories(root: Path) -> list[Path]:
    """Every `<project>/<run-id>` directory under `root`, in sorted order."""
    if not root.is_dir():
        return []
    runs = [
        path
        for path in root.glob("/".join(["*"] * _RUN_DEPTH))
        if path.is_dir() and not path.name.startswith(".")
    ]
    return sorted(runs)


def verify(root: Path) -> int:
    """Re-hash every capture under `root`. Returns a process exit status."""
    runs = _run_directories(root)
    if not runs:
        print(f"zoo verify: no captures under {root}/ -- nothing to re-hash")
        return 0
    print(f"zoo verify: {len(runs)} capture(s) under {root}/:")
    problems: list[str] = []
    for run in runs:
        found = manifest.problems(run)
        bodies = manifest.body_count(run)
        print(f"  {run}: {bodies} body/bodies, {len(found)} problem(s)")
        problems.extend(found)
    if problems:
        for problem in problems:
            print(f"  ! {problem}")
        print(
            f"zoo verify: {len(problems)} problem(s). A capture is immutable "
            f"(CLAUDE.md section 0.6): these bytes are not the bytes that "
            f"were recorded."
        )
        return 1
    print("zoo verify: every recorded body still hashes to what was recorded")
    return 0


def run_sink(host: str, port: int, out: Path) -> int:
    """Serve until interrupted, recording every POST. `SPEC.md` §3."""
    try:
        recorder = sink.Recorder(out, now=_system_clock, after_record=_announce)
    except sink.CaptureExists as refused:
        print(f"zoo sink: refusing to start: {refused}", file=sys.stderr)
        return 2
    server = sink.make_server(recorder, host=host, port=port)
    # The port the socket actually got, which is not `port` when `port` is 0.
    bound_port = server.server_address[1]
    print(f"zoo sink: recording POST {sink.TRACES_PATH} on http://{host}:{bound_port}")
    print(f"zoo sink: bodies to {recorder.raw}/, anything else to {recorder.rejected}/")
    print("zoo sink: it parses nothing. Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nzoo sink: stopped. {manifest.body_count(recorder.run)} body/bodies.")
    finally:
        server.server_close()
    return 0


def _stop_on_signal(running: capture.Capture) -> dict[int, Any]:
    """Make `SIGINT` and `SIGTERM` end the run cleanly. `SPEC.md` §4.6.

    Installed rather than relied upon: the pending-signal machinery runs a
    Python handler only when the main thread executes bytecode, and a capture
    has three threads blocked in `select` for the kernel to deliver the signal
    to instead. The handler only sets an event (`Capture.request_stop`); the
    actual shutdown happens on the main thread, which is where the Collector
    gets stopped rather than orphaned holding its port.

    Returns the handlers it replaced, so a caller can put them back.
    """

    def handler(number: int, frame: FrameType | None) -> None:
        running.request_stop()

    previous: dict[int, Any] = {}
    for number in STOP_SIGNALS:
        previous[number] = signal.getsignal(number)
        signal.signal(number, handler)
    return previous


def _restore_signals(previous: dict[int, Any]) -> None:
    for number, handler in previous.items():
        signal.signal(number, handler)


def _run_directory(captures: Path, project: str, run_id: str) -> Path:
    """`captures/<project>/<run-id>`, having checked both are segments.

    `SPEC.md` §2.1: one path segment, not starting with a dot. A run id with a
    slash in it would scatter one capture across two directories and a run id
    of `..` would write outside the capture root; both are a refusal rather
    than something the zoo tidies up.
    """
    for label, value in (("--project", project), ("--run-id", run_id)):
        if not value or "/" in value or "\\" in value or value.startswith("."):
            raise ValueError(
                f"{label} must be a single path segment that does not start "
                f"with a dot (SPEC.md section 2.1): {value!r}"
            )
    return captures / project / run_id


def run_capture(args: argparse.Namespace) -> int:
    """The whole tee, serving until interrupted. `SPEC.md` §4.6."""
    try:
        run = _run_directory(Path(args.captures), args.project, args.run_id)
        pinned = collector.pin(Path(args.collector_dir))
    except (ValueError, collector.CollectorRefused) as refused:
        print(f"zoo capture: refusing to start: {refused}", file=sys.stderr)
        return 2

    launcher = collector.Binary(
        pinned,
        host=args.host,
        http_port=args.collector_port,
        grpc_port=args.collector_grpc_port,
        sleep=_system_sleep,
    )
    running = capture.Capture(
        run,
        now=_system_clock,
        launcher=launcher,
        forward=forward.HttpForward(
            args.host, args.collector_port, timeout=args.forward_timeout
        ),
        pin=pinned,
        host=args.host,
        raw_port=args.port,
        json_port=args.json_port,
    )
    try:
        running.start()
    except (collector.CollectorRefused, sink.CaptureExists, OSError) as refused:
        print(f"zoo capture: refusing to start: {refused}", file=sys.stderr)
        return 2
    print("zoo capture: the raw bytes are the record. Ctrl-C to stop.", flush=True)
    previous = _stop_on_signal(running)
    try:
        running.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nzoo capture: stopping", flush=True)
        running.stop()
        _restore_signals(previous)
    print(running.summary())
    # A run whose json/ is incomplete must not look like one that is complete
    # (`SPEC.md` §4.4). The capture itself is intact either way.
    return 1 if running.failed_forwards else 0


def _announce(entry: manifest.BodyEntry) -> None:
    """The `after_record` seam, in production: one line per recorded body.

    Flushed, because an operator watching a pet project export into a log file
    should see each body as it lands rather than when the sink is killed.
    """
    print(
        f"  {entry.file}  {entry.bytes} bytes  sha256:{entry.sha256[:12]}",
        flush=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zoo",
        description=(
            "Record what real OTLP exporters send, byte for byte. "
            "Pre-release: nothing here is frozen."
        ),
    )
    parser.add_argument("--version", action="version", version=f"zoo {__version__}")
    subcommands = parser.add_subparsers(dest="command")

    sink_parser = subcommands.add_parser(
        "sink",
        help="record every POST's bytes and headers, and parse nothing",
    )
    sink_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"port to listen on (default: {DEFAULT_PORT})",
    )
    sink_parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"address to bind (default: {DEFAULT_HOST})",
    )
    sink_parser.add_argument(
        "--out",
        required=True,
        help="the run's raw/ directory: captures/<project>/<run-id>/raw",
    )

    capture_parser = subcommands.add_parser(
        "capture",
        help="the tee: the raw sink, the stock Collector behind it, the json sink",
    )
    capture_parser.add_argument("--project", required=True, help="z1 ... z6 (SPEC 2.1)")
    capture_parser.add_argument(
        "--run-id", required=True, help="one path segment, not starting with a dot"
    )
    capture_parser.add_argument(
        "--captures", default=str(CAPTURES), help=f"capture root (default: {CAPTURES})"
    )
    capture_parser.add_argument(
        "--port",
        type=int,
        default=capture.DEFAULT_RAW_PORT,
        help=(f"the raw sink: the app's port (default: {capture.DEFAULT_RAW_PORT})"),
    )
    capture_parser.add_argument(
        "--json-port",
        type=int,
        default=capture.DEFAULT_JSON_PORT,
        help=f"the json sink (default: {capture.DEFAULT_JSON_PORT})",
    )
    capture_parser.add_argument(
        "--collector-port",
        type=int,
        default=capture.DEFAULT_COLLECTOR_PORT,
        help=(
            f"the Collector's OTLP/HTTP receiver "
            f"(default: {capture.DEFAULT_COLLECTOR_PORT})"
        ),
    )
    capture_parser.add_argument(
        "--collector-grpc-port",
        type=int,
        default=capture.DEFAULT_COLLECTOR_GRPC_PORT,
        help=(
            f"its gRPC receiver, which the tee never feeds "
            f"(default: {capture.DEFAULT_COLLECTOR_GRPC_PORT})"
        ),
    )
    capture_parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"what all three bind (default: {DEFAULT_HOST})",
    )
    capture_parser.add_argument(
        "--collector-dir",
        default=str(collector.DEFAULT_DIR),
        help=(
            f"where VERSION, SHA256SUMS and config.yaml are "
            f"(default: {collector.DEFAULT_DIR}/)"
        ),
    )
    capture_parser.add_argument(
        "--forward-timeout",
        type=float,
        default=forward.DEFAULT_TIMEOUT,
        help=f"seconds (default: {forward.DEFAULT_TIMEOUT})",
    )

    verify_parser = subcommands.add_parser(
        "verify",
        help="re-hash every capture against its manifest",
    )
    verify_parser.add_argument(
        "path",
        nargs="?",
        default=str(CAPTURES),
        help=f"capture root to verify (default: {CAPTURES}/)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        return verify(Path(args.path))
    if args.command == "sink":
        return run_sink(args.host, args.port, Path(args.out))
    if args.command == "capture":
        return run_capture(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
