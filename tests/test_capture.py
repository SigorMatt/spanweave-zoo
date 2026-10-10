"""`zoo capture`: two sinks, one manifest, and the pin (`SPEC.md` §4.5, §4.6).

The Collector is the `launch` seam here, so these tests run everywhere --
including in CI, where no binary is fetched. What a launcher that starts
nothing cannot prove is the re-encoding itself, and that is
`test_collector_real.py`'s one job.

The pin is read from the repository's own `collector/` directory rather than
from a fixture: `collector/VERSION` is the record, and a test that asserted
against its own copy of the version would pass the day the two disagreed.
"""

from __future__ import annotations

import http.client
import json
import signal
import socket
import threading
import time
from pathlib import Path

import pytest

from spanweave_zoo import (
    __version__,
    capture,
    cli,
    collector,
    forward,
    manifest,
    sink,
)
from tests import otlp

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_DIR = REPO / "collector"

PROTOBUF = otlp.export_trace_service_request()
TIMEOUT = 5.0

# A pet project's own `MANIFEST.json`, as `EXPORT-CONTRACT.md` §1 has it. The
# zoo copies this document into the capture's manifest and reads no field of
# it (`SPEC.md` §5); these tests assert it arrives unchanged, not that it is
# valid anything.
PROJECT_MANIFEST = {
    "contract_version": "1.0",
    "framework": "openai",
    "framework_version": "2.6.1",
    "mode": "real",
    "model": "gpt-4.1-mini",
    # The project's own run starts after the capture is up -- the operator
    # brings the capture up first -- and `zoo capture` copies this document
    # when the run ends, dated against the capture's own start
    # (`SPEC.md` §5.3). The fake `Clock` below starts at `12:00:01`.
    "started_at": "2026-10-09T12:00:30+00:00",
}


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


class Started:
    """A Collector that is up, as the `launch` seam hands one back.

    `exited` is how a test says the child died on its own, which is what
    `SPEC.md` §4.6 has `zoo capture` notice during a run.
    """

    def __init__(self) -> None:
        self.stopped = 0
        self.exited: int | None = None

    def stop(self) -> None:
        self.stopped += 1

    def returncode(self) -> int | None:
        return self.exited


class FakeLauncher:
    """The `launch` seam with nothing behind it (`SPEC.md` §4.8)."""

    def __init__(self, version: str) -> None:
        self._version = version
        self.started: list[str] = []
        self.running = Started()

    def version(self) -> str:
        return self._version

    def start(self, json_endpoint: str) -> Started:
        self.started.append(json_endpoint)
        return self.running


