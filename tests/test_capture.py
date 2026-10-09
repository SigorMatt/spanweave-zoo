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
import threading
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
}


class Clock:
    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> str:
        self.ticks += 1
        return f"2026-10-09T12:00:{self.ticks:02d}+00:00"


class Started:
    def __init__(self) -> None:
        self.stopped = 0

    def stop(self) -> None:
        self.stopped += 1


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


def project_manifest_file(tmp_path: Path) -> Path:
    """The path an operator passes with `--project-manifest` (`SPEC.md` §5)."""
    path = tmp_path / "streaming-concierge" / "MANIFEST.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_json(path, PROJECT_MANIFEST)
    return path


def running_capture(
    run: Path,
    *,
    forwarder=None,
    version: str | None = None,
    kind: str = "recorded",
):
    """A started `Capture` on ports the OS picked, with a fake Collector."""
    straight = forwarder if forwarder is not None else Straight()
    launcher = FakeLauncher(version or pinned_version())
    started = capture.Capture(
        run,
        now=Clock(),
        launcher=launcher,
        forward=straight,
        pin=collector.pin(COLLECTOR_DIR),
        kind=kind,
        project_manifest=PROJECT_MANIFEST,
        raw_port=0,
        json_port=0,
        log=lambda line: None,
    )
    if isinstance(straight, Straight):
        straight.capture = started
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
