"""`zoo audit` without the `audit` extra (`SPEC.md` §7.1).

These run on every leg, extra or not. The audit module imports the three
pinned libraries at its top, so `cli.py` imports it only when `zoo audit`
runs: everything else the zoo does must work with the extra uninstalled, and
`zoo audit` without it is a refusal naming the command that installs it --
not a traceback, and not a report of nothing.

The tests that run the audit itself need the extra and are in
`tests/test_audit_real.py`, under the `needs_audit` marker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import spanweave_zoo
from spanweave_zoo import cli

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "capture"


def test_zoo_audit_is_a_subcommand_with_an_out_directory():
    args = cli._parser().parse_args(["audit", str(FIXTURE)])
    assert args.command == "audit"
    assert args.run == str(FIXTURE)
    assert args.out == "audit"
    assert cli._parser().parse_args(["audit", "x", "--out", "elsewhere"]).out == (
        "elsewhere"
    )


def test_the_cli_does_not_import_the_audit_module_to_start(monkeypatch):
    # `zoo --version` and every other subcommand must not need the extra: the
    # bare wheel `make install-check` installs has none of the three libraries.
    for name in ("spanweave", "spanweave_live", "agentgolden"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, "spanweave_zoo.audit", raising=False)
    assert cli.main(["verify", str(FIXTURE)]) == 0
    assert "spanweave_zoo.audit" not in sys.modules


def test_without_the_extra_zoo_audit_refuses_and_names_it(
    monkeypatch, tmp_path, capsys
):
    # `None` in `sys.modules` makes `import spanweave` raise ImportError, which
    # is exactly what a checkout synced with `--extra dev` alone does.
    for name in ("spanweave", "spanweave_live", "agentgolden"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, "spanweave_zoo.audit", raising=False)
    # And the package's attribute, which an earlier import in this process
    # bound and a fresh process without the extra never has.
    monkeypatch.delattr(spanweave_zoo, "audit", raising=False)
    out = tmp_path / "audit"
    assert cli.main(["audit", str(FIXTURE), "--out", str(out)]) == 2
    said = capsys.readouterr().err
    assert "uv sync --extra dev --extra audit" in said
    assert not out.exists()


# --- `make audit-check`, watched failing --------------------------------------


def _report(*cases: str) -> str:
    return f"<testsuites><testsuite>{''.join(cases)}</testsuite></testsuites>"


def test_audit_check_fails_on_a_run_that_selected_nothing():
    from tests import audit_check

    [problem] = audit_check.verdict(_report())
    assert audit_check.MARKER in problem


def test_audit_check_fails_on_a_skip_and_passes_a_clean_run():
    from tests import audit_check

    skipped = '<testcase classname="t" name="one"><skipped/></testcase>'
    passed = '<testcase classname="t" name="two"></testcase>'
    assert audit_check.verdict(_report(skipped, passed)) == ["skipped: t::one"]
    assert audit_check.verdict(_report(passed)) == []


def test_every_audit_test_that_needs_the_extra_carries_the_marker():
    # A test that lost the marker would leave the set `audit-check` watches.
    text = (REPO / "tests" / "test_audit_real.py").read_text(encoding="utf-8")
    marks = text.split("pytestmark = [", 1)[1].split("]", 1)[0]
    assert "pytest.mark.needs_audit" in marks


def test_without_the_extra_the_collector_selection_reports_no_skip(tmp_path):
    # f60f69c's `collector` leg: a module-level `importorskip` in
    # test_audit_real.py skipped the whole module at collection, before `-m
    # needs_collector` could deselect it, and `collector-check` -- rightly --
    # fails on any skip in its report. The extra is hidden from a child pytest
    # by shadowing the three packages with ones that refuse to import -- with
    # `ModuleNotFoundError`, what an absent package raises and the only error
    # `pytest.importorskip` turns into a skip, so on f60f69c this goes red by
    # the skip CI saw, not by a collection error (REVIEW-2026-10-12 R-6).
    import subprocess

    from tests import collector_check

    for name in ("spanweave", "spanweave_live", "agentgolden"):
        package = tmp_path / "shadow" / name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            "raise ModuleNotFoundError('hidden: the audit extra is not installed')\n"
        )
    report = tmp_path / "report.xml"
    env = {**__import__("os").environ, "PYTHONPATH": str(tmp_path / "shadow")}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "-m",
            "needs_collector",
            "tests/test_audit_real.py",
            "--junitxml",
            str(report),
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        check=False,
    )
    cases = collector_check.outcomes(report.read_text(encoding="utf-8"))
    assert [c for c in cases if c[1] != "passed"] == []
