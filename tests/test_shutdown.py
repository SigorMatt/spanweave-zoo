"""Ctrl-C stops the capture and nothing else (`SPEC.md` §4.6, A3e).

A terminal does not send Ctrl-C to a process. It sends `SIGINT` to the whole
**foreground process group** -- and until A3e the Collector child was in that
group, so it heard the keystroke itself, shut down on its own, and `zoo
capture` then saw a Collector that had exited and wrote it down as a failure.
A capture is immutable, so a capture ended the way the README says to end it
was failed for good (run-2 review, Z-1).

Every test that matters here therefore signals the **process group**, as a
terminal does, of a real `zoo capture` process: the in-process tests of A2 and
A3a raised the signal inside the test's own interpreter or set an exit code on
a fake, and neither could see what the terminal does.

The stand-in Collector below logs which signal it was stopped by, the way the
stock Collector does (`Received signal from OS {"signal": "interrupt"}`). That
line is what makes the group test deterministic rather than a race: whether
`zoo capture` *noticed* the child's exit before it stopped it was a race the
review lost on a loaded machine and won on an idle one, but which signal the
child received is not -- and the capture's own `collector.log` says which.
"""

from __future__ import annotations

import contextlib
import http.client
import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from spanweave_zoo import capture, cli, collector, manifest
from tests import otlp

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_DIR = REPO / "collector"
HOST = "127.0.0.1"
PROTOBUF = otlp.export_trace_service_request()
READY_LINE = "zoo capture: the raw bytes are the record. Ctrl-C to stop."
COLLECTOR_READY = "Everything is ready. Begin running and processing data."
# How long a test waits on another process before calling it hung. Generous,
# because CI machines are slow; a pass never waits this long.
PATIENCE = 60.0

# A stand-in for the Collector's *lifecycle* (`SPEC.md` §4.9): it binds the
# receiver port it is given, answers every forward 200, logs the stock ready
# line, and on `SIGINT` or `SIGTERM` logs which one it got and exits 0 -- as
# the stock Collector does. `stubborn` ignores `SIGTERM`, which is the child
# `zoo capture` has to `SIGKILL`. It writes its pid beside itself so a test can
# kill it by hand.
STUB_BODY = """
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if "--version" in sys.argv:
    print("otelcol-contrib version " + VERSION)
    raise SystemExit(0)


class Answer(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


NAMES = {signal.SIGINT: "interrupt", signal.SIGTERM: "terminated"}


def stop(number, frame):
    sys.stderr.write(
        'info\\tReceived signal from OS\\t{"signal": "' + NAMES[number] + '"}\\n'
    )
    sys.stderr.flush()
    os._exit(0)


signal.signal(signal.SIGINT, stop)
signal.signal(
    signal.SIGTERM, signal.SIG_IGN if BEHAVIOUR == "stubborn" else stop
)
host, _, port = os.environ["ZOO_COLLECTOR_OTLP_HTTP"].rpartition(":")
server = ThreadingHTTPServer((host, int(port)), Answer)
threading.Thread(target=server.serve_forever, daemon=True).start()
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pid"), "w") as f:
    f.write(str(os.getpid()))
sys.stderr.write("info\\tservice.go:256\\t" + READY + "\\n")
sys.stderr.flush()
while True:
    time.sleep(1)
"""


def pinned_version() -> str:
    return (COLLECTOR_DIR / "VERSION").read_text(encoding="utf-8").strip()


