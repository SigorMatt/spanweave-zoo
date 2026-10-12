"""`make audit-check`: the audit's tests RAN, and none of them skipped.

The audit needs the `audit` extra -- `spanweave`, `spanweave-live` and
`agentgolden`, pinned by git sha -- and no `check` leg installs it, by design
(`pyproject.toml`, the `audit` extra): every other batch must work without
them. So the tests that run the audit are marked `needs_audit` and skip on
those legs, and a green tick there says nothing about the audit either way.
This is `collector-check`'s answer to the same problem (`SPEC.md` §4.9): run
exactly the marked tests, read pytest's junit report rather than its exit code,
and fail if any skipped or if the marker selected nothing at all.

It also runs `mypy --strict` over the package with the three libraries
installed, so `audit.py` is type-checked against the real `spanweave` API and
not only against the `Any` an absent import becomes on a `check` leg.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from tests.collector_check import outcomes

REPO = Path(__file__).resolve().parent.parent

# The marker, spelled here, in `pyproject.toml` and in
# `tests/test_audit_real.py`, and nowhere else.
MARKER = "needs_audit"


def verdict(report: str) -> list[str]:
    """Why this report fails the guard. Empty means it passed."""
    cases = outcomes(report)
    if not cases:
        return [
            f"no test carries the `{MARKER}` marker, so this ran nothing at "
            f"all -- the audit was never exercised (SPEC.md §7)"
        ]
    return [f"{outcome}: {name}" for name, outcome in cases if outcome != "passed"]


def main() -> int:
    print(f"audit-check: the `{MARKER}` tests run, and not one of them skips")
    types = [sys.executable, "-m", "mypy", "--strict", "spanweave_zoo"]
    print(f"  $ {' '.join(types)}", flush=True)
    if subprocess.run(types, cwd=REPO).returncode != 0:
        raise SystemExit("audit-check: FAILED: mypy --strict, with the extra")
    with tempfile.TemporaryDirectory(prefix="zoo-audit-check-") as scratch:
        report_path = Path(scratch) / "report.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            MARKER,
            "-v",
            "-rs",
            "--junitxml",
            str(report_path),
        ]
        print(f"  $ {' '.join(command)}", flush=True)
        code = subprocess.run(command, cwd=REPO).returncode
        if not report_path.is_file():
            raise SystemExit(f"audit-check: pytest wrote no report (exit {code}).")
        report = report_path.read_text(encoding="utf-8")
    cases = outcomes(report)
    for name, outcome in cases:
        print(f"  {outcome:<8} {name}")
    problems = verdict(report)
    if problems or code != 0:
        for problem in problems:
            print(f"  ! {problem}")
        raise SystemExit(
            f"audit-check: FAILED (pytest exit {code}). A skip here means the "
            f"`audit` extra is not installed: uv sync --extra dev --extra audit."
        )
    print(f"audit-check: OK -- {len(cases)} audit tests ran, none skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
