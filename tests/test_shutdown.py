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
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from spanweave_zoo import capture, cli, collector, manifest
from tests import otlp, ports

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_DIR = REPO / "collector"
HOST = "127.0.0.1"
PROTOBUF = otlp.export_trace_service_request()
READY_LINE = "zoo capture: the raw bytes are the record. Ctrl-C to stop."
COLLECTOR_READY = "Everything is ready. Begin running and processing data."
# How long a test waits on another process before calling it hung. Generous,
# because CI machines are slow; a pass never waits this long.
PATIENCE = 60.0
# How long the `slow` stand-in takes to say it is ready after binding its port:
# long enough that a signal sent once it has bound lands in the readiness wait,
# short enough that a zoo which waited it out would still see it ready -- the
# readiness budget is 150 looks a tenth of a second apart (`collector.py`).
SLOW_READY = 5.0

# A stand-in for the Collector's *lifecycle* (`SPEC.md` §4.9): it binds the
# receiver port it is given, answers every forward 200, logs the stock ready
# line, and on `SIGINT` or `SIGTERM` logs which one it got and exits 0 -- as
# the stock Collector does. `stubborn` ignores `SIGTERM`, which is the child
# `zoo capture` has to `SIGKILL`; `slow` binds its port and then takes `SLOW`
# seconds -- well inside the readiness budget -- to log its ready line, which
# is the window B2 signals into. It writes its pid beside itself, once its
# port is bound, so a test can kill it by hand or see whether it is alive.
STUB_BODY = """
import os
import signal
import socketserver
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


class Server(ThreadingHTTPServer):
    # Bind and resolve no name, as the zoo's own sink does (SPEC.md 3.7):
    # the stock server_bind's getfqdn is a reverse lookup that took longer
    # than the whole readiness wait on a macOS runner.
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


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
server = Server((host, int(port)), Answer)
threading.Thread(target=server.serve_forever, daemon=True).start()
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "pid.tmp"), "w") as f:
    f.write(str(os.getpid()))
os.replace(os.path.join(here, "pid.tmp"), os.path.join(here, "pid"))
if BEHAVIOUR == "slow":
    time.sleep(SLOW)
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
        f"READY = {COLLECTOR_READY!r}\n"
        f"SLOW = {SLOW_READY!r}\n" + STUB_BODY,
        encoding="utf-8",
    )
    script.chmod(0o755)
    return directory


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

    Constructing one **starts it and waits until it is up** (B1): the sinks
    are given `--port 0 --json-port 0` and the ports they got are read from
    the two lines after the readiness line (`SPEC.md` §4.2), and the
    Collector's two ports -- which it must be told before it exists -- are
    picked, the whole start retried, bounded, when the refusal names an
    address in use (`tests/ports.py`). `tried` is every pair picked.

    `becoming_ready=True` (B2) returns earlier: as soon as the stand-in
    Collector has bound its port and written its pid -- the `slow` one then
    takes `SLOW_READY` seconds to say it is ready, so `zoo capture` is in its
    readiness wait -- with the pid in `collector_pid`. A port taken under the
    pick is retried the same way, because the stand-in that could not bind
    exits before it writes a pid, and `zoo capture` refuses naming the port.
    """

    def __init__(
        self,
        tmp_path: Path,
        collector_dir: Path,
        *,
        pick: Callable[[], int] = ports.free_port,
        log: Callable[[str], object] = print,
        becoming_ready: bool = False,
    ) -> None:
        self.run = tmp_path / "captures" / "z4" / "run-1"
        self._pid = collector_dir / "pid"
        self._becoming_ready = becoming_ready
        self._base = [
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
            "0",
            "--json-port",
            "0",
        ]
        self.tried: list[tuple[int, ...]] = []
        ports.with_picked_ports(self._start, count=2, pick=pick, log=log)

    def _start(self, picked: tuple[int, ...]) -> None:
        self.tried.append(picked)
        collector_port, grpc_port = picked
        self.command = [
            *self._base,
            "--collector-port",
            str(collector_port),
            "--collector-grpc-port",
            str(grpc_port),
        ]
        if self._becoming_ready:
            self._pid.unlink(missing_ok=True)
        self.process = subprocess.Popen(
            self.command,
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.printed: list[str] = []
        self._lines: queue.Queue[str] = queue.Queue()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()
        if self._becoming_ready:
            if not self._pid_written():
                self._refused()
            self.collector_pid = int(self._pid.read_text(encoding="utf-8"))
            return
        if self._next(READY_LINE) is None:
            self._refused()
        raw = self._next("zoo capture: recording POST ")
        json_sink = self._next("zoo capture: collector ")
        if raw is None or json_sink is None:
            self.kill()
            pytest.fail("no ports after the readiness line:\n" + self._output())
        self.port = bound_port(r" on http://[^ ]+:(\d+) -> ", raw)
        self.json_port = bound_port(r", via http://[^ ]+:(\d+)$", json_sink)

    def _refused(self) -> None:
        """Not up: a port taken under the pick is retried, anything else fails."""
        try:
            self.process.wait(timeout=PATIENCE)
        except subprocess.TimeoutExpired:
            self.kill()
            pytest.fail("never printed the readiness line:\n" + self._output())
        self._reader.join(timeout=PATIENCE)
        output = self._output()
        if self.process.returncode == 2 and ports.in_use(output):
            raise ports.PortTaken(output)
        pytest.fail(
            f"zoo capture exited {self.process.returncode} before it was up:\n" + output
        )

    def _pid_written(self) -> bool:
        """Whether the stand-in wrote its pid before `zoo capture` exited."""
        deadline = time.monotonic() + PATIENCE
        while time.monotonic() < deadline:
            if self._pid.exists():
                return True
            if self.process.poll() is not None:
                return self._pid.exists()
            time.sleep(0.02)
        return False

    def _output(self) -> str:
        return "\n".join(self.printed)

    def _read(self) -> None:
        assert self.process.stdout is not None
        for raw in self.process.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            self.printed.append(line)
            self._lines.put(line)

    def _next(self, wanted: str) -> str | None:
        """The next printed line containing `wanted`; `None` if it never comes."""
        deadline = time.monotonic() + PATIENCE
        while time.monotonic() < deadline:
            try:
                line = self._lines.get(timeout=0.5)
            except queue.Empty:
                if self.process.poll() is not None:
                    return None
                continue
            if wanted in line:
                return line
        return None

    def wait_for(self, wanted: str) -> None:
        """Block until a printed line contains `wanted`, or fail naming it."""
        if self._next(wanted) is None:
            self.kill()
            pytest.fail(f"never printed {wanted!r}; printed:\n" + self._output())

    def ctrl_c(self) -> int:
        """`SIGINT` to the process group, as a terminal sends it."""
        return self.signal_group(signal.SIGINT)

    def signal_group(self, number: int) -> int:
        """`number` to the process group, and the exit status that follows."""
        os.killpg(self.process.pid, number)
        try:
            return self.process.wait(timeout=PATIENCE)
        except subprocess.TimeoutExpired:
            self.kill()
            pytest.fail(f"zoo capture did not end on {signal.Signals(number).name}")

    def signal_process(self, number: int) -> int:
        """`number` to `zoo capture` alone, as a supervisor sends it, and the
        exit status that follows."""
        self.process.send_signal(number)
        try:
            status = self.process.wait(timeout=PATIENCE)
        except subprocess.TimeoutExpired:
            self.kill()
            pytest.fail(f"zoo capture did not end on {signal.Signals(number).name}")
        self._reader.join(timeout=PATIENCE)
        return status

    def kill(self) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait(timeout=PATIENCE)


def bound_port(pattern: str, line: str) -> int:
    """The port a §4.2 line names, which is the one the sink actually got."""
    found = re.search(pattern, line)
    assert found is not None, f"no port in {line!r}"
    return int(found.group(1))


# --- B1: the harness does not lose a port race -----------------------------


class Picks:
    """A `pick` that hands out `first` before it picks for real."""

    def __init__(self, *first: int) -> None:
        self.first = list(first)

    def __call__(self) -> int:
        return self.first.pop(0) if self.first else ports.free_port()


def held_port() -> socket.socket:
    """A listener on a port nobody else can bind until it is closed."""
    held = socket.socket()
    held.bind((HOST, 0))
    held.listen(8)
    return held


def test_a_collector_port_taken_before_the_bind_is_picked_again(tmp_path):
    # The close review's race, made to happen: the first Collector port the
    # harness picks is already held, so the stand-in's bind fails with the
    # address-in-use line and `zoo capture` refuses (SPEC.md section 4.6). The
    # harness starts the whole run again on new picks; the second start
    # reaches readiness, and both ports tried are on record.
    held = held_port()
    taken = int(held.getsockname()[1])
    try:
        zoo = ZooCapture(tmp_path, stand_in(tmp_path), pick=Picks(taken))
    finally:
        held.close()
    try:
        assert len(zoo.tried) == 2, zoo.tried
        assert zoo.tried[0][0] == taken
        assert zoo.tried[1][0] != taken
        assert post(zoo.port, PROTOBUF) == 200
        zoo.wait_for("raw/0001.body")
    except BaseException:
        zoo.kill()
        raise
    assert zoo.ctrl_c() == 0, "\n".join(zoo.printed)


def test_sinks_on_port_0_print_two_ports_a_test_can_post_to(tmp_path):
    # The harness picks no sink port: `--port 0 --json-port 0`, and the ports
    # the sinks got are read back from the two lines after the readiness line
    # (SPEC.md sections 4.2, 4.6). Each is POSTed to and records a body.
    zoo = ZooCapture(tmp_path, stand_in(tmp_path))
    try:
        assert zoo.command[zoo.command.index("--port") + 1] == "0"
        assert zoo.command[zoo.command.index("--json-port") + 1] == "0"
        assert 0 not in (zoo.port, zoo.json_port)
        assert zoo.port != zoo.json_port
        assert post(zoo.port, PROTOBUF) == 200
        zoo.wait_for("raw/0001.body")
        assert post(zoo.json_port, b"{}") == 200
        zoo.wait_for("json/0001.json")
    except BaseException:
        zoo.kill()
        raise
    assert zoo.ctrl_c() == 0, "\n".join(zoo.printed)
    assert (zoo.run / "raw" / "0001.body").read_bytes() == PROTOBUF
    assert (zoo.run / "json" / "0001.json").read_bytes() == b"{}"


def test_a_refusal_that_names_no_address_in_use_is_not_retried(tmp_path):
    # Degenerate: a refusal for any other reason -- here, no binary -- is the
    # test's to see, once. Retrying it would only hide it five times.
    collector_dir = stand_in(tmp_path)
    (collector_dir / collector.BINARY_NAME).unlink()
    logged: list[str] = []
    with pytest.raises(pytest.fail.Exception) as failed:
        ZooCapture(tmp_path, collector_dir, log=logged.append)
    assert "make collector" in str(failed.value)
    assert len([line for line in logged if "harness: start" in line]) == 1


def test_the_retry_is_bounded_and_names_every_port_tried():
    # Degenerate: an address that is in use on every start. Five starts, then
    # a failure naming each pick -- as honest as the refusal after one.
    picks = iter(range(40001, 40100))
    logged: list[str] = []

    def refused(picked: tuple[int, ...]) -> None:
        raise ports.PortTaken(f"bind: address already in use: {picked}")

    with pytest.raises(pytest.fail.Exception) as failed:
        ports.with_picked_ports(
            refused, count=2, pick=lambda: next(picks), log=logged.append
        )
    message = str(failed.value)
    assert f"{ports.ATTEMPTS} starts" in message
    for port in range(40001, 40001 + 2 * ports.ATTEMPTS):
        assert str(port) in message
    assert str(40001 + 2 * ports.ATTEMPTS) not in message
    assert len([line for line in logged if "refused" in line]) == ports.ATTEMPTS


def listed(run: Path) -> set[str]:
    return {entry["file"] for entry in manifest.read(run)[manifest.FILES]}


def test_ctrl_c_to_the_process_group_stops_the_capture_and_nothing_else(tmp_path):
    # The A3e row's first test. One export through the tee, then Ctrl-C as a
    # terminal sends it. The capture is clean: exit 0, no `problems`, `verify`
    # green. And the Collector was stopped by `zoo capture` -- `SIGTERM` -- and
    # never heard the keystroke, which is what its own log says.
    zoo = ZooCapture(tmp_path, stand_in(tmp_path))
    try:
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


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_hang_up_to_the_process_group_stops_the_capture_as_ctrl_c_does(tmp_path):
    # A3g; run-2b review N-2. Closing the terminal, or dropping the ssh session
    # it is in, sends `SIGHUP` to the foreground process group. Since A3e the
    # Collector is in a session of its own and does not get it -- so before
    # A3g the hang-up killed `zoo capture` by its default action, the manifest
    # was never completed and the Collector was left running, holding its
    # port. It now ends the run as Ctrl-C does: exit 0, no `problems`, verify
    # green, and the Collector stopped by the zoo.
    collector_dir = stand_in(tmp_path)
    zoo = ZooCapture(tmp_path, collector_dir)
    try:
        pid = int((collector_dir / "pid").read_text(encoding="utf-8"))
        assert post(zoo.port, PROTOBUF) == 200
        zoo.wait_for("raw/0001.body")
    except BaseException:
        zoo.kill()
        raise
    try:
        status = zoo.signal_group(signal.SIGHUP)
        printed = "\n".join(zoo.printed)
        assert status == 0, printed
        assert not alive(pid), "the Collector outlived the hang-up"
        document = manifest.read(zoo.run)
        assert manifest.PROBLEMS not in document, document.get(manifest.PROBLEMS)
        assert cli.verify(zoo.run) == 0
        log = (zoo.run / collector.LOG_NAME).read_text(encoding="utf-8")
        assert '"signal": "terminated"' in log, log
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def test_the_collector_killed_by_hand_mid_capture_is_a_problem(tmp_path):
    # The other half of the rule: an exit `zoo capture` did not ask for is a
    # problem, written when it is noticed, and the exit status says so -- even
    # though the run is then ended cleanly with Ctrl-C.
    collector_dir = stand_in(tmp_path)
    zoo = ZooCapture(tmp_path, collector_dir)
    try:
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


# --- B2: signals cover the whole life of a capture --------------------------


@pytest.mark.parametrize("number", cli.STOP_SIGNALS, ids=lambda n: n.name)
def test_a_stop_signal_while_the_collector_becomes_ready_leaves_nothing_behind(
    tmp_path, number
):
    # B2 (a), Qodo Q1. `zoo capture` installed its stop handlers only once
    # `start()` had returned, and the readiness wait can last most of a
    # minute: a supervisor's SIGTERM or a terminal's SIGHUP in that window
    # killed it by the default action, and the Collector -- in a session of
    # its own (A3e) -- outlived it, holding its port. Signalled while the
    # stand-in is bound and not yet ready, the zoo now stops the Collector,
    # writes nothing, and exits as a refusal does (SPEC.md section 4.6).
    collector_dir = stand_in(tmp_path, "slow")
    zoo = ZooCapture(tmp_path, collector_dir, becoming_ready=True)
    pid = zoo.collector_pid
    try:
        status = zoo.signal_process(number)
        printed = "\n".join(zoo.printed)
        assert not alive(pid), f"the Collector outlived {number.name}:\n{printed}"
        assert not zoo.run.exists(), sorted(zoo.run.rglob("*"))
        assert status == 2, printed
        assert "zoo capture: refusing to start: " in printed
        assert number.name in printed
        assert READY_LINE not in printed
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)
        zoo.kill()


