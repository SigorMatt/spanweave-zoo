"""The `zoo` command line.

Five subcommands today:

- `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` records what an
  exporter POSTs, byte for byte (`SPEC.md` §3, A1);
- `zoo capture --project z4 --run-id <id> --kind real --project-manifest <path>`
  runs the whole tee: the raw sink the exporter talks to, the stock Collector
  behind it, the json sink the Collector's JSON re-encoding lands in
  (`SPEC.md` §4, A2), and the `MANIFEST.json` it ends by completing
  (`SPEC.md` §5, A3);
- `zoo replay <run> --to http://host:port [--raw|--json] [--timing]` sends a
  capture's bodies to another receiver with their captured heads, adding
  nothing (`SPEC.md` §6, A4);
- `zoo verify [path]` re-hashes every capture against its manifest -- a whole
  capture root, or one run directory (`SPEC.md` §3.5, §5).

- `zoo audit <run> [--out audit]` runs a capture through `spanweave-live
  serve`, `spanweave.build` and `agentgolden`'s signature and writes
  `audit/<project>-<run-id>.md`, every finding naming its owner (`SPEC.md` §7,
  A5). It needs the `audit` extra, and is the one subcommand that does: its
  module is imported only when it runs (`run_audit`).

This module is also where the **clock** lives, and the **sleep**. No other
module under `spanweave_zoo/` reads either: the sink takes `now` as an argument
(`SPEC.md` §3.6) and the Collector's readiness wait, the replayer's
`--timing` and the audit's two timed replays all take `sleep` (`SPEC.md` §4.8,
§6.3, §7.6), so a recorded timestamp in
a test is a value the test chose,
and `_system_clock` below is the single place the real time enters the package.

`verify` refuses rather than reassures, and exits one of three statuses
(`SPEC.md` §5.6):

- **1** -- it checked a capture and the capture failed: a digest or a length
  that differs, a listed file missing, a file on disk the manifest never
  listed, no readable `MANIFEST.json`, no `ended_at` (the run was never
  completed), a `kind` the spec does not name, or a recorded `problem`;
- **2** -- it checked nothing, because the path it was given is not a capture.
  A path the operator **typed** is a claim that a capture is there, so an
  absent directory, a file, or a directory holding no run is a refusal naming
  the path. Reporting "nothing to re-hash" and exiting zero over a typo is the
  one failure mode this command exists to prevent (`CLAUDE.md`, "Honest
  refusal beats a reassuring pass");
- **0** -- every recorded body still hashes to what was recorded, or the
  **default** root holds no captures at all. That last one is deliberate and
  is the only place emptiness passes: `make verify` runs on a repository whose
  `captures/` is empty, and it also re-hashes the one real capture committed
  under `tests/fixtures/capture/`, so the gate checks bytes on every run
  rather than reporting a clean tree.

`--kind` is required on `capture` and has no default. A `recorded` capture and
a `real` one differ by that declaration alone, the audit reads it as the
truth, and argparse refusing the command is better than the zoo guessing
(`SPEC.md` §5).
"""

from __future__ import annotations

import argparse
import os
import signal
import socketserver
import sys
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import IO, Any

from spanweave_zoo import (
    __version__,
    capture,
    collector,
    forward,
    manifest,
    replay,
    sink,
)

# What `zoo capture` stops on. `SIGINT` is the operator's Ctrl-C; `SIGTERM` is
# whatever supervises the process when a pet project's run ends; `SIGHUP` is
# the terminal going away -- its window closed, its ssh session dropped. The
# Collector is in a session of its own (`SPEC.md` §4.6) and hears none of them,
# so a hang-up left to its default action killed `zoo capture` alone and left
# the Collector running, holding its port, with the manifest never completed
# (run-2b review N-2). All three end the run the same way.
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

# `captures/<project>/<run-id>/` -- `SPEC.md` §2. A run directory is what
# `verify` counts; the project level carries nothing of its own.
CAPTURES = Path("captures")
_RUN_DEPTH = 2

DEFAULT_PORT = 4318
DEFAULT_HOST = "127.0.0.1"

