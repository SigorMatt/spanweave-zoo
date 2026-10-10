"""`make collector-check`: the Collector tests RAN, and none of them skipped.

A2's central claim -- a protobuf export through the tee comes back as OTLP JSON
carrying the same trace and span ids -- is the one thing no seam can stand in
for, and checking it needs the real stock binary: a gitignored ~100 MB
download. So the tests that check it are marked `needs_collector` and skip when
the binary is absent (`SPEC.md` §4.9). That skip is honest. It is also why, for
five CI legs, the claim was only ever *checked* on the maintainer's machine: in
a green tick, a leg where every one of those tests skipped is
indistinguishable from a leg where every one of them passed.

This is the difference. It runs exactly the marked tests, reads pytest's own
junit-xml report rather than its prose, and **fails if any of them skipped** --
or if the marker selected nothing at all, which is how a renamed marker or a
dropped decorator would otherwise turn the whole leg into a no-op that passes.
Note what cannot do this job: pytest's exit code is `0` when every selected
test skips, so "the command succeeded" is precisely the wrong question.

`verdict()` is pure and takes the report as text, so it can be run against
planted reports -- a skip, an empty run, a failure, an error -- in
`tests/test_collector_ci.py`. A guard nobody has watched fail is a guard nobody
knows works (`tests/gates.py`).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The marker, spelled here and in `tests/test_collector_real.py` and nowhere
# else. `-m needs_collector` is what selects the tests, so the name is part of
# the gate: `tests/test_collector_ci.py` asserts every test in that file
# carries it, because a test that lost the decorator would quietly leave the
# set this guard watches.
MARKER = "needs_collector"

# The junit-xml children that mean "this test did not run and pass". A
# `<skipped>` child is the one this whole target exists for.
NOT_PASSED = ("skipped", "failure", "error")


def outcomes(report: str) -> list[tuple[str, str]]:
    """`(test id, outcome)` for every case in a junit-xml report, in order.

    The report is pytest's own machine-readable output. Reading it is how this
    guard avoids parsing a summary line whose wording is pytest's to change.
    """
    cases = []
    for case in ElementTree.fromstring(report).iter("testcase"):
        found = [child.tag for child in case if child.tag in NOT_PASSED]
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        cases.append((name, found[0] if found else "passed"))
    return cases


def verdict(report: str) -> list[str]:
    """Why this report fails the guard. Empty means it passed.

    Two kinds of failure, and the second is the subtle one: a report with no
    cases in it at all. Selecting nothing is not a pass -- it is the leg having
    checked nothing, which is the state this target was added to end.
    """
    cases = outcomes(report)
    if not cases:
        return [
            f"no test carries the `{MARKER}` marker, so this ran nothing at "
            f"all -- the real Collector was never exercised (SPEC.md §4.9)"
        ]
    return [f"{outcome}: {name}" for name, outcome in cases if outcome != "passed"]


def run_marked_tests(report_path: Path) -> int:
    """Run the marked tests and leave a junit-xml report at `report_path`."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        MARKER,
        "-v",
        # Report the reason for every skip. If this guard is about to fail
        # because the binary is absent, the log should already say so.
        "-rs",
        "--junitxml",
        str(report_path),
    ]
    # Flushed, because in CI this process's stdout is a pipe and the child's is
    # the same pipe: unflushed, every line here would land after pytest's whole
    # run and the log would read in the wrong order.
    print(f"  $ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=REPO).returncode


def main() -> int:
    print(
        f"collector-check: the `{MARKER}` tests run, and not one of them skips",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="zoo-collector-check-") as scratch:
        report_path = Path(scratch) / "report.xml"
        code = run_marked_tests(report_path)
        if not report_path.is_file():
            raise SystemExit(
                f"collector-check: pytest wrote no report (exit {code}). "
                f"Nothing can be concluded about the Collector tests."
            )
        report = report_path.read_text(encoding="utf-8")

    cases = outcomes(report)
    for name, outcome in cases:
        print(f"  {outcome:<8} {name}")
    problems = verdict(report)
    if problems or code != 0:
        for problem in problems:
            print(f"  ! {problem}")
        raise SystemExit(
            f"collector-check: FAILED (pytest exit {code}).\n"
            f"The `{MARKER}` tests are the only check that the stock Collector "
            f"re-encodes a real protobuf export (SPEC.md §4.9), and on this "
            f"run they did not all pass. A skip here means the pinned binary "
            f"is absent: run `make collector` first."
        )
    print(
        f"collector-check: OK -- {len(cases)} tests ran against the real "
        f"Collector, none skipped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
