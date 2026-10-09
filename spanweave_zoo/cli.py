"""The `zoo` command line.

Two subcommands today:

- `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` records what an
  exporter POSTs, byte for byte (`SPEC.md` §3, A1);
- `zoo verify [path]` re-hashes every capture against its manifest
  (`SPEC.md` §3.5; the rest of `MANIFEST.json` is §5, A3).

`capture` (A2), `replay` (A4) and `audit` (A5) are not here and are not
stubbed; `SPEC.md` §§4, 6 and 7 are the headings they will fill.

This module is also where the **clock** lives. No other module under
`spanweave_zoo/` reads one: the sink takes `now` as an argument
(`SPEC.md` §3.6), so a recorded timestamp in a test is a value the test chose,
and `_system_clock` below is the single place the real time enters the package.

`verify` refuses rather than reassures. A run with no readable `MANIFEST.json`
has nothing to re-hash against, and saying so with a non-zero exit is the one
failure mode this command exists to prevent (`CLAUDE.md`, "Honest refusal
beats a reassuring pass").
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from spanweave_zoo import __version__, manifest, sink

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
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
