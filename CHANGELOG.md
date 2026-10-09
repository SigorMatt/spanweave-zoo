# Changelog

Pre-release. Nothing here is frozen: the CLI, the capture layout and
`MANIFEST.json` all still move. Entries are by batch id (`WORKPLAN.md` §1).

## A0 — the repository skeleton

- `pyproject.toml`: package `spanweave_zoo`, console script `zoo`, Python
  3.11–3.14, **zero runtime dependencies**, the PEP 561 marker shipped. An
  `audit` extra — and only an extra — pins `spanweave` and `spanweave-live` by
  git sha for A5; a `dev` extra carries ruff, mypy and pytest. `uv.lock`
  committed.
- `Makefile` as the source of truth for the gates: `check` (ruff, ruff format,
  `mypy --strict`, pytest, the gate, `zoo verify`), `verify`, `install-check`.
  `zoo verify` is a prerequisite of `check` from the start, because "a capture
  is immutable" is only a claim if something re-checks it on every run
  (`CLAUDE.md` §0.6 rule 2).
- `.github/workflows/ci.yml`: `make check` and `make install-check` on Python
  3.11–3.14 on ubuntu-latest and 3.12 on macos-latest. CI installs
  `--extra dev` and never `--extra audit`: A0 through A4 must work without
  `spanweave` and `spanweave_live` present, and a CI that installed them would
  hide the day that stopped being true.
- `CLAUDE.md`: the operating contract, carrying `WORKPLAN.md` §0.6 as its own
  §0.6 — the eight standing rules, the architecture invariants, the halt
  points.
- `CONTRIBUTING.md`: the batch bar — spec first, a failing test confirmed red
  on the *derived* parent `<sha>^` in a worktree created by absolute path under
  the scratchpad, one named mutation shown caught, one concern per commit, a
  changelog entry, `make check` and `make verify` green, CI green on the tip.
- `SPEC.md` §1 (the zoo parses nothing, fixes nothing, improves nothing) and §2
  (the capture layout on disk). §§3–7 are headings naming what A1–A5 will
  specify, deliberately empty.
- `tests/gates.py` + `tests/test_gates.py`: one gate — no module under
  `spanweave_zoo/` imports `spanweave` or `spanweave_live` except `audit.py`.
  An AST walk, not a grep, so a nested, aliased or `TYPE_CHECKING` import is
  caught too; thirteen planted violations are each watched failing, and each is
  watched passing inside `audit.py`.
- `spanweave_zoo/`: `__init__.py`, `cli.py` and `py.typed`, minimal on purpose.
  `zoo --help`, `zoo --version`, and `zoo verify`, which exits 0 on a tree with
  no captures and **fails** on a capture it cannot yet re-hash rather than
  reporting an unchecked capture as verified — A3 implements the re-hash
  (`SPEC.md` §5).
- `README.md`: what the zoo is, the pre-release warning, the gates, and the
  provenance of the contract and the briefs.
- `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root, byte-identical to the
  documents handed to the pet projects, with their sha256s in `README.md`.
  Both root copies are contract version **1.1**; the pilot project Z4
  (`streaming-concierge`) was built against **1.0**, and the difference is the
  contract's own closing "Changes from 1.0" section. From now on every project
  is started from these bytes.
