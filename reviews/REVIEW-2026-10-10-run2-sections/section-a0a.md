# Section a0a — cold review of 91e91af (A0a)

Commit: `91e91af docs: the README's commands run as printed, the licence exists, the question has a home`
Derived parent: `git rev-parse 91e91af^` = `1c39f096a318df9f686dffe51f7395d87f53ab98` (a `plan:` commit, A3d done).
Worktrees: `$SP/wt-a0a-commit` (91e91af) and `$SP/wt-a0a-parent` (1c39f09), with `uv sync --extra dev` in each. Both removed at the end. No port was bound (nothing in this review starts a listener; the operator flow was not run).

## 1. Spec rule / "docs only"

- `git show --stat 91e91af`: CHANGELOG.md, LICENSE, OPEN_QUESTIONS.md, README.md, pyproject.toml, tests/install_check.py, tests/test_packaging.py, tests/test_readme.py. **Nothing under `spanweave_zoo/`, SPEC.md untouched.**
- pyproject changes: `license = "MIT"`, `license-files = ["LICENSE"]`, classifier `License :: OSI Approved :: MIT License`, sdist include `/LICENSE`. The shipped artifact changes (wheel gains `dist-info/licenses/LICENSE`; METADATA gains `License-Expression: MIT`, `License-File: LICENSE`, the classifier; sdist gains `LICENSE`), but no runtime behaviour does. SPEC.md does not describe packaging (only `grep licen|wheel|install-check|pyproject` hit is line 83, the audit pin), so the spec rule does not apply. The body says "Documentation only" and then describes the packaging change in its T5 bullet, so the label is a bit loose but discloses what changed. **Result: accurate enough, spec rule not triggered.**
- CHANGELOG entry present (`## A0a — the README is true, ...`).

## 2. Parent run (tests copied from 91e91af into the 1c39f09 worktree)

`uv run pytest tests/test_readme.py tests/test_packaging.py -q` on the parent: **11 failed, 56 passed**. Every failure is a real assertion or the parser's own error. None comes from a collection ImportError. **The parent run is not vacuous.**

| Test | Failure on parent |
|---|---|
| test_every_command_the_readme_prints_is_one_this_test_checks[zoo sink ...], [zoo capture ...], [zoo verify], [zoo verify captures/...] (4) | `assert 'zoo' in frozenset({'make','timeout','uv'})`: no `uv run` prefix |
| test_every_zoo_command_the_readme_prints_parses_as_printed[zoo capture --project z4 --run-id ...] | `argparse.ArgumentError: the following arguments are required: --kind, --project-manifest` (F3, as the body says) |
| test_the_operator_flow_is_numbered_and_starts_with_uv_sync | `the operator flow is not numbered` |
| test_the_readme_waits_on_the_line_the_code_actually_prints | READY_LINE not in README |
| test_the_readme_does_not_count_the_commands_it_prints | `['Five commands', 'five commands']` |
| test_packaging (all 3) | LICENSE FileNotFoundError; `KeyError: 'license'`; README lacks "MIT licensed (`LICENSE`)" |

The body says "ten of the new assertions". The observed count is 11 test ids, because of parametrize expansion. This is cosmetic.

`make install-check` on the parent with the new `tests/install_check.py`: **fails** with `AssertionError: wheel ships no LICENSE ... Entries: [... 12 entries, no licenses/]`.

## 3. Mutations (in the commit worktree, each reverted; `git status --short` empty after each)