# `zoo sink`'s banner. It and `capture.READY_LINE` both end "Ctrl-C to stop."
# and mean different things -- bytes recorded with nothing behind the sink, as
# against a whole tee up and re-encoding -- so each names its own command and
# neither is a prefix of the other. An operator reading a log should not have
# to work out which command wrote it (`SPEC.md` §3, §4.6).
SINK_BANNER = "zoo sink: it parses nothing. Ctrl-C to stop."


def _system_clock() -> str:
    """The real clock, in UTC, ISO-8601 -- the sink's `now` seam in production.

    The one clock read in `spanweave_zoo/`, passed in rather than reached for,
    so that every other module can be run on a clock a test chose.
    """
    return datetime.now(UTC).isoformat()


def _system_sleep(seconds: float) -> None:
    """The real `sleep`: the Collector's readiness seam (`SPEC.md` §4.8), and
    `zoo replay --timing`'s recorded gaps (`SPEC.md` §6.3).

    Here for the same reason as the clock: nothing under `spanweave_zoo/`
    sleeps on its own, so a test never waits for anything it did not choose to
    wait for -- and a replay of a capture whose gaps are hours long is a test
    nobody could write otherwise.
    """
    time.sleep(seconds)


class Progress:
    """`zoo capture`'s stdout: flushed every line, and never fatal.

    Two jobs, both of them `SPEC.md` §4.6's. Every line is **flushed as it is
    written**, because an operator watching a pet project export sees each body
    as it lands rather than when the capture is stopped.

    And a stdout nobody is reading any more ends the run instead of killing it.
    `zoo capture | head -5` closes the pipe while three threads are recording;
    the next `print` raises `BrokenPipeError`, and a traceback out of a sink's
    handler thread would leave the capture half-finished with a manifest that
    was never completed. So the first broken pipe asks the run to stop, further
    lines go nowhere, and the file descriptor is pointed at `os.devnull` so the
    interpreter's own flush at exit cannot raise either. The capture then ends
    the way Ctrl-C ends it: the manifest is completed, and the exit status is
    what the capture was, not what the pipe did. A terminal that hung up is
    the same event by another errno: its next write fails with `EIO`.
    """

    def __init__(self, stream: IO[str] | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout
        self.broken = False
        # Set once the run exists: the first broken pipe asks it to stop.
        self.on_broken: Callable[[], None] | None = None

    def __call__(self, line: str) -> None:
        if self.broken:
            return
        try:
            print(line, file=self._stream, flush=True)
        except (OSError, ValueError):
            # `BrokenPipeError` is a reader that went away; any other `OSError`
            # is the terminal that did -- a write to a tty that hung up fails
            # with `EIO`, and it arrives with the `SIGHUP` that is already
            # ending the run (`STOP_SIGNALS`). Left to propagate, it escaped
            # from the `finally` that stops the Collector. `ValueError` is the
            # same event seen a moment later: a stream already closed under us.
            self.broken = True
            _silence(self._stream)
            if self.on_broken is not None:
                self.on_broken()


def _silence(stream: IO[str]) -> None:
    """Point the stream's own file descriptor at `os.devnull`.

    Python flushes `sys.stdout` as the interpreter exits, and a flush onto a
    pipe nobody is reading prints `Exception ignored` and changes the exit
    status -- after the manifest is already complete and the capture already
    fine. This is the stdlib's own answer to `BrokenPipeError`, and it lives
    here because `cli.py` is the one module allowed to touch the world. A
    stream with no file descriptor at all -- a test's, or an interpreter's
    `sys.stdout` that was replaced -- has nothing to silence, which is what the
    last two exceptions below are.
    """
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stream.fileno())
        os.close(devnull)
    except (OSError, ValueError, AttributeError):
        pass


def _is_run(path: Path) -> bool:
    """Whether `path` is itself one run directory rather than a capture root.

    A run directory holds `MANIFEST.json`, or a `raw/` the sink made. This is
    asked because `zoo verify captures/z4/<run-id>` is a thing an operator
    types -- the README tells them to -- and globbing two levels down from a
    run directory would find nothing and say so with a **zero** exit, which is
    the one reassuring pass this command exists to refuse (`CLAUDE.md`).
    """
    return (path / manifest.MANIFEST_NAME).exists() or (path / capture.RAW_DIR).is_dir()