def stand_in(tmp_path: Path, behaviour: str = "obliging") -> Path:
    """A `collector/` directory whose binary is `STUB_BODY`."""
    directory = tmp_path / f"stand-in-{behaviour}"
    directory.mkdir(parents=True)
    (directory / collector.VERSION_NAME).write_text(
        pinned_version() + "\n", encoding="utf-8"
    )
    (directory / collector.CONFIG_NAME).write_text("receivers:\n", encoding="utf-8")
    script = directory / collector.BINARY_NAME
    script.write_text(
        f"#!{sys.executable}\n"
        f"VERSION = {pinned_version()!r}\n"
        f"BEHAVIOUR = {behaviour!r}\n"
        f"READY = {COLLECTOR_READY!r}\n" + STUB_BODY,
        encoding="utf-8",
    )
    script.chmod(0o755)
    return directory


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def post(port: int, body: bytes) -> int:
    connection = http.client.HTTPConnection(HOST, port, timeout=30)
    try:
        connection.request(
            "POST",
            "/v1/traces",
            body=body,
            headers={"Content-Type": "application/x-protobuf"},
        )
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def project_manifest(tmp_path: Path) -> Path:
    """A project manifest dated long after any capture's own start."""
    path = tmp_path / "pet" / "MANIFEST.json"
    path.parent.mkdir(parents=True)
    manifest.write_json(
        path, {"mode": "recorded", "started_at": "2999-01-01T00:00:00+00:00"}
    )
    return path


