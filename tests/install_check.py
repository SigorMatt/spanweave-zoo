"""Prove that what SHIPS works (`make install-check`).

Everything `make check` runs happens under `uv run`, with the source tree on
the path, so every gate it runs answers a question about the *repository*. A
packaging break -- a missing package directory, a console script pointing at a
function that is not there, a `py.typed` marker excluded -- passes every one of
those gates and fails for the first stranger.

So this target builds the sdist and the wheel, installs the wheel into a
throwaway virtualenv, and runs `zoo --help` from a working directory **outside**
the repo -- and *asserts* that it is doing that rather than assuming it: the
interpreter under test reports the file it imported `spanweave_zoo` from, and
this harness checks it is not the source tree.

It installs no extras. The `audit` extra pins `spanweave` and `spanweave_live`
by git sha and is needed by A5 alone; A0 through A4 must work without them, and
this gate is where that stops being a wish.

Deliberately NOT a prerequisite of `make check`: it builds a wheel and a venv,
and `check` is the fast gate a batch must pass. CI runs both.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist"

# What the interpreter under test is asked. Printed as JSON so this harness
# reads facts rather than parsing prose.
PROBE = """
import json, os, sys
import spanweave_zoo
print(json.dumps({
    "cwd": os.getcwd(),
    "file": spanweave_zoo.__file__,
    "version": spanweave_zoo.__version__,
    "marker": os.path.exists(
        os.path.join(os.path.dirname(spanweave_zoo.__file__), "py.typed")
    ),
}))
"""


def run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print(f"  $ {' '.join(str(a) for a in args)}   (in {cwd})")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"FAILED ({result.returncode}): {' '.join(map(str, args))}")
    return result


def build() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    run(["uv", "build"], cwd=REPO)
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    assert len(sdists) == 1, f"expected one sdist, got {sdists}"
    return wheels[0]


def audit_wheel(wheel: Path) -> None:
    """The wheel ships the package, the marker, and nothing else."""
    names = zipfile.ZipFile(wheel).namelist()
    assert "spanweave_zoo/__init__.py" in names, names
    assert "spanweave_zoo/py.typed" in names, (
        "wheel is missing the PEP 561 marker: a consumer's mypy --strict "
        f"would refuse to read the package. Entries: {names}"
    )
    for forbidden in ("tests/", "captures/", "collector/"):
        leaked = [n for n in names if n.startswith(forbidden)]
        assert not leaked, f"wheel ships {forbidden}: {leaked}"
    print(f"  wheel ships {len(names)} entries, library only")


def install_and_run(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="zoo-install-check-") as tmp:
        outside = Path(tmp).resolve()
        assert REPO not in outside.parents and outside != REPO, (
            f"the working directory under test is inside the repo: {outside}"
        )
        venv = outside / "venv"
        run(["uv", "venv", str(venv)], cwd=outside)
        python = venv / "bin" / "python"
        run(
            ["uv", "pip", "install", "--python", str(python), str(wheel)],
            cwd=outside,
        )

        # The console script, from outside the repo: what a stranger types.
        helped = run([str(venv / "bin" / "zoo"), "--help"], cwd=outside)
        for subcommand in ("sink", "capture", "verify"):
            assert subcommand in helped.stdout, helped.stdout
        versioned = run([str(venv / "bin" / "zoo"), "--version"], cwd=outside)
        print(f"  zoo --version -> {versioned.stdout.strip()}")

        # `zoo verify` on a directory that has no captures: exit 0, cleanly.
        verified = run([str(venv / "bin" / "zoo"), "verify"], cwd=outside)
        assert "nothing to re-hash" in verified.stdout, verified.stdout

        # `kind` is required in what SHIPS, not only in the source tree
        # (`SPEC.md` §5.2): a capture the audit cannot tell apart from a
        # recorded one is the failure this declaration exists to prevent, and
        # the console script is where an operator meets it.
        undeclared = subprocess.run(
            [
                str(venv / "bin" / "zoo"),
                "capture",
                "--project",
                "z4",
                "--run-id",
                "install-check",
            ],
            cwd=outside,
            capture_output=True,
            text=True,
        )
        assert undeclared.returncode != 0, undeclared.stdout
        assert "--kind" in undeclared.stderr, undeclared.stderr
        assert "--project-manifest" in undeclared.stderr, undeclared.stderr
        print("  zoo capture with no --kind -> refused")

        # `collector/` is repository data and is NOT in the wheel (above), so
        # the installed `zoo capture` has no pin to read. It must say so and
        # exit non-zero rather than start a capture it cannot label
        # (`SPEC.md` §4.6) -- the shipped artifact's honest refusal, asserted
        # where it actually ships.
        project_manifest = outside / "MANIFEST.json"
        project_manifest.write_text('{"contract_version": "1.1"}', encoding="utf-8")
        refused = subprocess.run(
            [
                str(venv / "bin" / "zoo"),
                "capture",
                "--project",
                "z4",
                "--run-id",
                "install-check",
                "--kind",
                "recorded",
                "--project-manifest",
                str(project_manifest),
            ],
            cwd=outside,
            capture_output=True,
            text=True,
        )
        assert refused.returncode != 0, refused.stdout
        assert "VERSION" in refused.stderr, refused.stderr
        assert not (outside / "captures").exists(), "the refusal still wrote something"
        print("  zoo capture with no collector/ -> refused, wrote nothing")

        probed = run([str(python), "-c", PROBE], cwd=outside)
        facts = json.loads(probed.stdout)
        assert facts["cwd"] == str(outside), facts
        imported = Path(facts["file"]).resolve()
        assert REPO not in imported.parents, (
            f"imported spanweave_zoo from the source tree: {imported}"
        )
        assert facts["marker"], "installed distribution carries no py.typed"
        print(f"  imported {imported}")
        print(f"  version  {facts['version']}")


def main() -> int:
    print("install-check: build, install, run from outside the repo")
    wheel = build()
    audit_wheel(wheel)
    install_and_run(wheel)
    print("install-check: OK -- what ships works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
