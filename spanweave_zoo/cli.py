"""The `zoo` command line.

A0 ships the entry point and `zoo verify` only as far as `make verify` needs it
today: there are no captures yet, and an empty `captures/` tree verifies
cleanly. The subcommands the plan names -- `sink` (A1), `capture` (A2),
`replay` (A4), `audit` (A5) -- are not here and are not stubbed; `SPEC.md`
§§3-7 are the headings they will fill.

`verify` refuses rather than reassures. Re-hashing a capture against its
`MANIFEST.json` is specified in `SPEC.md` §5 and implemented by A3, so until
then a capture found on disk makes this command exit non-zero saying exactly
that. Reporting an unchecked capture as verified would be the one failure mode
the command exists to prevent.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from spanweave_zoo import __version__

# `captures/<project>/<run-id>/` -- `SPEC.md` §2. A run directory is what
# `verify` counts; the project level carries nothing of its own.
CAPTURES = Path("captures")
_RUN_DEPTH = 2


def _run_directories(root: Path) -> list[Path]:
    """Every `<project>/<run-id>` directory under `root`, in sorted order."""
    if not root.is_dir():
        return []
    runs = [
        path
        for path in root.glob("/".join(["*"] * _RUN_DEPTH))
        if path.is_dir() and not path.name.startswith(".")
    ]
    return sorted(runs)


def verify(root: Path) -> int:
    """Re-hash every capture under `root`. Returns a process exit status."""
    runs = _run_directories(root)
    if not runs:
        print(f"zoo verify: no captures under {root}/ -- nothing to re-hash")
        return 0
    print(f"zoo verify: {len(runs)} capture(s) under {root}/:")
    for run in runs:
        print(f"  {run}")
    print(
        "zoo verify: re-hashing a capture against its MANIFEST.json is "
        "SPEC.md section 5 and is implemented by batch A3. Refusing to report "
        "these captures as verified."
    )
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zoo",
        description=(
            "Record what real OTLP exporters send, byte for byte. "
            "Pre-release: nothing here is frozen."
        ),
    )
    parser.add_argument("--version", action="version", version=f"zoo {__version__}")
    subcommands = parser.add_subparsers(dest="command")
    verify_parser = subcommands.add_parser(
        "verify",
        help="re-hash every capture against its manifest",
    )
    verify_parser.add_argument(
        "path",
        nargs="?",
        default=str(CAPTURES),
        help=f"capture root to verify (default: {CAPTURES}/)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        return verify(Path(args.path))
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