| # | Mutation | Result |
|---|---|---|
| M0 (body's) | README:67 delete `--kind recorded` line (tee block) | caught: `test_every_zoo_command_the_readme_prints_parses_as_printed[uv run zoo capture ... --project-manifest ...]`, `argparse.ArgumentError: the following arguments are required: --kind` |
| M1 | README:177 delete `--kind real` (operator step 3) | caught: same test, same error; 1 failed / 82 passed |
| M2 | `**4. In the pet` → `**7. In the pet` | caught: `test_the_operator_flow_is_numbered_and_starts_with_uv_sync`, `the operator flow's steps are [1, 2, 3, 7, 5, 6], not 1..6` |
| M3 | README:235 `make verify` → `make verfy` | caught: `test_every_make_target_the_readme_prints_exists[make verfy]`, `the Makefile has no 'verfy' target` |
| M4 | delete `license = "MIT"` from pyproject | caught: `test_the_package_declares_the_licence_it_ships`, `KeyError: 'license'` |
| M5 | delete `license-files` line | **install-check passes**: the wheel still ships `dist-info/licenses/LICENSE`, because hatchling's default license-files glob picks it up. This is correct, since the wheel does carry it. test_packaging catches the missing declaration (`project["license-files"]`). Not a gap. |
| M6 | `license-files = []` (LICENSE not shipped) | caught by **both**: install-check `AssertionError: wheel ships no LICENSE ...`; test_packaging 1 failed |
| M7 | step 4 `make run-real` → `make run-reel` | caught: `test_every_make_target_the_readme_prints_exists[make run-reel ...]` (exemption is exact-name) |

Gap probes (mutations the tests do **not** catch):

| # | Mutation | Result |
|---|---|---|
| G1 | README:199 grep reads `capture.txt` while line 198 redirects to `capture.log` | **80 passed**. Not caught |
| G2 | README:199 `timeout 30 bash -c` → `timeout bash -c` (real: `timeout: invalid time interval 'bash'`, exit 125) | **80 passed**. Not caught |
| G3 | step 3 fence ` ```bash ` → ` ```sh ` and delete `--kind real` | **76 passed**. The block drops out of extraction silently; the only guard is `len(readme_commands()) >= 8` |
| G4 | prose README:138 `` `make verify` `` → `` `make verfy` `` | 80 passed (inline prose is out of scope by design) |
| G6 | step 4 drop `ENDPOINT=http://localhost:4318` | 80 passed. This is harmless: the Z4 Makefile defaults `ENDPOINT ?= http://localhost:4318` |

## 4. Clock / randomness / network

No file under `spanweave_zoo/` changed. The new tests use `shlex`, `tomllib` and `re`. They open no socket and read no clock. Nothing to judge.

## 5. Form

The subject has `<area>: <one line>` form. The body names A0a and its review items, and says SPEC is untouched. It is one concern, namely the A0a row (README truth, licence, OPEN_QUESTIONS). The area is `docs` while tests and pyproject also changed; given the row this is acceptable.

## 6. make check (commit worktree, no Collector binary)

`make check`: ruff `All checks passed!`, pytest **241 passed, 3 skipped**, gates 31 passed, `zoo verify` on captures/ (none) and tests/fixtures/capture (1 capture, 2 bodies, 0 problems) OK, `zoo 0.0.1`. The body's "244 passed" was with the binary; 241 + 3 skipped = 244, which is consistent.
`make install-check`: `install-check: OK -- what ships works`. `unzip -l dist/*.whl` shows `spanweave_zoo-0.0.1.dist-info/licenses/LICENSE` (1092 bytes), and METADATA has `License-Expression: MIT`, `License-File: LICENSE`, `Classifier: License :: OSI Approved :: MIT License`. The sdist has `spanweave_zoo-0.0.1/LICENSE`.

## 7. Specific claims

**(a) Every printed `zoo` command is parsed by `cli._parser()`: confirmed, with gaps.** `readme_commands()` takes every ` ```bash ` fence (tests/test_readme.py BASH_BLOCK), joins `\`-continuations and strips `#` comments. The README at 91e91af has 11 bash blocks: README:48, 64, 120, 155, 165, 175, 194, 208, 234, 243, 273. All of them are extracted, including the multi-line tee (64-69), step 3 (175-179) and the supervisor block (194-200), whose `zoo capture` argv stops at `>` and parses. The bare fences are Ctrl-C (219), the digests (299) and the layout (323), and they are correctly excluded. Commands the extractor sees but no test checks:
- `timeout 30 bash -c '...'` (README:199). `timeout` is in KNOWN_PROGRAMS, but no test validates that command. The only related check is `test_the_readme_waits_on_the_line_the_code_actually_prints`, which checks the grep pattern's prefix against `capture.READY_LINE`. G1 and G2 show this. The KNOWN_PROGRAMS comment ("each of these is checked below") is false for `timeout`.
- `make run-real ENDPOINT=...` / `make run-recorded` are exempt by exact name. A typo is caught (M7), but the variable is not checked.
- `make verify`, `make check`, `make collector`, `make install-check`, `make collector` (README:166, 235, 274-278) are all checked against Makefile targets. **A broken make target name in a bash block is caught (M3). In prose it is not (G4).**
Not seen at all: any block fenced as anything other than `bash` (G3), and inline prose commands (README:138 `make verify`; README:265 the recorded variant, "`--kind recorded` at step 3 and `make run-recorded` at step 4", which is prose and never parsed as a command).

**(b) Operator flow numbered, `uv sync --extra dev` first, each command complete: confirmed.** README:153-247 at 91e91af has steps **1-6**: uv sync, make collector, zoo capture (`--kind real --project-manifest`), make run-real, Ctrl-C (bare fence, labelled a keystroke), make verify plus `zoo verify <run>`. `git diff 91e91af 040b194 -- README.md` touches only the table and SPEC rows (A4 replay), the collector cache sentence (A0b), a new "The replayer" section with two `zoo replay` bash blocks, and the gates block (`make collector-check`, sixth CI leg). **The operator section (README "Running a pet project's real run") has no drift since 91e91af.** tests/test_readme.py, test_packaging.py, install_check.py, LICENSE and OPEN_QUESTIONS.md are unchanged 91e91af..040b194.

**(c) LICENSE: confirmed.** `diff /home/msi/git/spanweave/LICENSE LICENSE` and `diff /home/msi/git/spanweave-live/LICENSE LICENSE` are both empty, so the file is byte-identical. The holder is `Copyright (c) 2026 MATTHEW SIGURKO (m.sigor@gmail.com)`. Both siblings' pyproject has `license = "MIT"`, `license-files = ["LICENSE"]` and the MIT classifier, and the zoo declares the same three. The built wheel ships `dist-info/licenses/LICENSE` (section 6).

**(d) OPEN_QUESTIONS: confirmed.** §1 (OPEN_QUESTIONS.md:22-65) is the manifest-timing question. Its decision text (:52-60) matches WORKPLAN §3's F4 row clause for clause: copied at the end, after Ctrl-C; absent or started_at-predates gives `project_manifest: null` plus a `problems` entry; `zoo capture` exits non-zero; verify fails on `problems`; "A capture is never silently fine". It adds one consistent clause: the path is still checked at the start, per A3b and SPEC §5.3. §3 (:91-120) registers A3b's undatable-`started_at` corollary (keep the document plus a problem), matching WORKPLAN §4 (WORKPLAN.md:338-345) and the fourth row of SPEC §5.3's four-outcome table at 91e91af.

**(e) No counts left: refuted in one place.** `grep -iE '\b(one|...|ten|\d+)[ -]commands?\b'` over the docs at HEAD finds `WORKPLAN.md:266`, the A2 §4 note (2026-10-09): "A3's five-command README section must be exercised the same way." The A0a §4 note (WORKPLAN.md:399) says "No row or §4 note counts commands any more". The rows are clean. The CHANGELOG hits (:115, :335) are historical entries, which is fine. test_readme guards only README.md, so nothing would catch a count elsewhere.

## Findings

**A0a-1 — the supervisor wait line is printed as runnable and nothing checks it.** `tests/test_readme.py` puts `timeout` in KNOWN_PROGRAMS with the comment "each of these is checked below". No test checks the `timeout 30 bash -c 'until grep -q ... capture.log; ...'` command at README:199 beyond its grep pattern's prefix. A log-name mismatch between the redirect (README:198) and the grep (G1), or a malformed `timeout` (G2, which really exits 125), passes all 80 README tests. Such a mismatch would make the supervisor wait the full 30 s and exit 124 while the capture is in fact ready. The printed line is correct today, so the operator is not misled now. Proposed bin: **next batch** (assert that the redirect target equals the grep's file and that `timeout`'s first argument is a duration; or say plainly that `timeout` is held only by the READY_LINE test).

**A0a-2 — extraction is keyed on the ` ```bash ` fence label alone.** A command block fenced ` ```sh `, ` ```shell `, ` ```console ` or bare drops out of every check silently (G3: delete `--kind real` and relabel the fence, and all 76 remaining tests pass). The only backstop is `len(readme_commands()) >= 8`. Inline prose commands such as README:138 and the recorded variant at README:265 are also unchecked. All fences at 91e91af and HEAD are `bash` or deliberately bare, so nothing is wrong today. Proposed bin: **thread** (for example, fail on any fence label other than `bash` or empty, or count the bare fences explicitly).

**A0a-3 — one command count survives in WORKPLAN §4.** `WORKPLAN.md:266` (the A2 note) still says "A3's five-command README section", contradicting the A0a note's "No row or §4 note counts commands any more" (WORKPLAN.md:399) and the row's "the row and §4 stop counting". It is a historical note, and the plan is the builder's to edit. Proposed bin: **thread** (builder rewords it or qualifies the A0a note).

**A0a-4 — step 2's digest wording (pre-existing, not introduced by A0a).** README:169 says `make collector` "checks its sha256 against the release's own digest". `collector/fetch.py:12` checks against the checked-in `collector/SHA256SUMS`, which is what README:86-88 says. The wording dates from 1c39f09 (README:175 there). Proposed bin: **thread**.

Nothing found that blocks the Z4 capture.

Cleanup: both a0a worktrees removed, `git worktree prune` run. Other reviewers' worktrees were left alone.