def _run_directories(root: Path) -> list[Path]:
    """Every `<project>/<run-id>` directory under `root`, in sorted order."""
    if not root.is_dir():
        return []
    if _is_run(root):
        return [root]
    runs = [
        path
        for path in root.glob("/".join(["*"] * _RUN_DEPTH))
        if path.is_dir() and not path.name.startswith(".")
    ]
    return sorted(runs)


def verify(root: Path, *, named: bool = False) -> int:
    """Re-hash every capture under `root`. Returns a process exit status.

    `named` is whether the operator typed the path (`SPEC.md` §5.6). A typed
    path is a claim that a capture is there, so finding none is a refusal --
    exit **2**, naming the path, because the command checked nothing. The
    default root is the one path that may legitimately hold nothing: a
    repository that has recorded no captures yet is nothing to re-hash, which
    is `make verify` on a clean tree and exits 0.
    """
    runs = _run_directories(root)
    if not runs:
        if named:
            print(
                f"zoo verify: {root} is not a capture: no "
                f"{manifest.MANIFEST_NAME}, no {capture.RAW_DIR}/, and no "
                f"<project>/<run-id> under it. Nothing was checked "
                f"(SPEC.md section 5.6).",
                file=sys.stderr,
            )
            return 2
        print(f"zoo verify: no captures under {root}/ -- nothing to re-hash")
        return 0
    print(f"zoo verify: {len(runs)} capture(s) under {root}/:")
    problems: list[str] = []
    for run in runs:
        found = manifest.problems(run)
        # The declaration the audit keys off, printed as the capture carries
        # it -- and as nothing where the capture carries nothing (`zoo sink`
        # alone writes no `kind`).
        declared = manifest.kind_of(run) or "none declared"
        print(
            f"  {run}: kind={declared}, {manifest.tally(run)}, {len(found)} problem(s)"
        )
        problems.extend(found)
    if problems:
        for problem in problems:
            print(f"  ! {problem}")
        print(
            f"zoo verify: {len(problems)} problem(s), each named above -- not verified."
        )
        return 1
    print("zoo verify: every recorded body still hashes to what was recorded")
    return 0


def run_sink(host: str, port: int, out: Path) -> int:
    """Serve until interrupted, recording every POST. `SPEC.md` §3.

    Exits 0 once the capture is sealed, and 1 when the sealed manifest
    records a problem -- a POST still being handled when the journals closed,
    or a journal line the assembly could not read (`SPEC.md` §3.7, §5.5).
    """
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
    print(SINK_BANNER, flush=True)
    previous = _shut_down_on_signal(server)
    problems: list[str] = []
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _restore_signals(previous)
        # Close-then-seal, as `zoo capture` does it (`SPEC.md` §3.7, §5.5;
        # B3a): the listener is closed so nothing new is accepted, every POST
        # already being handled is waited for -- for at most the same bound
        # `zoo capture` gives its sinks (§4.6) -- and then the journals are
        # closed, so a handler that outlived the wait writes nothing into a
        # capture whose manifest is about to be sealed. Each one still running
        # is a `problems` entry, written before the assembly.
        server.server_close()
        recorder.settle(capture.FLUSH_WAIT)
        for problem in recorder.close():
            problems.append(problem)
            manifest.append_problem(recorder.run, problem)
        # The run is over, so the manifest is assembled from the journal
        # (`SPEC.md` §5.5). `zoo sink` declares no `kind` and carries no
        # project manifest -- it is the sink alone, with nothing behind it --
        # but what it did record is covered and `ended_at` says the capture is
        # complete, which is what `zoo verify` asks of it.
        problems += manifest.finish(recorder.run, ended_at=_system_clock())
    print(f"\nzoo sink: stopped. {manifest.body_count(recorder.run)} body/bodies.")
    for problem in problems:
        print(f"  ! {problem}")
    # A run that recorded a problem the capture could not fix exits non-zero
    # saying so, as `zoo capture` does (`SPEC.md` §5.6).
    return 1 if problems else 0