# --- the shutdown sequence, in process --------------------------------------


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


def in_process(tmp_path: Path, collector_dir: Path, *, stop_wait: float, log):
    """A started in-process capture, its Collector on a picked port (B1)."""
    pinned = collector.pin(collector_dir)
    copied = project_manifest(tmp_path)

    def build(port: int) -> capture.Capture:
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
            forward=lambda head, body: 200,
            pin=pinned,
            kind="recorded",
            project_manifest=copied,
            raw_port=0,
            json_port=0,
            log=log,
        )

    return ports.started_capture(build)


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

    def __call__(self, head, body):
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


class Broken(Exception):
    """What a failing step of `start()`'s tail raises, in the tests below."""


def test_a_start_that_fails_after_the_collector_is_up_stops_it(tmp_path, monkeypatch):
    # B2 (b), Qodo Q8. Everything in `start()` after the Collector was up and
    # the run directory made -- the clock, the label, setting the sinks
    # serving, the readiness line -- was outside the `try` that stops the
    # Collector on the way out. A label that cannot be written left the child
    # running and both sinks bound (SPEC.md section 4.6).
    def unwritable(*args, **kwargs):
        raise Broken("the manifest could not be labelled")

    monkeypatch.setattr(capture.manifest, "label", unwritable)
    launcher = Launcher()
    started = capture.Capture(
        tmp_path / "captures" / "z4" / "run-1",
        now=Clock(),
        launcher=launcher,
        forward=lambda head, body: 200,
        pin=collector.pin(COLLECTOR_DIR),
        kind="recorded",
        project_manifest=project_manifest(tmp_path),
        raw_port=0,
        json_port=0,
        log=lambda line: None,
    )
    with pytest.raises(Broken):
        started.start()
    assert launcher.running.stopped == 1, "the Collector was left running"
    assert started.raw is not None and started.json is not None
    assert started.raw.server.socket.fileno() == -1, "the raw sink is still bound"
    assert started.json.server.socket.fileno() == -1, "the json sink is still bound"
    # Nothing was labelled, so there is no capture to close (SPEC.md 5.5).
    assert not (started.run / manifest.MANIFEST_NAME).exists()


