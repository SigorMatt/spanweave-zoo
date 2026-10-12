## A0 — d33059e (skeleton, on main)

Reviewed read-only from a detached worktree at
`/tmp/claude-1000/-home-msi-git-spanweave/db8f7f20-b229-460c-afff-06719260f7b2/scratchpad/wt-a0`
(absolute, under the scratchpad, outside the repo). The main working tree was
never touched: `git -C /home/msi/git/spanweave-zoo status --short` is empty and
HEAD is still `zoo`. Derived parent confirmed: `git rev-parse d33059e^` =
`998f1cd`, whose whole tree is `WORKPLAN.md` and nothing else — so the
"new test fails on the parent" check is genuinely degenerate and the mutations
below are what carry the bar.

### Passed checks

- **Spec in the same commit.** `SPEC.md` is created by d33059e with §1
  (`§1.1` parses nothing, `§1.2` fixes nothing, `§1.3` improves nothing, `§1.4`
  what follows) and §2 (the capture layout) fully written, and §§3–7 as empty
  headings naming A1–A5. Both match the A0 row verbatim, including the layout
  `captures/<project>/<run-id>/raw/NNNN.body` + `NNNN.headers.json`,
  `json/NNNN.json`, `MANIFEST.json` (SPEC.md:69–80). **Verified.**
- **One concern.** All 20 paths in the commit are the skeleton; `WORKPLAN.md`
  is *not* among them (the batch brief forbids editing it) and no later batch's
  behaviour is smuggled in — `spanweave_zoo/` is exactly `__init__.py`,
  `cli.py`, `py.typed`. **Verified.** The only forward references are inert:
  `.gitignore` lines 11–14 ignore A2's Collector binary and `pyproject.toml:87`
  includes `/collector` in the sdist. Neither is behaviour. **Not a finding.**