class ZooCapture:
    """`zoo capture` as an operator runs it: its own process, its own group.

    `start_new_session` makes the zoo the leader of a fresh process group, so
    `os.killpg` reaches exactly what a terminal's Ctrl-C would -- the zoo and
    everything it left in its group -- and nothing of the test's own.
    """

    def __init__(self, tmp_path: Path, collector_dir: Path) -> None:
        self.run = tmp_path / "captures" / "z4" / "run-1"
        self.port = free_port()
        command = [
            sys.executable,
            "-m",
            "spanweave_zoo.cli",
            "capture",
            "--project",
            "z4",
            "--run-id",
            "run-1",
            "--kind",
            "recorded",
            "--project-manifest",
            str(project_manifest(tmp_path)),
            "--captures",
            str(tmp_path / "captures"),
            "--collector-dir",
            str(collector_dir),
            "--port",
            str(self.port),
            "--json-port",
            str(free_port()),
            "--collector-port",
            str(free_port()),
            "--collector-grpc-port",
            str(free_port()),
        ]
        self.process = subprocess.Popen(
            command,
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.printed: list[str] = []
        self._lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        for raw in self.process.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            self.printed.append(line)
            self._lines.put(line)

    def wait_for(self, wanted: str) -> None:
        """Block until a printed line contains `wanted`, or fail naming it."""
        deadline = time.monotonic() + PATIENCE
        while time.monotonic() < deadline:
            try:
                line = self._lines.get(timeout=0.5)
            except queue.Empty:
                if self.process.poll() is not None:
                    break
                continue
            if wanted in line:
                return
        self.kill()
        pytest.fail(f"never printed {wanted!r}; printed:\n" + "\n".join(self.printed))

    def ctrl_c(self) -> int:
        """`SIGINT` to the process group, as a terminal sends it."""
        os.killpg(self.process.pid, signal.SIGINT)
        try:
            return self.process.wait(timeout=PATIENCE)
        except subprocess.TimeoutExpired:
            self.kill()
            pytest.fail("zoo capture did not end on Ctrl-C")

    def kill(self) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait(timeout=PATIENCE)


def listed(run: Path) -> set[str]:
    return {entry["file"] for entry in manifest.read(run)[manifest.FILES]}


def test_ctrl_c_to_the_process_group_stops_the_capture_and_nothing_else(tmp_path):
    # The A3e row's first test. One export through the tee, then Ctrl-C as a
    # terminal sends it. The capture is clean: exit 0, no `problems`, `verify`
    # green. And the Collector was stopped by `zoo capture` -- `SIGTERM` -- and
    # never heard the keystroke, which is what its own log says.
    zoo = ZooCapture(tmp_path, stand_in(tmp_path))
    try:
        zoo.wait_for(READY_LINE)
        assert post(zoo.port, PROTOBUF) == 200
        zoo.wait_for("raw/0001.body")
    except BaseException:
        zoo.kill()
        raise
    status = zoo.ctrl_c()
    printed = "\n".join(zoo.printed)

    assert status == 0, printed
    document = manifest.read(zoo.run)
    assert manifest.PROBLEMS not in document, document.get(manifest.PROBLEMS)
    assert cli.verify(zoo.run) == 0

    log = (zoo.run / collector.LOG_NAME).read_text(encoding="utf-8")
    assert '"signal": "terminated"' in log, log
    assert '"signal": "interrupt"' not in log, (
        "the Collector heard the terminal's Ctrl-C: it is in zoo capture's "
        "process group"
    )
    assert collector.LOG_NAME in listed(zoo.run)
    # The operator's terminal has the zoo's lines and not the Collector's.
    assert COLLECTOR_READY not in printed
    assert "Received signal" not in printed


def test_the_collector_killed_by_hand_mid_capture_is_a_problem(tmp_path):
    # The other half of the rule: an exit `zoo capture` did not ask for is a
    # problem, written when it is noticed, and the exit status says so -- even
    # though the run is then ended cleanly with Ctrl-C.
    collector_dir = stand_in(tmp_path)
    zoo = ZooCapture(tmp_path, collector_dir)
    try:
        zoo.wait_for(READY_LINE)
        pid = int((collector_dir / "pid").read_text(encoding="utf-8"))
        os.kill(pid, signal.SIGKILL)
        zoo.wait_for("collector exited: -9")
    except BaseException:
        zoo.kill()
        raise
    status = zoo.ctrl_c()

    assert status == 1, "\n".join(zoo.printed)
    document = manifest.read(zoo.run)
    assert document[manifest.PROBLEMS] == ["collector exited: -9"]
    assert collector.LOG_NAME in listed(zoo.run)
    assert cli.verify(zoo.run) == 1


# --- the shutdown sequence, in process --------------------------------------


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


def in_process(tmp_path: Path, collector_dir: Path, *, stop_wait: float, log):
    pinned = collector.pin(collector_dir)
    port = free_port()
    launcher = collector.Binary(
        pinned,
        host=HOST,
        http_port=port,
        grpc_port=0,
        sleep=time.sleep,
        pause=0.05,
        stop_wait=stop_wait,
    )
    return capture.Capture(
        tmp_path / "captures" / "z4" / "run-1",
        now=Clock(),
        launcher=launcher,
        forward=lambda method, path, headers, body: 200,
        pin=pinned,
        kind="recorded",
        project_manifest=project_manifest(tmp_path),
        raw_port=0,
        json_port=0,
        log=log,
    )


def test_a_collector_that_ignores_sigterm_is_killed_and_that_is_not_a_problem(
    tmp_path,
):
    # Degenerate: the child does not go when asked. The wait is bounded, the
    # SIGKILL follows, the operator is told -- and it is still an exit inside
    # the shutdown `zoo capture` ran, not a Collector that died on its own.
    printed: list[str] = []
    started = in_process(
        tmp_path, stand_in(tmp_path, "stubborn"), stop_wait=0.5, log=printed.append
    )
    started.start()
    child = started.collector
    assert child is not None
    started.stop()

    assert child.returncode() == -signal.SIGKILL
    assert started.problems == []
    assert manifest.PROBLEMS not in manifest.read(started.run)
    assert any("SIGKILL" in line for line in printed), printed
    assert cli.verify(started.run) == 0


def test_the_collectors_log_is_the_run_directorys_and_not_the_terminals(tmp_path):
    # Its lines from before the run directory existed -- the ready line -- and
    # after, byte for byte, in `collector.log`; none of them in what the
    # capture prints.
    printed: list[str] = []
    started = in_process(
        tmp_path, stand_in(tmp_path), stop_wait=10.0, log=printed.append
    )
    started.start()
    started.stop()

    log = (started.run / collector.LOG_NAME).read_bytes()
    assert log.startswith(b"info\tservice.go:256\t" + COLLECTOR_READY.encode())
    assert b'{"signal": "terminated"}\n' in log
    assert not any(COLLECTOR_READY in line for line in printed), printed
    assert collector.LOG_NAME in listed(started.run)


class Started:
    def __init__(self) -> None:
        self.stopped = 0

    def stop(self) -> bool:
        self.stopped += 1
        return False

    def returncode(self) -> int | None:
        return None

    def keep_log(self, path: Path) -> None:
        pass


class Launcher:
    def __init__(self) -> None:
        self.running = Started()

    def version(self) -> str:
        return pinned_version()

    def start(self, json_endpoint: str) -> Started:
        return self.running


class Held:
    """A forward the Collector has not answered yet, until a test says so."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def __call__(self, method, path, headers, body):
        self.entered.set()
        self.release.wait(timeout=PATIENCE)
        return 200


def held_capture(tmp_path: Path, forward: Held, **kwargs):
    launcher = Launcher()
    started = capture.Capture(
        tmp_path / "captures" / "z4" / "run-1",
        now=Clock(),
        launcher=launcher,
        forward=forward,
        pin=collector.pin(COLLECTOR_DIR),
        kind="recorded",
        project_manifest=project_manifest(tmp_path),
        raw_port=0,
        json_port=0,
        log=lambda line: None,
        **kwargs,
    )
    started.start()
    return started, launcher


def test_a_forward_under_way_is_answered_before_the_collector_is_stopped(tmp_path):
    # "Let the Collector flush": a body already handed to the Collector is
    # answered before the Collector is told to go, so its final flush can
    # carry it and the forward does not fail on a Collector shutting down.
    forward = Held()
    started, launcher = held_capture(tmp_path, forward)
    assert started.raw is not None
    poster = threading.Thread(target=post, args=(started.raw.port, PROTOBUF))
    poster.start()
    assert forward.entered.wait(timeout=PATIENCE)

    stopper = threading.Thread(target=started.stop)
    stopper.start()
    stopper.join(timeout=0.5)
    assert launcher.running.stopped == 0, (
        "the Collector was stopped with a forward still waiting on it"
    )
    forward.release.set()
    stopper.join(timeout=PATIENCE)
    poster.join(timeout=PATIENCE)

    assert launcher.running.stopped == 1
    assert manifest.read(started.run)[manifest.FORWARDS] == [
        {"file": "raw/0001.body", "status": 200}
    ]


def test_the_wait_for_a_forward_under_way_is_bounded(tmp_path):
    # Degenerate: a Collector that never answers must not become a capture
    # that never stops. The wait gives up, and the Collector is stopped anyway.
    forward = Held()
    started, launcher = held_capture(tmp_path, forward, flush_wait=0.2)
    assert started.raw is not None
    poster = threading.Thread(target=post, args=(started.raw.port, PROTOBUF))
    poster.start()
    assert forward.entered.wait(timeout=PATIENCE)
    try:
        started.stop()
        assert launcher.running.stopped == 1
    finally:
        forward.release.set()
        poster.join(timeout=PATIENCE)


def test_the_summary_counts_bodies_by_where_they_are(tmp_path):
    # One export is one body. Its re-encoding is a body too, the Collector's,
    # and is counted where it is rather than added to the exporter's: the run-2
    # rehearsal's one export was summarised as "2 body/bodies".
    run = tmp_path / "captures" / "z4" / "run-1"
    run.mkdir(parents=True)
    for name in ("raw/0001.body", "json/0001.json", "rejected/0001.body"):
        manifest.journal_body(
            run, manifest.BodyEntry(file=name, sha256=manifest.digest(b""), bytes=0)
        )
    manifest.label(run, kind="recorded", collector_version="0", started_at="x")
    manifest.finish(run, ended_at="y")
    assert manifest.tally(run) == "1 body/bodies in raw/, 1 in json/, 1 in rejected/"