def post(port: int, path: str, body: bytes, headers: dict[str, str] | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.request("POST", path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def pinned_version() -> str:
    return (COLLECTOR_DIR / "VERSION").read_text(encoding="utf-8").strip()


class Straight:
    """The forward with the Collector taken out of the middle.

    Points `HttpForward` at whatever port the json sink ended up on, which is
    only known once the capture has started -- so the lookup is deferred. What
    lands in `json/` is therefore the protobuf rather than JSON, and the tests
    that use this say so: what they are about is the two sinks, the one
    manifest and the pin, not the re-encoding.
    """

    def __init__(self) -> None:
        self.capture: capture.Capture | None = None

    def __call__(self, method, path, headers, body):
        assert self.capture is not None and self.capture.json is not None
        return forward.HttpForward("127.0.0.1", self.capture.json.port)(
            method, path, headers, body
        )


def project_manifest_file(tmp_path: Path, document: object = None) -> Path:
    """The path an operator passes with `--project-manifest` (`SPEC.md` §5)."""
    path = tmp_path / "streaming-concierge" / "MANIFEST.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_json(path, PROJECT_MANIFEST if document is None else document)
    return path


def running_capture(
    run: Path,
    *,
    forwarder=None,
    version: str | None = None,
    kind: str = "recorded",
    project_manifest: Path | None = None,
    log=None,
    wire=None,
):
    """A started `Capture` on ports the OS picked, with a fake Collector.

    `wire` is called with the capture **before** it starts, which is where
    `cli.run_capture` hands `Progress` the run it must ask to stop: the first
    line a capture prints is the readiness line, so anything that reacts to a
    printed line has to be connected before that (`SPEC.md` §4.6).
    """
    straight = forwarder if forwarder is not None else Straight()
    launcher = FakeLauncher(version or pinned_version())
    started = capture.Capture(
        run,
        now=Clock(),
        launcher=launcher,
        forward=straight,
        pin=collector.pin(COLLECTOR_DIR),
        kind=kind,
        project_manifest=project_manifest
        if project_manifest is not None
        else project_manifest_file(run.parent.parent.parent),
        raw_port=0,
        json_port=0,
        log=log if log is not None else (lambda line: None),
    )
    if isinstance(straight, Straight):
        straight.capture = started
    if wire is not None:
        wire(started)
    started.start()
    return started, launcher


# --- the pin, as the manifest carries it ------------------------------------


def test_the_collector_version_in_the_manifest_equals_collector_version(tmp_path):
    # The A2 row's second acceptance test, and `SPEC.md` §4.5: the pin, not a
    # guess -- written before the first body can arrive.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, launcher = running_capture(run)
    try:
        assert manifest.read(run)[manifest.COLLECTOR_VERSION] == pinned_version()
        assert launcher.started == [f"http://127.0.0.1:{started.json.port}"]
    finally:
        started.stop()
    assert launcher.running.stopped == 1


def test_capture_refuses_a_collector_that_does_not_report_the_pin(tmp_path):
    # `SPEC.md` §4.5: a capture labelled with a version that did not re-encode
    # it would be worse than one labelled with nothing.
    run = tmp_path / "captures" / "z4" / "run-1"
    with pytest.raises(collector.CollectorRefused) as refused:
        running_capture(run, version="0.0.0-not-the-pin")
    assert "0.0.0-not-the-pin" in str(refused.value)
    assert pinned_version() in str(refused.value)
    # Nothing was written: the refusal came before the run directory.
    assert not run.exists()


def test_the_pin_is_a_bare_version_and_the_config_is_checked_in():
    pinned = collector.pin(COLLECTOR_DIR)
    assert pinned.version == pinned_version()
    assert not pinned.version.startswith("v"), "VERSION is the version, not a tag"
    assert pinned.version.count(".") == 2, pinned.version
    assert pinned.config.is_file()
    assert pinned.binary.name == collector.BINARY_NAME


def test_the_pinned_config_is_stock_and_re_encodes_to_json():
    # `SPEC.md` §4.2. Asserted as text, because there is no YAML parser here
    # and there is not going to be one: zero runtime dependencies, and a dev
    # dependency to read four lines would be a dependency all the same.
    text = (COLLECTOR_DIR / "config.yaml").read_text(encoding="utf-8")
    assert "encoding: json" in text
    assert "compression: none" in text
    assert f"${{env:{collector.ENV_GRPC}:-127.0.0.1:4317}}" in text
    assert f"${{env:{collector.ENV_HTTP}:-127.0.0.1:4318}}" in text
    assert f"${{env:{collector.ENV_JSON_SINK}:-http://127.0.0.1:4319}}" in text
    assert "batch: {}" in text, "the batch processor is at its defaults"
    # Readiness is the Collector's own ready line (`SPEC.md` §4.6), and it logs
    # that at `info`: at `warn` a healthy Collector says nothing at all and
    # there would be nothing to read.
    assert "level: info" in text and "level: warn" not in text
    # Stock means stock: one receiver, one processor, one exporter.
    assert "receivers: [otlp]" in text
    assert "processors: [batch]" in text
    assert "exporters: [otlp_http]" in text


def test_every_pinned_platform_has_a_digest_for_the_pinned_version():
    # `SPEC.md` §4.1: `make collector` refuses a platform with no line, so the
    # lines must name the version that is pinned and not an older one.
    lines = [
        line.split()
        for line in (COLLECTOR_DIR / "SHA256SUMS").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines, "no pinned digests at all"
    for digest, asset in lines:
        assert len(digest) == 64 and int(digest, 16) >= 0, digest
        assert asset.startswith(f"otelcol-contrib_{pinned_version()}_"), asset
        assert asset.endswith(".tar.gz"), asset
    platforms = {asset.split("_")[2] for _, asset in lines}
    assert {"linux", "darwin"} <= platforms


# --- two sinks, one manifest ------------------------------------------------


def test_both_sinks_write_one_manifest_for_the_run(tmp_path):
    # `SPEC.md` §4.5: one `MANIFEST.json` per run directory, carrying `bodies`
    # for raw AND json -- which is what A3 extends. With the Collector taken
    # out of the middle, `json/0001.json` holds the protobuf; what is under
    # test is the manifest, the numbering and the two directories.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    try:
        status, _ = post(
            started.raw.port,
            "/v1/traces",
            PROTOBUF,
            {"Content-Type": "application/x-protobuf"},
        )
    finally:
        started.stop()
    assert status == 200

    assert sorted(path.name for path in run.iterdir()) == [
        "MANIFEST.json",
        manifest.JOURNAL_NAME,
        manifest.FORWARD_JOURNAL_NAME,
        "json",
        "raw",
    ]
    document = manifest.read(run)
    assert [entry["file"] for entry in document["bodies"]] == [
        "raw/0001.body",
        "json/0001.json",
    ]
    assert document[manifest.COLLECTOR_VERSION] == pinned_version()
    assert document[manifest.FORWARDS] == [{"file": "raw/0001.body", "status": 200}]
    assert (run / "raw" / "0001.body").read_bytes() == PROTOBUF
    assert (run / "json" / "0001.json").read_bytes() == PROTOBUF
    assert cli.verify(tmp_path / "captures") == 0
    assert started.failed_forwards == []


def test_the_two_sinks_rejected_directories_do_not_collide(tmp_path):
    # `SPEC.md` §4.5: two recorders on one run directory with one `rejected/`
    # would share a counter and overwrite each other. A misdirected POST is
    # still recorded, in each sink's own directory.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    try:
        raw_status, _ = post(started.raw.port, "/v1/metrics", b"aimed at the raw sink")
        json_status, _ = post(started.json.port, "/wrong", b"aimed at the json sink")
    finally:
        started.stop()
    assert (raw_status, json_status) == (404, 404)
    assert (run / "rejected" / "0001.body").read_bytes() == b"aimed at the raw sink"
    assert (
        run / "rejected-json" / "0001.body"
    ).read_bytes() == b"aimed at the json sink"
    assert [entry["file"] for entry in manifest.read(run)["bodies"]] == [
        "rejected/0001.body",
        "rejected-json/0001.body",
    ]
    assert cli.verify(tmp_path / "captures") == 0


def test_the_json_sinks_headers_are_kept_like_any_other_request(tmp_path):
    # `SPEC.md` §4.5: the Collector is an HTTP client like any other and the
    # sink does not keep less of what one caller sent than of another's.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    try:
        post(
            started.raw.port,
            "/v1/traces",
            PROTOBUF,
            {"Content-Type": "application/x-protobuf"},
        )
    finally:
        started.stop()
    delivered = json.loads((run / "json" / "0001.headers.json").read_text())
    pairs = {name.lower(): value for name, value in delivered["headers"]}
    assert pairs["content-type"] == "application/x-protobuf"
    assert delivered["path"] == "/v1/traces"
    assert delivered["received_at"].startswith("2026-10-09T12:00:")


# --- a forward that fails, and what `zoo capture` exits with -----------------


def test_a_failed_forward_leaves_the_capture_intact_and_exits_non_zero(tmp_path):
    # `SPEC.md` §4.4. The degenerate case the row's arrangement makes likely:
    # the Collector is a separate process and may simply not be there.
    run = tmp_path / "captures" / "z4" / "run-1"

    def refusing(method, path, headers, body):
        raise ConnectionRefusedError(111, "Connection refused")

    started, _ = running_capture(run, forwarder=refusing)
    try:
        status, _ = post(started.raw.port, "/v1/traces", PROTOBUF)
    finally:
        started.stop()
    assert status == 200, "the answer does not depend on the forward"
    assert (run / "raw" / "0001.body").read_bytes() == PROTOBUF
    assert list((run / "json").glob("*.json")) == [], (
        "nothing reached the Collector, so json/ is empty -- and says so"
    )
    assert [entry.error for entry in started.failed_forwards] == [
        "ConnectionRefusedError: [Errno 111] Connection refused"
    ]
    assert "FAILED" in started.summary()
    assert cli.verify(tmp_path / "captures") == 0


def test_capture_refuses_a_run_directory_that_already_holds_a_body(tmp_path):
    run = tmp_path / "captures" / "z4" / "run-1"
    (run / "raw").mkdir(parents=True)
    (run / "raw" / "0001.body").write_bytes(b"an earlier run's bytes")
    with pytest.raises(sink.CaptureExists):
        running_capture(run)
    assert (run / "raw" / "0001.body").read_bytes() == b"an earlier run's bytes"


def test_capture_refuses_a_json_directory_that_already_holds_a_body(tmp_path):
    # The json sink is checked too, and by its own suffix: `json/NNNN.json`.
    run = tmp_path / "captures" / "z4" / "run-1"
    (run / "json").mkdir(parents=True)
    (run / "json" / "0001.json").write_bytes(b"{}")
    with pytest.raises(sink.CaptureExists):
        running_capture(run)


# --- the command, and what it refuses ---------------------------------------


def test_the_capture_command_refuses_without_a_collector_directory(tmp_path, capsys):
    status = cli.main(
        [
            "capture",
            "--project",
            "z4",
            "--run-id",
            "run-1",
            "--kind",
            "recorded",
            "--captures",
            str(tmp_path / "captures"),
            "--project-manifest",
            str(project_manifest_file(tmp_path)),
            "--collector-dir",
            str(tmp_path / "nowhere"),
        ]
    )
    assert status == 2
    assert "VERSION" in capsys.readouterr().err
    assert not (tmp_path / "captures").exists()


def test_the_capture_command_refuses_without_the_binary(tmp_path, capsys):
    # `SPEC.md` §4.6: say so, and name `make collector`. The pin is checked in,
    # the binary is a gitignored download, and the refusal distinguishes them.
    elsewhere = tmp_path / "collector"
    elsewhere.mkdir()
    (elsewhere / "VERSION").write_text("0.162.0\n")
    (elsewhere / "config.yaml").write_text("receivers:\n")
    status = cli.main(
        [
            "capture",
            "--project",
            "z4",
            "--run-id",
            "run-1",
            "--kind",
            "recorded",
            "--captures",
            str(tmp_path / "captures"),
            "--project-manifest",
            str(project_manifest_file(tmp_path)),
            "--collector-dir",
            str(elsewhere),
            "--port",
            "0",
            "--json-port",
            "0",
        ]
    )
    assert status == 2
    error = capsys.readouterr().err
    assert "make collector" in error
    assert not (tmp_path / "captures").exists()


@pytest.mark.parametrize("run_id", ["two/segments", ".hidden", "", ".."])
def test_the_capture_command_refuses_a_run_id_that_is_not_one_segment(
    tmp_path, capsys, run_id
):
    # `SPEC.md` §2.1, enforced rather than assumed: `..` would write outside
    # the capture root and a slash would scatter one capture across two
    # directories.
    status = cli.main(
        [
            "capture",
            "--project",
            "z4",
            "--run-id",
            run_id,
            "--kind",
            "recorded",
            "--captures",
            str(tmp_path / "captures"),
            "--project-manifest",
            str(project_manifest_file(tmp_path)),
            "--collector-dir",
            str(COLLECTOR_DIR),
        ]
    )
    assert status == 2
    assert "single path segment" in capsys.readouterr().err


def test_capture_is_in_the_commands(capsys):
    with pytest.raises(SystemExit) as exited:
        cli.main(["--help"])
    assert exited.value.code == 0
    helped = capsys.readouterr().out
    for subcommand in ("sink", "capture", "verify"):
        assert subcommand in helped


def test_a_signal_ends_the_run_rather_than_leaving_the_collector_behind(tmp_path):
    """`SPEC.md` §4.6: Ctrl-C and `SIGTERM` both stop a capture.

    Driven through the handler `zoo capture` installs, with a real signal
    raised, because the thing this guards against is subtle and was observed:
    a capture has three threads blocked in `select`, the kernel may hand the
    signal to any of them, and a main thread parked in an untimed wait never
    runs the Python handler at all -- so Ctrl-C did nothing and the Collector
    stayed up holding its port.
    """
    run = tmp_path / "captures" / "z4" / "run-1"
    started, launcher = running_capture(run)
    previous = cli._stop_on_signal(started)
    try:
        waiter = threading.Thread(target=started.serve_forever, daemon=True)
        waiter.start()
        signal.raise_signal(signal.SIGINT)
        waiter.join(timeout=TIMEOUT)
        assert not waiter.is_alive(), "SIGINT did not end the run"
    finally:
        cli._restore_signals(previous)
        started.stop()
    assert launcher.running.stopped == 1, "the Collector was left running"


def test_both_stop_signals_are_handled(tmp_path):
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    previous = cli._stop_on_signal(started)
    try:
        assert set(previous) == {signal.SIGINT, signal.SIGTERM}
        for number in previous:
            assert signal.getsignal(number) not in (
                signal.SIG_DFL,
                signal.default_int_handler,
            )
    finally:
        cli._restore_signals(previous)
        started.stop()
    assert signal.getsignal(signal.SIGINT) == previous[signal.SIGINT]


def test_serve_forever_returns_once_stopped(tmp_path):
    # `zoo capture` blocks in `serve_forever` and is stopped by a signal; this
    # is the same path without a signal, so the test cannot hang: the wait is
    # on an `Event`, not on a clock (`SPEC.md` §4.8).
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    waiter = threading.Thread(
        target=lambda: started.serve_forever(poll_interval=0.01), daemon=True
    )
    waiter.start()
    started.stop()
    waiter.join(timeout=TIMEOUT)
    assert not waiter.is_alive()


# --- A3: the capture ends by writing the whole manifest (`SPEC.md` §5) ------


def test_the_capture_ends_by_writing_every_field_the_manifest_carries(tmp_path):
    # The A3 row, end to end over a socket: a real POST through the tee, then
    # the manifest the capture wrote when it stopped.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run, kind="real")
    try:
        status, _ = post(
            started.raw.port,
            "/v1/traces",
            PROTOBUF,
            {"Content-Type": "application/x-protobuf", "Content-Encoding": "gzip"},
        )
    finally:
        started.stop()
    assert status == 200

    document = manifest.read(run)
    assert document[manifest.KIND] == "real"
    assert document[manifest.PROJECT_MANIFEST] == PROJECT_MANIFEST
    assert document[manifest.SINK_VERSION] == __version__
    assert document[manifest.COLLECTOR_VERSION] == pinned_version()
    # Both timestamps come from the injected clock and from nowhere else
    # (`SPEC.md` §3.6), so they are values this test chose.
    assert document[manifest.STARTED_AT] == "2026-10-09T12:00:01+00:00"
    assert document[manifest.ENDED_AT].startswith("2026-10-09T12:00:")
    assert document[manifest.ENDED_AT] > document[manifest.STARTED_AT]
    # Carried across from each body's own `headers.json`, for raw AND json:
    # the Collector's forward kept the exporter's content headers (§4.3).
    assert [
        (entry["file"], entry["content_type"], entry["content_encoding"])
        for entry in document[manifest.BODIES]
    ] == [
        ("raw/0001.body", "application/x-protobuf", "gzip"),
        ("json/0001.json", "application/x-protobuf", "gzip"),
    ]
    assert cli.verify(tmp_path / "captures") == 0


def test_a_capture_cannot_be_constructed_without_declaring_its_kind(tmp_path):
    # No default, no inference (`SPEC.md` §5): the declaration is the only
    # difference between a recorded capture and a real one.
    with pytest.raises(TypeError):
        capture.Capture(
            tmp_path / "captures" / "z4" / "run-1",
            now=Clock(),
            launcher=FakeLauncher(pinned_version()),
            forward=Straight(),
            pin=collector.pin(COLLECTOR_DIR),
            project_manifest=PROJECT_MANIFEST,
        )


def test_the_manifest_declares_the_kind_before_the_first_body_can_arrive(tmp_path):
    # A capture stopped the hard way still says what it was: the declaration
    # and the pin are written at the start, `ended_at` at the end.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run, kind="real")
    try:
        document = manifest.read(run)
        assert document[manifest.KIND] == "real"
        assert document[manifest.STARTED_AT] == "2026-10-09T12:00:01+00:00"
        assert manifest.ENDED_AT not in document
    finally:
        started.stop()
    assert manifest.ENDED_AT in manifest.read(run)


def test_the_capture_command_requires_a_kind(tmp_path, capsys):
    # The A3 row's third acceptance test, at the one place an operator meets
    # it. A missing declaration is argparse's own refusal and exits non-zero.
    with pytest.raises(SystemExit) as exited:
        cli.main(
            [
                "capture",
                "--project",
                "z4",
                "--run-id",
                "run-1",
                "--captures",
                str(tmp_path / "captures"),
                "--project-manifest",
                str(project_manifest_file(tmp_path)),
                "--collector-dir",
                str(COLLECTOR_DIR),
            ]
        )
    assert exited.value.code == 2
    error = capsys.readouterr().err
    assert "required" in error and "--kind" in error
    assert not (tmp_path / "captures").exists()


def test_the_capture_command_refuses_a_kind_the_spec_does_not_name(tmp_path, capsys):
    with pytest.raises(SystemExit) as exited:
        cli.main(
            [
                "capture",
                "--project",
                "z4",
                "--run-id",
                "run-1",
                "--kind",
                "live",
                "--captures",
                str(tmp_path / "captures"),
                "--project-manifest",
                str(project_manifest_file(tmp_path)),
                "--collector-dir",
                str(COLLECTOR_DIR),
            ]
        )
    assert exited.value.code == 2
    error = capsys.readouterr().err
    assert "recorded" in error and "real" in error
    assert not (tmp_path / "captures").exists()


def test_the_capture_command_refuses_a_project_manifest_it_cannot_read(
    tmp_path, capsys
):
    # `SPEC.md` §5: loudly, at the start, before any bytes are on disk --
    # rather than at the end, when the capture is already a capture and the
    # one thing missing from it cannot be added without editing it.
    status = cli.main(
        [
            "capture",
            "--project",
            "z4",
            "--run-id",
            "run-1",
            "--kind",
            "real",
            "--captures",
            str(tmp_path / "captures"),
            "--project-manifest",
            str(tmp_path / "nowhere" / "MANIFEST.json"),
            "--collector-dir",
            str(COLLECTOR_DIR),
        ]
    )
    assert status == 2
    error = capsys.readouterr().err
    assert str(tmp_path / "nowhere" / "MANIFEST.json") in error
    assert not (tmp_path / "captures").exists()


def test_the_refusal_counts_bodies_and_headers_apart_in_the_json_sink(tmp_path):
    # Found by running the real flow (`SPEC.md` §3.1): the json sink's bodies
    # are `*.json`, so one glob matched `0001.headers.json` too and the
    # refusal said "2 body file(s), starting 0001.headers.json" for one
    # recorded export. The refusal was right and unreadable.
    run = tmp_path / "captures" / "z4" / "run-1"
    (run / "json").mkdir(parents=True)
    (run / "json" / "0001.json").write_bytes(b"{}")
    manifest.write_json(run / "json" / ("0001" + manifest.HEADERS_SUFFIX), {})
    with pytest.raises(sink.CaptureExists) as refused:
        running_capture(run)
    assert "1 body file(s) and 1 headers file(s)" in str(refused.value)
    assert "starting 0001.json" in str(refused.value)


def test_a_directory_holding_only_a_headers_file_is_still_refused(tmp_path):
    # Degenerate, and the safe answer: half a capture is a capture to refuse.
    # Writing `0001.json` beside a left-over `0001.headers.json` would
    # overwrite the half that is there.
    run = tmp_path / "captures" / "z4" / "run-1"
    (run / "raw").mkdir(parents=True)
    manifest.write_json(run / "raw" / ("0001" + manifest.HEADERS_SUFFIX), {})
    with pytest.raises(sink.CaptureExists) as refused:
        running_capture(run)
    assert "0 body file(s) and 1 headers file(s)" in str(refused.value)


# --- A3a: a capture exists only once it is ready (`SPEC.md` §4.6) ------------
#
# Readiness is three listeners accepting AND the Collector child alive with its
# own ready line in its log, and the run directory is made only after that.
# These tests therefore need a child process that behaves like the Collector
# around its receiver port, so they run `STUB_BODY` below under `collector.
# Binary` -- the real launcher, the real pipe, the real log reading -- rather
# than the 100 MB download `test_collector_real.py` skips without.

# The line the stock Collector logs once every component has started
# (`service@v.../service.go`). Written out here rather than imported, so these
# tests fail on an implementation that stopped looking for it as well as on one
# that never looked.
COLLECTOR_READY = "Everything is ready. Begin running and processing data."

# The one line that means a capture is up (`SPEC.md` §4.6), and `zoo sink`'s
# own banner, which must not be mistaken for it.
READINESS_LINE = "zoo capture: the raw bytes are the record. Ctrl-C to stop."
SINK_BANNER_LINE = "zoo sink: it parses nothing. Ctrl-C to stop."

STUB_BODY = """
import os
import socket
import sys
import time

if "--version" in sys.argv:
    print("otelcol-contrib version " + VERSION)
    raise SystemExit(0)

if BEHAVIOUR == "bad-config":
    # What the real binary does with a config it cannot load: one line on
    # stderr, exit 1, no port bound (`SPEC.md` §4.6).
    sys.stderr.write("Error: cannot start pipelines: this config is not one\\n")
    raise SystemExit(1)

host, _, port = os.environ["ZOO_COLLECTOR_OTLP_HTTP"].rpartition(":")
listener = socket.socket()
try:
    listener.bind((host, int(port)))
except OSError as held:
    # The real Collector's own words for a port it cannot have, and then exit
    # 1: `error  Failed to start component  {"error": "listen tcp ...: bind:
    # address already in use"}`.
    sys.stderr.write(
        "error\\tFailed to start component\\t{\\"error\\": \\"listen tcp "
        + host + ":" + port + ": bind: " + str(held.strerror) + "\\"}\\n"
    )
    raise SystemExit(1)
listener.listen(8)
if BEHAVIOUR == "ready":
    sys.stderr.write("info\\tservice.go:256\\t" + READY + "\\n")
sys.stderr.flush()
time.sleep(600)
"""


def free_port() -> int:
    """A port a child process can be told to bind before it exists.

    The Collector is given its receiver's port before it starts, so this cannot
    be `port=0` the way every sink in the suite is. If something does take it in
    between, that is the refusal these tests are about anyway.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def stub_collector(tmp_path: Path, *, behaviour: str) -> collector.Pin:
    """A `collector/` directory whose binary is `STUB_BODY`."""
    directory = tmp_path / f"stub-collector-{behaviour}"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / collector.VERSION_NAME).write_text(
        pinned_version() + "\n", encoding="utf-8"
    )
    (directory / collector.CONFIG_NAME).write_text("receivers:\n", encoding="utf-8")
    script = directory / collector.BINARY_NAME
    script.write_text(
        "#!/usr/bin/env python3\n"
        f"VERSION = {pinned_version()!r}\n"
        f"BEHAVIOUR = {behaviour!r}\n"
        f"READY = {COLLECTOR_READY!r}\n" + STUB_BODY,
        encoding="utf-8",
    )
    script.chmod(0o755)
    return collector.pin(directory)


def stub_capture(
    run: Path,
    tmp_path: Path,
    *,
    behaviour: str,
    collector_port: int | None = None,
    attempts: int = 30,
    log=None,
):
    """A `Capture` whose Collector is the stub, on a port chosen here.

    The readiness wait gets the real `sleep`, as `zoo capture` gives it: what
    is being waited on is another process starting, and the budget is bounded
    by `attempts` rather than by a clock (`SPEC.md` §4.8).
    """
    pinned = stub_collector(tmp_path, behaviour=behaviour)
    port = collector_port if collector_port is not None else free_port()
    launcher = collector.Binary(
        pinned,
        host="127.0.0.1",
        http_port=port,
        grpc_port=0,
        sleep=time.sleep,
        attempts=attempts,
        pause=0.05,
    )
    return capture.Capture(
        run,
        now=Clock(),
        launcher=launcher,
        forward=lambda method, path, headers, body: 200,
        pin=pinned,
        kind="recorded",
        project_manifest=project_manifest_file(tmp_path),
        raw_port=0,
        json_port=0,
        log=log if log is not None else (lambda line: None),
    )


def test_a_foreign_listener_on_the_collector_port_is_refused_and_writes_nothing(
    tmp_path,
):
    # The A3a row's first test. Something else is on the Collector's port, so
    # the Collector cannot have it and exits -- and a capture whose `json/`
    # could only ever be empty is refused before a byte is written, naming the
    # port so the operator knows what to kill (`SPEC.md` §4.6).
    run = tmp_path / "captures" / "z4" / "run-1"
    held = socket.socket()
    held.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    held.bind(("127.0.0.1", 0))
    held.listen(8)
    port = int(held.getsockname()[1])
    try:
        started = stub_capture(
            run, tmp_path, behaviour="ready", collector_port=port, attempts=30
        )
        with pytest.raises(collector.CollectorRefused) as refused:
            started.start()
    finally:
        held.close()
    assert str(port) in str(refused.value), str(refused.value)
    assert not run.exists(), "a refusal before readiness leaves no directory"
    assert not (tmp_path / "captures").exists()


def test_a_collector_that_holds_the_port_without_reporting_ready_is_refused(tmp_path):
    # The AND in `SPEC.md` §4.6, and the one a connection cannot check: the
    # stub binds the receiver port and accepts connections, and never logs the
    # line the Collector logs when it is actually running. A readiness probe
    # that only connected would call this capture ready and record a run whose
    # `json/` stays empty.
    run = tmp_path / "captures" / "z4" / "run-1"
    started = stub_capture(run, tmp_path, behaviour="silent", attempts=10)
    with pytest.raises(collector.CollectorRefused) as refused:
        started.start()
    assert COLLECTOR_READY in str(refused.value)
    assert not run.exists(), "a refusal before readiness leaves no directory"


def test_a_collector_that_cannot_start_at_all_is_refused_naming_the_cause(tmp_path):
    # Degenerate: a bad config. The child exits before it binds anything, and
    # the refusal carries the Collector's own last words rather than a timeout.
    run = tmp_path / "captures" / "z4" / "run-1"
    started = stub_capture(run, tmp_path, behaviour="bad-config", attempts=30)
    with pytest.raises(collector.CollectorRefused) as refused:
        started.start()
    assert "cannot start pipelines" in str(refused.value)
    assert not run.exists()


def test_a_ready_collector_makes_the_directory_and_prints_one_readiness_line(tmp_path):
    # The other side of the same rule: once three listeners accept and the
    # Collector has said it is ready, the run directory is made, the manifest
    # is labelled, and the readiness line is printed -- once, first.
    run = tmp_path / "captures" / "z4" / "run-1"
    printed: list[str] = []
    started = stub_capture(
        run, tmp_path, behaviour="ready", attempts=100, log=printed.append
    )
    started.start()
    try:
        assert printed[0] == READINESS_LINE
        assert printed.count(READINESS_LINE) == 1
        assert run.is_dir()
        document = manifest.read(run)
        assert document[manifest.KIND] == "recorded"
        assert document[manifest.STARTED_AT] == "2026-10-09T12:00:01+00:00"
        assert started.raw is not None and started.json is not None
        status, _ = post(started.raw.port, "/v1/traces", PROTOBUF)
        assert status == 200, "the raw sink is serving by the time it is announced"
    finally:
        started.stop()
    assert collector.READY_MARKER == COLLECTOR_READY
    assert cli.verify(tmp_path / "captures") == 0


def test_the_collector_exiting_mid_capture_is_recorded_and_reported(tmp_path):
    # `SPEC.md` §4.6: a Collector that dies during a run is a failure written
    # into the manifest and reported at exit, never a silently empty `json/`.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, launcher = running_capture(run)
    try:
        launcher.running.exited = 137
        started.check_collector()
        started.check_collector()  # recorded once, not once per look
        assert started.problems == ["collector exited: 137"]
        assert manifest.read(run)[manifest.PROBLEMS] == ["collector exited: 137"]
        assert "collector exited: 137" in started.summary()
        assert cli._exit_status(started) == 1
    finally:
        started.stop()


def test_a_capture_with_no_problems_exits_zero(tmp_path):
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run)
    try:
        assert started.problems == []
        assert cli._exit_status(started) == 0
    finally:
        started.stop()
    assert manifest.PROBLEMS not in manifest.read(run)


def test_the_sink_banner_is_distinct_from_the_captures_readiness_line():
    # Both end "Ctrl-C to stop." and they mean different things: one says
    # bytes are being recorded with nothing behind the sink, the other that a
    # whole tee is up. An operator reading a log must not have to guess which
    # command they are looking at.
    assert capture.READY_LINE == READINESS_LINE
    assert cli.SINK_BANNER == SINK_BANNER_LINE
    assert capture.READY_LINE != cli.SINK_BANNER
    assert capture.READY_LINE not in cli.SINK_BANNER
    assert cli.SINK_BANNER not in capture.READY_LINE
    assert "zoo capture:" in capture.READY_LINE
    assert "zoo sink:" in cli.SINK_BANNER


# --- A3b: the manifest is assembled at the end, and covers the capture ------


def test_the_end_of_run_manifest_covers_every_file_in_the_run_directory(tmp_path):
    # The A3b row, through the tee and over a socket: the journals, both
    # headers files and both bodies, each with a digest of its own.
    run = tmp_path / "captures" / "z4" / "run-1"
    started, _ = running_capture(run, kind="real")
    try:
        post(
            started.raw.port,
            "/v1/traces",
            PROTOBUF,
            {"Content-Type": "application/x-protobuf"},
        )
    finally:
        started.stop()

    document = manifest.read(run)
    accounted = {entry["file"] for entry in document[manifest.BODIES]} | {
        entry["file"] for entry in document[manifest.FILES]
    }
    assert accounted == {
        path.relative_to(run).as_posix()
        for path in run.rglob("*")
        if path.is_file() and path.name != manifest.MANIFEST_NAME
    }
    assert manifest.JOURNAL_NAME in accounted
    assert manifest.FORWARD_JOURNAL_NAME in accounted
    assert "raw/0001" + manifest.HEADERS_SUFFIX in accounted
    assert "json/0001" + manifest.HEADERS_SUFFIX in accounted
    assert cli.verify(tmp_path / "captures") == 0


def test_a_project_manifest_rewritten_mid_run_lands_as_the_end_of_run_copy(tmp_path):
    # The A3b row's first acceptance test, and the manifest-timing decision:
    # the project writes its own `MANIFEST.json` while it runs, so the copy a
    # capture carries is the one that is there when the capture ends -- not the
    # one its previous run left behind (`SPEC.md` §5.3).
    run = tmp_path / "captures" / "z4" / "run-1"
    before = dict(PROJECT_MANIFEST, model="the-previous-runs-model")
    path = project_manifest_file(tmp_path, before)
    started, _ = running_capture(run, project_manifest=path)
    try:
        # What `make run-real` does while the capture is up.
        during = dict(PROJECT_MANIFEST, model="the-recorded-runs-model")
        manifest.write_json(path, during)
    finally:
        started.stop()
    assert manifest.read(run)[manifest.PROJECT_MANIFEST] == during
    assert started.problems == []
    assert cli._exit_status(started) == 0
    assert cli.verify(tmp_path / "captures") == 0


def test_a_project_manifest_older_than_the_capture_is_a_problem_and_exits_non_zero(
    tmp_path, capsys
):
    # The A3b row's second acceptance test. A document written before this
    # capture existed is an earlier run's: the capture carries none, says why,
    # exits non-zero, and does not verify.
    run = tmp_path / "captures" / "z4" / "run-1"
    stale = dict(PROJECT_MANIFEST, started_at="2026-10-09T09:00:00+00:00")
    started, _ = running_capture(
        run, project_manifest=project_manifest_file(tmp_path, stale)
    )
    started.stop()

    document = manifest.read(run)
    assert document[manifest.PROJECT_MANIFEST] is None
    assert document[manifest.PROBLEMS] == started.problems
    assert "09:00:00" in document[manifest.PROBLEMS][0]
    assert cli._exit_status(started) == 1
    assert "PROBLEM" in started.summary()
    assert cli.verify(tmp_path / "captures") == 1
    assert "09:00:00" in capsys.readouterr().out


class Pipe:
    """A stdout that was closed by whatever was reading it.

    `zoo capture | head -5`: the reader is gone, and the next write raises.
    """

    def __init__(self) -> None:
        self.writes = 0

    def write(self, text: str) -> int:
        self.writes += 1
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self) -> None:
        pass


class Recording:
    """A stdout that writes down what was written and when it was flushed."""

    def __init__(self) -> None:
        self.text = ""
        self.flushed = ""

    def write(self, text: str) -> int:
        self.text += text
        return len(text)

    def flush(self) -> None:
        self.flushed = self.text


def test_every_progress_line_is_flushed_as_it_is_written(tmp_path):
    # `SPEC.md` §4.6: an operator watching a pet project export into a log file
    # sees each body as it lands, not when the capture is stopped -- so the
    # line is flushed while the run is still going, and this test looks at the
    # stream before the capture stops.
    run = tmp_path / "captures" / "z4" / "run-1"
    stream = Recording()
    progress = cli.Progress(stream)
    started, _ = running_capture(run, log=progress)
    try:
        assert capture.READY_LINE in stream.flushed
        post(started.raw.port, "/v1/traces", PROTOBUF)
        assert "raw/0001.body" in stream.flushed
    finally:
        started.stop()


def test_a_closed_stdout_ends_the_run_and_leaves_the_manifest_complete(tmp_path):
    # `SPEC.md` §4.6: `zoo capture | head` closes the pipe under three
    # recording threads. The run ends the way Ctrl-C ends it -- the manifest is
    # completed -- rather than a traceback out of a handler thread, and the
    # exit status is what the capture was, not what the pipe did.
    run = tmp_path / "captures" / "z4" / "run-1"
    pipe = Pipe()
    progress = cli.Progress(pipe)
    started, _ = running_capture(
        run,
        log=progress,
        wire=lambda running: setattr(progress, "on_broken", running.request_stop),
    )
    try:
        # The readiness line already broke it, and nothing raised.
        assert progress.broken
        assert pipe.writes == 1, "it kept writing to a stream that is gone"
        # The run was asked to stop, so the caller's wait returns on its own.
        started.serve_forever(poll_interval=0.01)
    finally:
        started.stop()

    document = manifest.read(run)
    assert document[manifest.ENDED_AT] > document[manifest.STARTED_AT]
    assert manifest.FILES in document
    assert started.problems == []
    assert cli._exit_status(started) == 0
    assert cli.verify(tmp_path / "captures") == 0