class StoppedBeforeReady(Exception):
    """A stop signal that arrived while `zoo capture` was still starting.

    Raised out of the signal handler into `Capture.start`, which unwinds the
    way a refusal does: the Collector stopped, both sinks closed, and nothing
    on disk (`SPEC.md` §4.6; B2, Q1).
    """

    def __init__(self, number: int) -> None:
        self.name = signal.Signals(number).name
        super().__init__(
            f"{self.name} arrived before the capture was ready -- the Collector "
            f"was stopped and nothing was written (SPEC.md section 4.6)"
        )


def _stop_on_signal(running: capture.Capture) -> dict[int, Any]:
    """Make `SIGINT`, `SIGTERM` and `SIGHUP` end the run cleanly. `SPEC.md` §4.6.

    Installed rather than relied upon: the pending-signal machinery runs a
    Python handler only when the main thread executes bytecode, and a capture
    has three threads blocked in `select` for the kernel to deliver the signal
    to instead. Once the run directory exists the handler only sets an event
    (`Capture.request_stop`); the actual shutdown happens on the main thread,
    which is where the Collector gets stopped rather than orphaned holding its
    port.

    Installed **before** the capture starts (B2, Q1), so it covers the
    readiness wait too. Until the run directory is about to be made, the
    first signal raises `StoppedBeforeReady` instead -- the readiness wait has
    no event to look at, and a start that goes on to make a directory is a
    capture the operator asked not to make -- and `Capture.start` unwinds it
    like a refusal, stopping the Collector it already started. It raises
    once: a second signal while that unwind is stopping the Collector only
    asks again, rather than interrupting the stop and orphaning the child.

    Returns the handlers it replaced, so a caller can put them back.
    """
    raised = False

    def handler(number: int, frame: FrameType | None) -> None:
        nonlocal raised
        if not running.committed and not raised:
            raised = True
            raise StoppedBeforeReady(number)
        running.request_stop()

    previous: dict[int, Any] = {}
    for number in STOP_SIGNALS:
        previous[number] = signal.getsignal(number)
        signal.signal(number, handler)
    return previous


def _shut_down_on_signal(server: socketserver.BaseServer) -> dict[int, Any]:
    """Make `zoo sink` end on `SIGINT`, `SIGTERM` and `SIGHUP` alike (B2, Q6).

    `SPEC.md` §3.7. A supervisor's `SIGTERM` or a terminal's `SIGHUP`, left to
    the default action, killed the sink before its manifest was assembled.
    The handler asks the server to shut down from a thread of its own --
    `shutdown()` waits for `serve_forever` to return, and `serve_forever` is
    running on the very thread the handler interrupted -- so the loop returns
    as it would on its own, and the caller's `finally` seals the manifest.

    Returns the handlers it replaced, so a caller can put them back.
    """

    def handler(number: int, frame: FrameType | None) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

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
        # Read now, and **copied** when the run ends (`SPEC.md` §5.3). Both:
        # a path that is not a readable JSON document is a refusal while
        # nothing is on disk and the operator can still fix the typo, and the
        # copy the capture carries is the one the project's own run left
        # behind, which is only knowable at the end.
        project_manifest = Path(args.project_manifest)
        manifest.read_project_manifest(project_manifest)
    except (
        ValueError,
        collector.CollectorRefused,
        manifest.ProjectManifestUnreadable,
    ) as refused:
        print(f"zoo capture: refusing to start: {refused}", file=sys.stderr)
        return 2

    launcher = collector.Binary(
        pinned,
        host=args.host,
        http_port=args.collector_port,
        grpc_port=args.collector_grpc_port,
        sleep=_system_sleep,
    )
    # Every line of the run goes through this: flushed as it is written, and a
    # closed stdout ends the run rather than killing it (`SPEC.md` §4.6).
    progress = Progress()
    running = capture.Capture(
        run,
        now=_system_clock,
        launcher=launcher,
        forward=forward.HttpForward(
            args.host, args.collector_port, timeout=args.forward_timeout
        ),
        pin=pinned,
        kind=args.kind,
        project_manifest=project_manifest,
        host=args.host,
        raw_port=args.port,
        json_port=args.json_port,
        log=progress,
    )
    progress.on_broken = running.request_stop
    # Before `start()`, not after it (B2, Q1): the readiness wait can last most
    # of a minute, and a SIGTERM or SIGHUP in it, left to the default action,
    # killed `zoo capture` and left the Collector -- in its own session -- up
    # and holding its port (`SPEC.md` §4.6).
    previous = _stop_on_signal(running)
    try:
        try:
            running.start()
        except (
            collector.CollectorRefused,
            sink.CaptureExists,
            OSError,
            StoppedBeforeReady,
        ) as refused:
            # Every refusal is before readiness and has written nothing: no
            # run directory, no manifest, no bytes (`SPEC.md` §4.6). `OSError`
            # is the port one -- "address already in use" names the port it
            # is about -- and a stop signal during the start is one too.
            print(f"zoo capture: refusing to start: {refused}", file=sys.stderr)
            return 2
        # The readiness line is `capture.READY_LINE`, printed by `start()`
        # itself once the directory exists, so that there is one place where
        # "a capture is up" is said and it cannot be said by a run that
        # refused.
        try:
            running.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # However the run ends: the Collector is in its own session
            # (`SPEC.md` §4.6) and does not die with the terminal's process
            # group, so a run that left without stopping it would leave it
            # holding its port.
            progress("\nzoo capture: stopping")
            running.stop()
    finally:
        _restore_signals(previous)
    progress(running.summary())
    return _exit_status(running)


