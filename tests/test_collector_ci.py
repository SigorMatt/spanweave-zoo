"""The sixth CI leg: the Collector really ran, and the guard knows if it did not.

Two pieces, and only the second is interesting. The first is the archive cache
`make collector` keeps so CI does not fetch 100 MB on every push, keyed on the
sha256 that pins it -- and refusing a cached archive whose digest is not that
one, because a cache hit that trusted a file name would be a way of running an
unpinned Collector while the fetcher printed the pin.

The second is the guard. `make collector-check` exists because a skip is
invisible in a green tick: pytest exits `0` when every selected test skips, so
the five `check` legs have always been able to report success having never
re-encoded a byte (`SPEC.md` §4.9). So `verdict()` is run here against
**planted reports** -- a skip, an empty run, a failure, an error -- the way
`tests/test_gates.py` runs the import gate against planted violations. A guard
nobody has watched fail is a guard nobody knows works.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests import collector_check

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_DIR = REPO / "collector"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
REAL_TESTS = REPO / "tests" / "test_collector_real.py"


def report(*cases: str) -> str:
    """A junit-xml report shaped the way pytest writes one."""
    return (
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite '
        'name="pytest" errors="0" failures="0" skipped="0" tests="0">'
        + "".join(cases)
        + "</testsuite></testsuites>"
    )


def case(name: str, outcome: str = "") -> str:
    body = f'<{outcome} message="planted">planted</{outcome}>' if outcome else ""
    return (
        f'<testcase classname="tests.test_collector_real" name="{name}" '
        f'time="0.1">{body}</testcase>'
    )


def fetcher():
    """`collector/fetch.py` as a module. It is a script, deliberately: it is the
    one thing in the repository that opens a socket to the internet, and it
    lives outside `spanweave_zoo/` so that `urllib` never appears there."""
    spec = importlib.util.spec_from_file_location(
        "zoo_collector_fetch", COLLECTOR_DIR / "fetch.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the guard, watched failing ------------------------------------------


def test_the_guard_fails_when_a_marked_test_skipped():
    # The failure mode the whole sixth leg exists for. Two passed and one
    # skipped is not "two thirds proved": the skip is a claim nobody checked.
    problems = collector_check.verdict(
        report(
            case("test_the_binary_on_disk_is_the_pinned_version"),
            case("test_a_protobuf_export_comes_back_as_json", "skipped"),
            case("test_the_collector_refuses_rather_than_hangs"),
        )
    )
    assert problems == [
        "skipped: tests.test_collector_real::test_a_protobuf_export_comes_back_as_json"
    ]


def test_the_guard_fails_when_every_marked_test_skipped():
    # What the leg looks like with no binary on disk: pytest's exit code is 0.
    problems = collector_check.verdict(
        report(case("test_one", "skipped"), case("test_two", "skipped"))
    )
    assert [p.split(":")[0] for p in problems] == ["skipped", "skipped"]


def test_the_guard_fails_when_the_marker_selected_nothing():
    # A renamed marker, a dropped decorator, a deleted file: pytest reports no
    # tests and exits 5, and a job that only looked at skips would see none.
    [problem] = collector_check.verdict(report())
    assert collector_check.MARKER in problem
    assert "ran nothing at all" in problem


@pytest.mark.parametrize("outcome", ["failure", "error"])
def test_the_guard_fails_on_a_failure_and_on_an_error(outcome):
    [problem] = collector_check.verdict(report(case("test_one", outcome)))
    assert problem.startswith(f"{outcome}: ")


def test_the_guard_passes_only_when_every_marked_test_passed():
    assert collector_check.verdict(report(case("test_one"), case("test_two"))) == []


def test_the_guard_reports_every_outcome_it_read():
    assert collector_check.outcomes(
        report(case("test_one"), case("test_two", "skipped"))
    ) == [
        ("tests.test_collector_real::test_one", "passed"),
        ("tests.test_collector_real::test_two", "skipped"),
    ]


# --- the marker is the set the guard watches ------------------------------


def test_every_test_that_needs_the_collector_carries_the_marker():
    # The guard selects by `-m needs_collector`. A test in this file written
    # without the decorator would need the binary, fail without it, and sit
    # outside the set the sixth leg proves ran -- so the decorator is checked
    # here rather than remembered.
    tree = ast.parse(REAL_TESTS.read_text(encoding="utf-8"))
    tests = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert len(tests) >= 3, "the real-Collector tests went missing"
    for node in tests:
        names = [
            decorator.id
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Name)
        ]
        assert collector_check.MARKER in names, f"{node.name} is unmarked"


def test_the_marker_selects_exactly_those_tests():
    # And the marker works as a selector, which is a separate claim from being
    # written down: `pytest -m` must find them whether they skip or run.
    collected = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            collector_check.MARKER,
            "--collect-only",
            "-q",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert collected.returncode == 0, collected.stdout + collected.stderr
    selected = [
        line for line in collected.stdout.splitlines() if line.startswith("tests/")
    ]
    assert selected, collected.stdout
    assert all(line.startswith("tests/test_collector_real.py::") for line in selected)


# --- the cached archive ---------------------------------------------------


def test_a_cached_archive_with_the_pinned_digest_is_reused(tmp_path):
    fetch = fetcher()
    archive = tmp_path / "otelcol-contrib_0.0.0_linux_amd64.tar.gz"
    archive.write_bytes(b"pretend this is a release tarball")
    assert fetch.cached(archive, fetch.digest_of(archive)) is True


def test_an_archive_that_is_not_there_is_not_a_cache_hit(tmp_path):
    fetch = fetcher()
    assert fetch.cached(tmp_path / "absent.tar.gz", "0" * 64) is False


def test_a_cached_archive_whose_digest_is_not_the_pin_is_refused(tmp_path):
    # The degenerate case: a truncated download, a poisoned cache, a restored
    # key from another version. `make collector` must refuse it exactly as it
    # refuses a bad download -- these are not the bytes that were pinned
    # (`SPEC.md` §4.1) -- and say how to get rid of it.
    fetch = fetcher()
    archive = tmp_path / "otelcol-contrib_0.162.0_linux_amd64.tar.gz"
    archive.write_bytes(b"not the pinned bytes")
    with pytest.raises(SystemExit) as refused:
        fetch.cached(archive, "a" * 64)
    said = str(refused.value)
    assert "REFUSING" in said
    assert "a" * 64 in said
    assert fetch.digest_of(archive) in said
    assert str(archive) in said


def test_the_printed_pin_is_the_asset_and_the_digest_from_sha256sums():
    # What CI keys its cache on. Read from the pin by the fetcher, so the key
    # cannot drift from `collector/SHA256SUMS`.
    printed = subprocess.run(
        [sys.executable, str(COLLECTOR_DIR / "fetch.py"), "--print-pin"],
        capture_output=True,
        text=True,
        check=True,
    )
    pin = dict(
        line.split("=", 1) for line in printed.stdout.splitlines() if "=" in line
    )
    fetch = fetcher()
    version = (COLLECTOR_DIR / "VERSION").read_text(encoding="utf-8").strip()
    assert pin["asset"].startswith(f"otelcol-contrib_{version}_")
    assert pin["asset"].endswith(".tar.gz")
    assert pin["sha256"] == fetch.pinned_digests()[pin["asset"]]
    assert len(pin["sha256"]) == 64


def test_an_unknown_argument_is_a_refusal():
    fetch = fetcher()
    with pytest.raises(SystemExit) as refused:
        fetch.main(["--unpack-whatever"])
    assert "usage" in str(refused.value)


# --- the leg itself -------------------------------------------------------


def test_ci_has_a_sixth_leg_that_fetches_the_collector_and_proves_it_ran():
    # The deliverable of this batch is a CI job, so the job is asserted the way
    # README's commands are: as the text that runs.
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "\n  collector:\n" in workflow, "no `collector` job"
    assert "- run: make collector\n" in workflow
    assert "- run: make collector-check\n" in workflow, (
        "the leg fetches the Collector but never proves the tests ran"
    )
    # Cached by the digest that pins it, not by a date or a branch.
    assert "path: collector/.cache" in workflow
    assert "fetch.py --print-pin" in workflow
    assert "steps.pin.outputs.sha256" in workflow


def test_make_has_the_target_ci_runs():
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "\ncollector-check:\n\tuv run python -m tests.collector_check\n" in makefile
    # And it is not a prerequisite of `check`: `make check` must stay green on
    # a machine with no binary (`SPEC.md` §4.9).
    assert "check: lint types test gates verify\n" in makefile