- **Determinism / purity under `spanweave_zoo/` (CLAUDE.md "Architecture
  invariants", §0.6).** `grep -rnE
  "time\.time|datetime|\.now\(|random|socket|requests|httpx|urllib|hash\(|pickle|yaml\.load|eval\(|exec\(|subprocess|__import__"
  spanweave_zoo/` → **no hits**. The package reads no clock, draws no random
  number, binds no socket, and imports nothing from the network or unsafe
  deserialization. Ordering in `cli.py:40` is an explicit `sorted()`, not glob
  order. **Verified.**
- **The gate the row promised exists and bites.** `tests/gates.py:78–101` is an
  AST walk (`ast.walk`, so nested / `try` / `TYPE_CHECKING` imports are seen)
  over `spanweave_zoo/**/*.py`, with `audit.py` the sole exemption;
  `tests/test_gates.py` asserts it against 13 planted violation shapes *and*
  asserts each of the 13 is allowed in `audit.py`, plus a false-positive test
  and a "the gate scanned ≥2 files" tripwire (`test_gates.py:86–88`). Proven by
  mutation below. **Verified.**
- **Row claims, each checked against the commit.** `pyproject.toml:6` name
  `spanweave-zoo`, `:78` package `spanweave_zoo`, `:37` console script
  `zoo = "spanweave_zoo.cli:main"`, `:21–24` classifiers 3.11/3.12/3.13/3.14,
  `:34` `dependencies = []`, `:55–58` the `audit` **extra** carrying
  `spanweave @ …@fec7da27af517ad8b58ae3ec57827916aae60674` and
  `spanweave-live @ …@cddc694b8b2a365434c0d97889f6e303e08a0b6d` — the two shas
  the row names, and nowhere else in the file. `Makefile:7,36,47` has `check`,
  `verify`, `install-check`. `.github/workflows/ci.yml:18–29` is
  ubuntu-latest × 3.11–3.14 plus macos-latest × 3.12, and `:41` syncs
  `--extra dev` only, never `--extra audit`. **All verified.**
- **README sha256s are correct.** Recomputed against the files at d33059e:
  ```
  aeadb64bb5fa31495d63c397200f58a9696a5f47e44d458ec27f035c2ae302b4  EXPORT-CONTRACT.md
  c82487fd275d1a0d365ff43134f03ff527e201091a39154f336bd01548095a70  ZOO-BRIEFS.md
  ```
  byte-for-byte what `README.md:64–65` states (and equal to the git blob
  hashes, so no checkout filter is in play). **Verified.**
- **`uv.lock` is honoured, so the gate run is reproducible.** `uv sync --extra
  dev` installed mypy 2.4.0, pytest 9.1.1, ruff 0.17.0 — exactly the pins at
  `uv.lock:208,313,329`, not a fresh resolution of the `>=` ranges in the `dev`
  extra. **Verified.**
- **No test skips on what happens to be installed** (CONTRIBUTING bar). 35
  passed, 0 skipped, with the `audit` extra absent. **Verified.**
- **Degenerate cases covered.** `tests/test_cli.py:20,27,33` cover an absent
  capture root, an empty one, and a capture that cannot be re-hashed.
  **Verified.**
- **CI green on d33059e.** `gh run list --json headSha,conclusion` shows two
  `"conclusion":"success"` CI runs for `d33059e…` (the `main` push and the
  `zoo` push). **Verified**, matching the WORKPLAN §4 note.

### `make check` and `make install-check`

Both green at d33059e in the worktree:

```
uv run ruff check .            -> All checks passed!
uv run ruff format --check .   -> 7 files already formatted
uv run mypy --strict spanweave_zoo -> Success: no issues found in 2 source files
uv run pytest                  -> 35 passed in 0.09s
uv run pytest tests/test_gates.py -v -> 30 passed in 0.04s
uv run zoo verify              -> zoo verify: no captures under captures/ -- nothing to re-hash
uv run zoo --version           -> zoo 0.0.1
EXIT=0
```

```
make install-check -> install-check: OK -- what ships works
  wheel ships 7 entries, library only
  imported /tmp/zoo-install-check-96mia4pn/venv/lib/python3.14/site-packages/spanweave_zoo/__init__.py
EXIT=0
```

No port contention was hit — A0 binds nothing (that is A1's sink), so none of
ports 4317–4320 were touched by this review.

### Mutations shown caught

**M1 — the gate the row promised (the one the brief asked for).** Added
`import spanweave  # MUTATION` to `spanweave_zoo/cli.py` after line 19, so a
module under `spanweave_zoo/` that is not `audit.py` imports `spanweave`:

```
$ uv run pytest tests/test_gates.py -q
............................F.                                           [100%]
_________________ test_the_package_imports_neither_analyser ___________________
    def test_the_package_imports_neither_analyser():
        found = gates.check_package()
>       assert found == [], "\n".join(str(v) for v in found)
E       AssertionError: spanweave_zoo/cli.py:21: [no-analyser-imports] imports 'spanweave'; only audit.py may consume the libraries the zoo captures for (CLAUDE.md section 0.6)
tests/test_gates.py:83: AssertionError
1 failed, 29 passed in 0.06s
```

Reverted; 30 passed again. The gate is real and names the file and the line.

**M2 — the behaviour A0 actually added (honest refusal).** `cli.py:57`
`return 1` → `return 0`, i.e. `zoo verify` reports a capture it cannot re-hash
as verified:

```
$ uv run pytest tests/test_cli.py -q
>       assert cli.verify(tmp_path / "captures") == 1
E       AssertionError: assert 0 == 1
tests/test_cli.py:38: AssertionError
1 failed, 4 passed in 0.03s
```

**M3 — the console script.** `pyproject.toml:37`
`zoo = "spanweave_zoo.cli:main"` → `:run`:

```
$ make install-check
ImportError: cannot import name 'run' from 'spanweave_zoo.cli' (…/site-packages/spanweave_zoo/cli.py)
FAILED (1): /tmp/zoo-install-check-frojw99z/venv/bin/zoo --help
make: *** [Makefile:48: install-check] Error 1
```

All three reverted; `git status --short` in the worktree is empty.

### Findings

**F1 — `README.md:80` claims the sha256s are "how that is checked", and
nothing checks them.** `README.md:79–81`: "For every project started from now
on, these two files are byte-identical to the ones handed to the project, and
**the sha256s above are how that is checked**." No test, target or CI step
recomputes them: `grep -rn "aeadb64b\|c82487fd" .` at d33059e hits only
`README.md:64–65`. `CONTRIBUTING.md:76–80` makes it a human discipline ("the
root copies then move with their hashes … in one commit"). So the two
documents whose byte-for-byte identity is the repository's provenance claim can
drift from their stated hashes with every gate green. The fix is a few lines in
`tests/` that re-hash both files and compare to the block parsed out of
`README.md` — the same shape as the README-is-test-gated discipline used in the
sibling repo. → `next batch`

**F2 — the gate's exemption is by basename anywhere under the package, not
"at the package root" as its own comment says.** `tests/gates.py:36–39` reads
"The one exemption, **by file name at the package root** (`SPEC.md` §7)", but
`no_analyser_imports` (gates.py:80) tests `pathlib.PurePath(path).name in
EXEMPT_FILES`, which ignores the directory. Probed in the worktree:

```
spanweave_zoo/audit.py        -> EXEMPT (no violation)
spanweave_zoo/sink/audit.py   -> EXEMPT (no violation)
spanweave_zoo/replay/audit.py -> EXEMPT (no violation)
spanweave_zoo/a/b/audit.py    -> EXEMPT (no violation)
```

`test_the_exemption_is_by_file_not_by_directory` (test_gates.py:53) covers the
*opposite* direction only — it asserts `spanweave_zoo/audit/sink.py` and
`spanweave_zoo/audit_helpers.py` are caught — so this hole is untested and
would not be noticed. No such file exists today, so nothing is violated; it is
a latent hole that A5 could walk into (an `audit/` package with any module
named `audit.py` inside it, or a `sink/audit.py` helper). One line
(`str(PurePath(path)) in ("spanweave_zoo/audit.py",)`) plus one test closes it.
→ `thread`, worth flagging in A5's brief

**F3 — `make check` never type-checks `tests/`, and the pyproject stanza that
exists to permit that is dead config.** `Makefile:15` is
`uv run mypy --strict spanweave_zoo` — 2 source files. So `tests/gates.py`
(the gate's own implementation, fully annotated and frozen-dataclass'd) and
`tests/install_check.py` (133 lines of subprocess harness) are never checked.
Separately, `pyproject.toml:120–122`:

```toml
[[tool.mypy.overrides]]
module = ["tests.*"]
strict = false
```

does not do what it reads as. Under the locked mypy 2.4.0, pointing mypy at
`tests` with that config still produces 11 `no-untyped-def` errors — per-module
`strict = false` does not switch off the globally expanded strict flags:

```
$ uv run mypy tests
tests/test_cli.py:11: error: Function is missing a type annotation  [no-untyped-def]
…
Found 11 errors in 2 files (checked 5 source files)
```

Latent only because nothing invokes it; but the stanza signals an intent the
Makefile does not carry out, and whoever adds `tests` to `make types` later
will find the exemption does not work. → `thread`

**F4 — `README.md:31` calls `zoo verify` "the capture re-hash" when at A0 it
re-hashes nothing.** The "What exists today" table row reads
`` `zoo --help`, `zoo verify` | the entry point, and the capture re-hash ``,
and the paragraph at `README.md:35–38` immediately corrects it ("`zoo verify`
today exits 0 on a tree with no captures and **fails** on a capture it cannot
yet re-hash"), as do `SPEC.md:140` and `cli.py:9–13`. So the overclaim is one
table cell against four honest statements, and WORKPLAN §4 already registers
the A0/A3 gap. Noting it only because the row is the part a reader skims.
→ `thread`

**F5 — `README.md:68` says "Both root copies are contract version 1.1", but
`ZOO-BRIEFS.md` carries no version marker at all.** `grep -n "1\.1"
EXPORT-CONTRACT.md` → lines 3 and 28 (line 3: "Contract version **1.1** (1.0
was given to Z4; the changes are listed at the end)"); `grep -n "1\.1"
ZOO-BRIEFS.md` → **no match**. The briefs are not the contract and have no
contract version, so "both root copies are contract version 1.1" is true of one
file and an unverifiable inference about the other. The substance of the note —
Z4 was built against 1.0, the difference is the contract's own "Changes from
1.0" section (EXPORT-CONTRACT.md:107–113), Z4's own manifest records `1.0` per
the contract's instruction at line 4 — all checks out. → `thread`

**F6 — no `LICENSE` and no `license` field in `pyproject.toml`.** Already
registered by the builder at WORKPLAN §4 (2026-10-09 A0) as awaiting the
maintainer. Recorded here only so the review and the plan agree; the wheel's
metadata carries no licence today. → `thread` (already registered)

**Nit, not a finding.** `gates.no_analyser_imports(path, source, tree)`
(gates.py:78) never uses `source` — the body works off `tree`. Harmless; ruff's
`ARG` rules are not in the `select` list (pyproject.toml:108) so nothing flags
it.

### Deliberate choices I checked and am not calling findings

- `requires-python = ">=3.11"` (pyproject.toml:10) is open-ended while the
  classifiers and the CI matrix stop at 3.14, so 3.15 will install untested.
  The comment at pyproject.toml:18–20 states the reason — "a harness that
  records a stranger's exporter must not narrow the runtime the stranger's app
  happens to run on" — and the alternative (an upper cap) is the worse failure
  for this repository's job. Intentional.
- `make check` runs `tests/test_gates.py` twice (once via `test`, once via
  `gates`). `Makefile:20–24` says so explicitly and gives the reason (a failure
  that names the invariant). Intentional, and the suite is 0.04s.
- `make verify` resolves `captures/` relative to the cwd (`cli.py:27`), so it
  is a repo-root command. `install-check` runs `zoo verify` from a temp dir and
  asserts "nothing to re-hash", which passes by absence rather than by
  checking anything — but that step is testing the console script, not verify,
  and `verify`'s real behaviour is covered in `tests/test_cli.py`.

### Verdict

Nothing in d33059e `blocks run 2`. One item for the `next batch` (F1: the
provenance hashes are claimed to be checked and are not). Four threads (F2–F5)
plus the already-registered licence item (F6). The batch bar is met: spec in
the commit, the gate real and watched failing, three mutations caught, one
concern, `make check` / `make install-check` / CI all green, purity clean.