def _exit_status(running: capture.Capture) -> int:
    """What `zoo capture` exits with (`SPEC.md` §4.4, §4.6).

    Non-zero when a forward failed or the Collector exited during the run: a
    run whose `json/` is incomplete must not look like one that is complete.
    The capture itself is intact either way, and `MANIFEST.json` says which
    bodies never reached the Collector and what went wrong.
    """
    return 1 if running.failed_forwards or running.problems else 0


def run_replay(args: argparse.Namespace) -> int:
    """Send a capture's bytes to another receiver. `SPEC.md` §6.

    Three statuses, on `verify`'s rule (`SPEC.md` §6.4): **2** when nothing was
    sent -- not a capture, an unreadable manifest, no body on the chosen side,
    a `--to` that is not an `http://host[:port]`; **1** when a send did not
    answer 2xx or could not be made at all; **0** when every body went out and
    every answer was a 2xx.
    """
    run = Path(args.run)
    progress = Progress()
    try:
        host, port = replay.destination(args.to)
        planned = replay.planned(run, args.source)
    except replay.ReplayRefused as refused:
        print(f"zoo replay: refusing to send: {refused}", file=sys.stderr)
        return 2
    progress(
        f"zoo replay: {len(planned)} body/bodies from {run}/{args.source}/ "
        f"to http://{host}:{port}, as captured"
    )
    outcomes = replay.replay(
        run,
        source=args.source,
        send=replay.sender(host, port, timeout=args.timeout),
        timing=args.timing,
        # The seam, and the only sleep in the package (`SPEC.md` §6.3). It is
        # passed only when it is going to be used, so a replay without
        # `--timing` cannot sleep even by accident.
        sleep=_system_sleep if args.timing else None,
        log=progress,
    )
    undelivered = [outcome for outcome in outcomes if not outcome.delivered]
    # Sent is answered: a body whose head could not be read, whose connection
    # was refused or whose answer never came did not reach a receiver, and the
    # last line -- the one a reader of a long replay reads -- must not count
    # it as sent (`SPEC.md` §6.4; run-2b review N-10).
    answered = [outcome for outcome in outcomes if outcome.status is not None]
    turned_away = [outcome for outcome in answered if not outcome.delivered]
    progress(
        f"zoo replay: {len(answered)} sent, {len(turned_away)} that did not answer "
        f"2xx, {len(outcomes) - len(answered)} not sent"
    )
    for outcome in undelivered:
        progress(f"  ! {outcome.file}: {outcome.error or f'status {outcome.status}'}")
    return 1 if undelivered else 0


