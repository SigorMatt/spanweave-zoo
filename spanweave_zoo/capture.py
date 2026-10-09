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
§4.5). Start order is json sink, then Collector, then raw sink -- nothing can
be forwarded before there is something to forward it to. Stop order is the
reverse, so that the Collector's last batch has somewhere to go.

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

# How often the waiting caller wakes to notice that it was asked to stop
# (`SPEC.md` §4.6). It is a poll interval and not a clock read: the main thread
# has to execute bytecode now and then or a signal handler never runs, because
# the OS may deliver the signal to any thread and the other threads here are
# blocked in `select`. `socketserver.serve_forever` takes the same parameter
# for the same reason.
STOP_POLL = 0.2

MakeServer = Callable[..., ThreadingHTTPServer]


class _Listener:
    """One sink on its own thread, shut down and joined on the way out."""

    def __init__(
        self,
        recorder: sink.Recorder,
        server: ThreadingHTTPServer,
    ) -> None:
        self.recorder = recorder
        self.server = server
        self.port: int = server.server_address[1]
        self._thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=30)


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
        project_manifest: object,
        host: str = "127.0.0.1",
        raw_port: int = DEFAULT_RAW_PORT,
        json_port: int = DEFAULT_JSON_PORT,
        make_server: MakeServer = sink.make_server,
        log: Callable[[str], None] = print,
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
        # what it is would be a capture the audit has to guess about.
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
        self._stopping = threading.Event()
        # Whether there is a manifest to close, and whether it was closed.
        # `stop()` runs on the way out of a failed `start()` as well as at the
        # end of a run, and `ended_at` is written exactly once.
        self._labelled = False
        self._finished = False

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
        recorder = sink.Recorder(
            out,
            now=self._now,
            rejected=rejected,
            body_suffix=body_suffix,
            forward=forward,
            after_record=self._announce_body,
            after_forward=self._announce_forward,
        )
        server = self._make_server(recorder, host=self.host, port=port)
        return _Listener(recorder, server)

    def start(self) -> None:
        """Bring the run up, or raise and leave nothing half-started.

        Order matters and is checked by the order of these lines: the version
        is confirmed against the pin before a directory is made, the manifest
        is labelled before a body can arrive, and the raw sink -- the only one
        the exporter talks to -- is last, so a forward always has somewhere to
        go.
        """
        version = collector.check_version(self._launcher, self._pin)
        self.run.mkdir(parents=True, exist_ok=True)
        manifest.label(
            self.run,
            kind=self._kind,
            collector_version=version,
            project_manifest=self._project_manifest,
            started_at=self._now(),
        )
        self._labelled = True

        self.json = self._listener(
            self.run / JSON_DIR,
            port=self._json_port,
            rejected=self.run / sink.REJECTED_JSON_DIR,
            body_suffix=sink.JSON_SUFFIX,
            forward=None,
        )
        self.json.start()
        self._log(
            f"zoo capture: json sink on http://{self.host}:{self.json.port}"
            f" -> {self.run / JSON_DIR}/"
        )

        try:
            self.collector = self._launcher.start(
                f"http://{self.host}:{self.json.port}"
            )
            self._log(f"zoo capture: collector {version} up, re-encoding to JSON")
            self.raw = self._listener(
                self.run / RAW_DIR,
                port=self._raw_port,
                rejected=self.run / sink.REJECTED_DIR,
                body_suffix=sink.BODY_SUFFIX,
                forward=self._forward,
            )
            self.raw.start()
        except BaseException:
            self.stop()
            raise
        self._log(
            f"zoo capture: recording POST {sink.TRACES_PATH} on "
            f"http://{self.host}:{self.raw.port} -> {self.run / RAW_DIR}/"
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
            pass

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
            self.collector.stop()
            self.collector = None
        if self.json is not None:
            self.json.stop()
        self._finish()

    def _finish(self) -> None:
        """Write `ended_at` and the body entries' content headers, once.

        Guarded both ways: nothing is written for a run that never got as far
        as a labelled manifest (there is no capture to close, and no directory
        to put one in), and nothing is written twice when `stop()` is called
        again -- `zoo capture` calls it from a `finally` and `start()` calls it
        on the way out of a failure.
        """
        if not self._labelled or self._finished:
            return
        self._finished = True
        manifest.finish(self.run, ended_at=self._now())

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
            return (
                f"{line}, {failures} forward(s) FAILED -- json/ is incomplete "
                f"and MANIFEST.json says which (SPEC.md section 4.4)"
            )
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
