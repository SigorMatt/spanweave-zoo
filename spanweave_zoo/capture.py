"""`zoo capture`: two sinks, one Collector, one run directory (`SPEC.md` §4.6).

The arrangement, and why it is this way round:

```
   the pet project                 zoo capture
   ---------------                 -----------------------------------------
   OTLP/HTTP exporter  --POST-->   raw sink        :4318   writes raw/NNNN
                                       |  forward (byte-identical)
                                       v
                                   Collector       :4320   re-encodes to JSON
                                       |  otlp_http exporter, encoding: json
                                       v
                                   json sink       :4319   writes json/NNNN
```

The raw sink is first because the record comes first: the exporter's bytes are
written to disk before anything downstream is given a chance to fail
(`SPEC.md` §4.3). The Collector is second because its output is a convenience
kept *beside* the record (`CLAUDE.md` §0.6 rule 4). If the Collector is down,
the capture is still a capture, and the manifest says which bodies never
reached it (§4.4).

Two recorders, one `MANIFEST.json`, one lock per run directory (`SPEC.md`
§4.5). The bodies are journalled as they are recorded and the manifest is
assembled **once**, when the run ends (`SPEC.md` §5.5) -- which is also when
the project's own `MANIFEST.json` is copied, because the project writes that
file while it runs and the copy worth carrying is the one its run left behind
(`SPEC.md` §5.3). A project manifest that is gone by then, or that predates
this capture, is a `problems` entry and a non-zero exit, never a quiet
substitution.

Everything is brought up before anything is written: both sinks bind
their ports, the Collector is started and waited for, and **only then** is the
run directory created, the manifest labelled, the sinks set serving and the one
readiness line printed (`SPEC.md` §4.6). A refusal for any reason -- a port
held, the Collector exiting, a bad config -- therefore leaves no directory at
all, rather than a capture that was never a capture. Stop order is the reverse
of start order, so that the Collector's last batch has somewhere to go.

Nothing here starts a process, binds a socket, reads a clock or sleeps: it is
handed a launcher, a listener factory, a forward and a `now` (`SPEC.md` §4.8).
That is what lets the tee's mechanics be tested with no Collector at all, and
what makes a recorded timestamp a value a test chose.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from http.server import ThreadingHTTPServer
from pathlib import Path

from spanweave_zoo import collector, manifest, sink

RAW_DIR = "raw"
JSON_DIR = "json"

DEFAULT_RAW_PORT = 4318
DEFAULT_JSON_PORT = 4319
DEFAULT_COLLECTOR_PORT = 4320
DEFAULT_COLLECTOR_GRPC_PORT = 4317

# The one line that says a capture is up (`SPEC.md` §4.6). It is printed once,
# first, and only after the run directory exists -- so a line that an operator
# or a script reads as "recording" is never printed by a run that refused.
# `zoo sink`'s banner (`cli.SINK_BANNER`) says a different thing and says it
# differently.
READY_LINE = "zoo capture: the raw bytes are the record. Ctrl-C to stop."

# How often the waiting caller wakes to notice that it was asked to stop
# (`SPEC.md` §4.6). It is a poll interval and not a clock read: the main thread
# has to execute bytecode now and then or a signal handler never runs, because
# the OS may deliver the signal to any thread and the other threads here are
# blocked in `select`. `socketserver.serve_forever` takes the same parameter
# for the same reason.
STOP_POLL = 0.2

MakeServer = Callable[..., ThreadingHTTPServer]


def _say(line: str) -> None:
    """One progress line, flushed (`SPEC.md` §4.6).

    Flushed on every write, because an operator watching a pet project export
    into a log file should see each body as it lands rather than when the
    capture is stopped -- and because a capture that looks silent is a capture
    an operator is about to kill. `cli.py` passes a printer that also survives
    a stdout nobody is reading any more.
    """
    print(line, flush=True)


class _Listener:
    """One sink: bound at construction, served later, closed on the way out.

    Binding and serving are two steps because readiness and recording are two
    things (`SPEC.md` §4.6). The port is held -- and the kernel is accepting
    connections onto its backlog -- as soon as the server exists, which is what
    "the listener accepts" means and what makes a port already in use a
    refusal before any directory is made. The thread that answers requests
    starts afterwards, once there is a labelled manifest for a body to be
    recorded into.
    """

    def __init__(
        self,
        recorder: sink.Recorder,
        server: ThreadingHTTPServer,
    ) -> None:
        self.recorder = recorder
        self.server = server
        self.port: int = server.server_address[1]
        self._serving = False
        self._thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )

    def serve(self) -> None:
        self._serving = True
        self._thread.start()

    def stop(self) -> None:
        # `shutdown()` waits for `serve_forever` to notice and return, so it
        # must not be called on a listener that never served: it would wait for
        # a loop that never started. A bound-but-unserved listener is exactly
        # what a refusal leaves behind, and closing the socket is all it needs.
        if self._serving:
            self.server.shutdown()
            self._thread.join(timeout=30)
        self.server.server_close()


class Capture:
    """One run: two sinks, one Collector, one manifest.

    Constructed with its seams, started, served, stopped. `zoo capture` is this
    object plus a signal handler; a test is this object plus a launcher that
    starts nothing.
    """

    def __init__(
        self,
        run: Path,
        *,
        now: Callable[[], str],
        launcher: collector.Launcher,
        forward: sink.Forward,
        pin: collector.Pin,
        kind: str,
        project_manifest: Path,
        host: str = "127.0.0.1",
        raw_port: int = DEFAULT_RAW_PORT,
        json_port: int = DEFAULT_JSON_PORT,
        make_server: MakeServer = sink.make_server,
        log: Callable[[str], None] = _say,
        on_record: Callable[[manifest.BodyEntry], None] | None = None,
    ) -> None:
        self.run = run
        self.host = host
        self._now = now
        self._launcher = launcher
        self._forward = forward
        self._pin = pin
        # `kind` and the project's manifest have no defaults on purpose
        # (`SPEC.md` §5): a capture that could be written without declaring
        # what it is would be a capture the audit has to guess about. The
        # project's manifest is held as a **path** and read when the run ends
        # (`SPEC.md` §5.3): the project writes that file while it runs, so the
        # copy a capture should carry is the one that is there at the end.
        self._kind = kind
        self._project_manifest = project_manifest
        self._raw_port = raw_port
        self._json_port = json_port
        self._make_server = make_server
        self._log = log
        # The sink's `after_record` seam (`SPEC.md` §3.6) reaching through
        # `zoo capture`. The integration test uses it to wait for the
        # Collector's JSON to land on an `Event` rather than by polling a
        # directory, which is how a test that waits for another process stays a
        # test and not a race.
        self._on_record = on_record
        self.raw: _Listener | None = None
        self.json: _Listener | None = None
        self.collector: collector.Running | None = None
        # What went wrong during the run that the capture itself cannot fix:
        # today, a Collector child that exited (`SPEC.md` §4.6). Each one is
        # written into `MANIFEST.json` when it is noticed and makes
        # `zoo capture` exit non-zero, because a run whose `json/` stopped
        # being written must not look like one that is complete.
        self.problems: list[str] = []
        self._collector_exited = False
        self._stopping = threading.Event()
        # Whether there is a manifest to close, and whether it was closed.
        # `stop()` runs on the way out of a failed `start()` as well as at the
        # end of a run, and `ended_at` is written exactly once.
        self._labelled = False
        self._finished = False
        # What the manifest says the capture started at, kept so that the
        # project's own manifest can be dated against it when the run ends
        # (`SPEC.md` §5.3). The value is the injected clock's, never read again
        # from the file.
        self._started_at: str | None = None

    # -- the parts of the run ------------------------------------------------

    def _listener(
        self,
        out: Path,
        *,
        port: int,
        rejected: Path,
        body_suffix: str,
        forward: sink.Forward | None,
    ) -> _Listener:
        """One recorder, bound to its port and not yet serving.

        Constructing the recorder is where `SPEC.md` §3.1's refusal happens --
        a run directory that already holds a body -- and binding is where a
        port already in use does. Both are before the run directory exists.
        """
        recorder = sink.Recorder(
            out,
            now=self._now,
            rejected=rejected,
            body_suffix=body_suffix,
            forward=forward,
            after_record=self._announce_body,
            after_forward=self._announce_forward,
            create_directory=False,
        )
        server = self._make_server(recorder, host=self.host, port=port)
        return _Listener(recorder, server)

    def start(self) -> None:
        """Bring the run up, or raise and leave nothing on disk at all.

        The order is the whole of `SPEC.md` §4.6 and is checked by the order of
        these lines:

        1. the version is confirmed against the pin;
        2. both recorders are constructed and both sinks bind their ports, so
           a run directory that already holds a body and a port something else
           is holding are both refused here;
        3. the Collector is started and waited for -- its own ready line, and
           its receiver accepting a connection;
        4. **then** the run directory is made and the manifest labelled;
        5. then the sinks serve, raw last, so a forward always has somewhere to
           go and no body can be recorded before the manifest says what the
           capture is;
        6. then, and only then, the readiness line.

        Nothing before step 4 writes a byte. A refusal anywhere above it leaves
        no directory, which is what makes "there is a capture" mean "there was
        a capture to make".
        """
        version = collector.check_version(self._launcher, self._pin)
        try:
            self.json = self._listener(
                self.run / JSON_DIR,
                port=self._json_port,
                rejected=self.run / sink.REJECTED_JSON_DIR,
                body_suffix=sink.JSON_SUFFIX,
                forward=None,
            )
            self.raw = self._listener(
                self.run / RAW_DIR,
                port=self._raw_port,
                rejected=self.run / sink.REJECTED_DIR,
                body_suffix=sink.BODY_SUFFIX,
                forward=self._forward,
            )
            self.collector = self._launcher.start(
                f"http://{self.host}:{self.json.port}"
            )
        except BaseException:
            self.stop()
            raise

        self.run.mkdir(parents=True, exist_ok=True)
        self._started_at = self._now()
        manifest.label(
            self.run,
            kind=self._kind,
            collector_version=version,
            started_at=self._started_at,
        )
        self._labelled = True

        self.json.serve()
        self.raw.serve()
        self._log(READY_LINE)
        self._log(
            f"zoo capture: recording POST {sink.TRACES_PATH} on "
            f"http://{self.host}:{self.raw.port} -> {self.run / RAW_DIR}/"
        )
        self._log(
            f"zoo capture: collector {version} re-encoding to JSON into "
            f"{self.run / JSON_DIR}/, via http://{self.host}:{self.json.port}"
        )

    def request_stop(self) -> None:
        """Ask the run to end. What a signal handler calls (`SPEC.md` §4.6).

        Setting an event and nothing else, because this runs inside a signal
        handler: joining threads and terminating a child process from there is
        how a clean shutdown becomes a hung one.
        """
        self._stopping.set()

    def serve_forever(self, *, poll_interval: float = STOP_POLL) -> None:
        """Block until `request_stop` or `stop` is called.

        The sinks are already serving on their own threads; this is only the
        caller's wait. It waits in short hops rather than once and forever, and
        that is load-bearing rather than tidy: this process has three threads
        blocked in `select`, the kernel may hand a `SIGINT` to any of them, and
        a main thread parked in an untimed wait never runs the Python handler
        that would notice. A run that cannot be stopped with Ctrl-C leaves the
        Collector behind holding its port.
        """
        while not self._stopping.wait(poll_interval):
            # The same hop that keeps Ctrl-C answerable is where a Collector
            # that died is noticed, so it reaches the manifest during the run
            # rather than at the end of it (`SPEC.md` §4.6).
            self.check_collector()

    def stop(self) -> None:
        """Stop the raw sink, then the Collector, then the json sink.

        That order and no other: the exporter is told nothing more will be
        recorded, then the Collector is asked to shut down -- which flushes its
        last batch -- and only then does the thing it flushes into go away.

        Then, and only then, the manifest is closed (`SPEC.md` §5): `ended_at`
        is the end of the run, and the content headers are carried across from
        the headers files of every body -- including the ones the Collector's
        last flush only just landed.
        """
        self._stopping.set()
        if self.raw is not None:
            self.raw.stop()
        if self.collector is not None:
            # Asked before it is stopped: afterwards every Collector has an
            # exit status, and the one worth recording is the one it had
            # before anybody asked it to go (`SPEC.md` §4.6).
            self.check_collector()
            self.collector.stop()
            self.collector = None
        if self.json is not None:
            self.json.stop()
        self._finish()

    def check_collector(self) -> None:
        """Notice a Collector child that exited on its own (`SPEC.md` §4.6).

        Called on every hop of the caller's wait and once more on the way out.
        A Collector that is gone means `json/` stopped being written, which is
        a fact about the capture: it goes into `MANIFEST.json` as a `problems`
        entry the moment it is seen, is printed, and makes `zoo capture` exit
        non-zero. Recorded once, however often it is looked at -- a problem
        repeated every 200 milliseconds would be a manifest full of one fact.
        """
        if self.collector is None or self._collector_exited:
            return
        code = self.collector.returncode()
        if code is None:
            return
        self._collector_exited = True
        problem = f"collector exited: {code}"
        self.problems.append(problem)
        if self._labelled:
            manifest.append_problem(self.run, problem)
        self._log(
            f"  ! {problem} -- the raw bytes are still being recorded, "
            f"json/ is not (SPEC.md section 4.6)"
        )

    def _finish(self) -> None:
        """Assemble the manifest, once (`SPEC.md` §5.5).

        The journals become `bodies` and `forwards`, every other file in the
        run directory gets a digest, the project's own manifest is copied as it
        stands *now*, and `ended_at` goes in last.

        Guarded both ways: nothing is written for a run that never got as far
        as a labelled manifest (there is no capture to close, and no directory
        to put one in), and nothing is written twice when `stop()` is called
        again -- `zoo capture` calls it from a `finally` and `start()` calls it
        on the way out of a failure.

        Whatever the completion could not do -- a project manifest that is gone
        or that belongs to an earlier run, a journal line it could not read --
        joins `self.problems`, so it is in the manifest, in the summary and in
        the exit status (`SPEC.md` §5.3).
        """
        if not self._labelled or self._finished:
            return
        self._finished = True
        self.problems += manifest.finish(
            self.run,
            ended_at=self._now(),
            project_manifest=self._project_manifest,
            started_at=self._started_at,
        )

    # -- what it recorded ----------------------------------------------------

    @property
    def failed_forwards(self) -> list[manifest.ForwardEntry]:
        if self.raw is None:
            return []
        return self.raw.recorder.failed_forwards

    def summary(self) -> str:
        bodies = manifest.body_count(self.run)
        failures = len(self.failed_forwards)
        line = (
            f"zoo capture: {bodies} body/bodies under {self.run}/, "
            f"{manifest.MANIFEST_NAME} written: kind={self._kind}"
        )
        if failures:
            line = (
                f"{line}, {failures} forward(s) FAILED -- json/ is incomplete "
                f"and MANIFEST.json says which (SPEC.md section 4.4)"
            )
        for problem in self.problems:
            line = f"{line}, PROBLEM: {problem}"
        return line

    def _announce_body(self, entry: manifest.BodyEntry) -> None:
        self._log(f"  {entry.file}  {entry.bytes} bytes  sha256:{entry.sha256[:12]}")
        if self._on_record is not None:
            self._on_record(entry)

    def _announce_forward(self, outcome: manifest.ForwardEntry) -> None:
        if outcome.error is not None:
            self._log(f"  ! {outcome.file} recorded, NOT forwarded: {outcome.error}")
        elif outcome.failed:
            self._log(f"  ! {outcome.file} forwarded, collector said {outcome.status}")