def test_a_readiness_line_that_cannot_be_printed_still_ends_in_a_sealed_capture(
    tmp_path,
):
    # Degenerate, B2 (b): the very last step of the tail fails -- the label is
    # on disk and the sinks are serving -- and the run unwinds through the
    # whole stop path: the Collector stopped, and the manifest closed rather
    # than left without `ended_at`.
    def log(line: str) -> None:
        if line == READY_LINE:
            raise Broken("the readiness line could not be printed")

    launcher = Launcher()
    started = capture.Capture(
        tmp_path / "captures" / "z4" / "run-1",
        now=Clock(),
        launcher=launcher,
        forward=lambda head, body: 200,
        pin=collector.pin(COLLECTOR_DIR),
        kind="recorded",
        project_manifest=project_manifest(tmp_path),
        raw_port=0,
        json_port=0,
        log=log,
    )
    with pytest.raises(Broken):
        started.start()
    assert launcher.running.stopped == 1, "the Collector was left running"
    assert manifest.ENDED_AT in manifest.read(started.run)
    assert cli.verify(started.run) == 0


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


# --- every line `zoo capture` prints is one SPEC.md §4.2 lists --------------


def spec_terminal_lines() -> list[str]:
    """The templates in SPEC.md §4.2's one `text` block, in order."""
    text = (REPO / "SPEC.md").read_text(encoding="utf-8")
    section = text[text.index("### 4.2 ") : text.index("### 4.3 ")]
    found = re.findall(r"^```text\n(.*?)^```$", section, re.MULTILINE | re.DOTALL)
    assert len(found) == 1, "SPEC.md section 4.2 holds no single `text` block"
    return [line for line in found[0].splitlines() if line]