def run_audit(args: argparse.Namespace) -> int:
    """Audit one capture. `SPEC.md` §7.

    The audit module imports `spanweave`, `spanweave_live` and `agentgolden`,
    which are the `audit` extra's and nobody else's, so it is imported here and
    only here: every other subcommand -- and the bare wheel `make
    install-check` installs -- works without them (`SPEC.md` §7.1). Without
    the extra this is a refusal naming the command that installs it, exit 2.
    """
    try:
        from spanweave_zoo import audit
    except ImportError as missing:
        print(
            f"zoo audit: refusing: the audit needs the `audit` extra, and it is "
            f"not installed ({missing}). Install it with: uv sync --extra dev "
            f"--extra audit",
            file=sys.stderr,
        )
        return 2
    try:
        # The real `sleep` for step 2's two timed replays (`SPEC.md` 7.3,
        # 7.6): the audit sleeps through this seam and nowhere else.
        result = audit.audit(Path(args.run), out=Path(args.out), sleep=_system_sleep)
    except audit.AuditRefused as refused:
        print(f"zoo audit: refusing: {refused}", file=sys.stderr)
        return 2
    owners = ", ".join(
        f"{owner} {sum(1 for f in result.findings if f.owner == owner)}"
        for owner in audit.OWNERS
    )
    print(
        f"zoo audit: wrote {result.path}: {len(result.findings)} finding(s) ({owners})"
    )
    for reason in result.incomplete:
        print(f"  ! incomplete: {reason}")
    return result.exit


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
        "--kind",
        required=True,
        choices=sorted(manifest.KINDS),
        help=(
            "what this capture is: a run against a key-free stub (recorded) "
            "or against a real model (real). Required: there is no default "
            "and nothing is inferred (SPEC.md section 5)"
        ),
    )
    capture_parser.add_argument(
        "--project-manifest",
        required=True,
        help=(
            "path to the pet project's own MANIFEST.json "
            "(EXPORT-CONTRACT.md section 1), copied into the capture verbatim"
        ),
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

    replay_parser = subcommands.add_parser(
        "replay",
        help="send a capture's bodies to another receiver, exactly as captured",
    )
    replay_parser.add_argument(
        "run", help="one run directory: captures/<project>/<run-id>"
    )
    replay_parser.add_argument(
        "--to",
        required=True,
        help="where to send them: http://host[:port] (SPEC.md section 6)",
    )
    # One flag, two values, and a default: `--raw` is the exporter's own bytes
    # and `--json` the Collector's re-encoding of them (`SPEC.md` §2.4, §6.1).
    side = replay_parser.add_mutually_exclusive_group()
    side.add_argument(
        "--raw",
        dest="source",
        action="store_const",
        const=replay.RAW,
        default=replay.RAW,
        help=f"send {replay.RAW}/: the bytes the exporter sent (default)",
    )
    side.add_argument(
        "--json",
        dest="source",
        action="store_const",
        const=replay.JSON,
        help=f"send {replay.JSON}/: the Collector's JSON re-encoding",
    )
    replay_parser.add_argument(
        "--timing",
        action="store_true",
        help=(
            "sleep the recorded inter-arrival gaps, so the receiver sees the "
            "export pattern the exporter had (SPEC.md section 6.3)"
        ),
    )
    replay_parser.add_argument(
        "--timeout",
        type=float,
        default=forward.DEFAULT_TIMEOUT,
        help=f"seconds per send (default: {forward.DEFAULT_TIMEOUT})",
    )

    audit_parser = subcommands.add_parser(
        "audit",
        help=(
            "run a capture through spanweave-live serve, spanweave and "
            "agentgolden, and write down what happened (needs the audit extra)"
        ),
    )
    audit_parser.add_argument(
        "run", help="one run directory: captures/<project>/<run-id>"
    )
    audit_parser.add_argument(
        "--out",
        default="audit",
        help="where <project>-<run-id>.md is written (default: audit)",
    )

    verify_parser = subcommands.add_parser(
        "verify",
        help="re-hash every capture against its manifest",
    )
    # `default=None` rather than `captures`: `main` has to tell a path the
    # operator typed from the default, because the two mean different things
    # when nothing is there (`verify`, `SPEC.md` §5.6).
    verify_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            f"a capture root, or one run directory, to re-hash "
            f"(default: {CAPTURES}/). A path that is not a capture is a "
            f"refusal, not a pass"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        if args.path is None:
            return verify(CAPTURES)
        return verify(Path(args.path), named=True)
    if args.command == "sink":
        return run_sink(args.host, args.port, Path(args.out))
    if args.command == "capture":
        return run_capture(args)
    if args.command == "replay":
        return run_replay(args)
    if args.command == "audit":
        return run_audit(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