def template(line: str) -> re.Pattern[str]:
    """A §4.2 line as a pattern: each `<...>` stands for any text, or none."""
    parts = re.split(r"<[^<>]+>", line)
    return re.compile(".*".join(re.escape(part) for part in parts))


class Exiting(Started):
    """A Collector that exited on its own, or one that needed `SIGKILL`."""

    def __init__(self, *, exited: int | None = None, killed: bool = False) -> None:
        super().__init__()
        self.exited = exited
        self.killed = killed

    def returncode(self) -> int | None:
        return self.exited

    def stop(self) -> bool:
        super().stop()
        return self.killed


def printed_in_process(tmp_path: Path, name: str, forward, running: Started, **kwargs):
    """What one in-process capture printed, start to summary."""
    lines: list[str] = []
    launcher = Launcher()
    launcher.running = running
    started = capture.Capture(
        tmp_path / name / "captures" / "z4" / "run-1",
        now=Clock(),
        launcher=launcher,
        forward=forward,
        pin=collector.pin(COLLECTOR_DIR),
        kind="recorded",
        project_manifest=project_manifest(tmp_path / name),
        raw_port=0,
        json_port=0,
        log=lines.append,
        **kwargs,
    )
    started.start()
    return started, lines


def test_every_line_zoo_capture_prints_is_one_spec_42_lists(tmp_path, capsys):
    """SPEC.md §4.2's list of terminal lines is the list, both ways.

    A3g; run-2b review N-3. The list omitted the two lines after readiness,
    `zoo capture: stopping` and the forward-failure lines, and nothing tested
    the summary. Every line below is produced by the code -- through a real
    `zoo capture` process for the lines an operator always sees, in process
    for the ones only a failure prints -- and each must be one §4.2 lists;
    and every line §4.2 lists must be one something here printed, so the
    list cannot keep a line the code no longer prints.
    """
    printed: list[str] = []

    # The operator's flow: a real process, an export, Ctrl-C.
    zoo = ZooCapture(tmp_path / "process", stand_in(tmp_path / "process"))
    try:
        assert post(zoo.port, PROTOBUF) == 200
        zoo.wait_for("raw/0001.body")
    except BaseException:
        zoo.kill()
        raise
    assert zoo.ctrl_c() == 0, "\n".join(zoo.printed)
    printed += zoo.printed

    # A forward refused, and one answered with an error status.
    def refused(head, body):
        raise ConnectionRefusedError(111, "Connection refused")

    for name, forward in (("refused", refused), ("503", lambda head, body: 503)):
        started, lines = printed_in_process(tmp_path, name, forward, Started())
        assert started.raw is not None
        post(started.raw.port, PROTOBUF)
        started.stop()
        printed += [*lines, started.summary()]

    # A Collector that exits on its own, and one that has to be killed.
    started, lines = printed_in_process(
        tmp_path, "exited", lambda head, body: 200, Exiting(exited=3)
    )
    started.check_collector()
    started.stop()
    printed += [*lines, started.summary()]
    started, lines = printed_in_process(
        tmp_path, "killed", lambda head, body: 200, Exiting(killed=True)
    )
    started.stop()
    printed += lines

    # A forward still waiting when the flush wait runs out.
    held = Held()
    started, lines = printed_in_process(
        tmp_path, "held", held, Started(), flush_wait=0.05
    )
    assert started.raw is not None
    poster = threading.Thread(target=post, args=(started.raw.port, PROTOBUF))
    poster.start()
    try:
        assert held.entered.wait(timeout=PATIENCE)
        started.stop()
    finally:
        held.release.set()
        poster.join(timeout=PATIENCE)
    printed += lines

    # A refusal, which is the one line that goes to stderr.
    capsys.readouterr()
    assert (
        cli.main(
            [
                "capture",
                "--project",
                "z4",
                "--run-id",
                "refused",
                "--kind",
                "recorded",
                "--project-manifest",
                str(project_manifest(tmp_path / "refusal")),
                "--collector-dir",
                str(tmp_path / "no-collector-here"),
            ]
        )
        == 2
    )
    printed += capsys.readouterr().err.splitlines()

    templates = [template(line) for line in spec_terminal_lines()]
    produced = [line for line in printed if line]
    unlisted = [
        line
        for line in produced
        if not any(pattern.fullmatch(line) for pattern in templates)
    ]
    assert not unlisted, f"printed, and not in SPEC.md section 4.2: {unlisted}"
    unprinted = [
        pattern.pattern
        for pattern in templates
        if not any(pattern.fullmatch(line) for line in produced)
    ]
    assert not unprinted, f"in SPEC.md section 4.2, and never printed: {unprinted}"
    # And the lines an operator always sees, in the order they are printed.
    operator = [line for line in zoo.printed if line]
    assert operator[0] == READY_LINE
    assert operator[-2:-1] == ["zoo capture: stopping"]
    assert operator[-1].startswith("zoo capture: 1 body/bodies in raw/, ")
    assert operator[-1].endswith(", MANIFEST.json written: kind=recorded")
