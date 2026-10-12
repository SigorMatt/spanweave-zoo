# Run-2 cold review: section `plan` (the seven `plan:` commits since 34c4369)

Reviewer: aux, read-only (WORKPLAN.md §0.1 step 5, §0.2). The tree was clean before and after.
The only file written is this one (gitignored under `patches/`).
Method: `git show --stat`, `--word-diff` of each plan commit, `git show <sha>:<path>` at each
code sha, `gh run list/view`, `gh api .../jobs/<id>`, `gh api .../activity`, `gh cache list`,
`git ls-remote origin`, `git reflog origin/zoo`. No worktree was created and no port was bound
(so the A3c/A4 mutations were checked by reading the code and by a stdlib call, not by running the tests).

## 1. Per-commit checks

| plan commit | batch | stat | subject | status sha = `<plan>^` | on origin/zoo | §4 claims |
|---|---|---|---|---|---|---|
| 957149d | A3a | WORKPLAN.md only, +20/-5 | ok (1 clause) | 2b3c499 = 957149d^ | yes | ok; §0.3 edit is a remit question (P-5) |
| 23d1ddb | A3b | WORKPLAN.md only, +25/-4 | ok | 810f2db = 23d1ddb^ | yes | ok |
| 01cfb7e | A3c | WORKPLAN.md only, +21/-4 | ok | 8af242d = 01cfb7e^ | yes | ok by inspection; evidence not in the code commit (P-6) |
| 1c39f09 | A3d | WORKPLAN.md only, +27/-3 | ok | 52c33ba = 1c39f09^ | yes | ok, one overclaim (P-8); row not corrected (P-4); evidence not in the code commit (P-6) |
| 8cb6d7d | A0a | WORKPLAN.md only, +32/-3 | ok (1 clause, bookkeeping) | 91e91af = 8cb6d7d^ | yes | ok except how it describes T18 (P-3) |
| 5006d7d | A0b | WORKPLAN.md only, +23/-3 | ok | 222825f = 5006d7d^ | yes | numbers ok; job name wrong (P-1); row not corrected (P-4) |
| 040b194 | A4 + run 2 | WORKPLAN.md only, +26/-4 | **2 extra clauses** (P-2) | 0c1e538 = 040b194^ | yes (= origin/zoo tip) | ok, with wording issues (P-7, P-9); evidence not in the code commit (P-6) |

Every status went `todo` → `done (<sha>)`, and each sha is the plan commit's direct parent. Every
plan commit also moves the next row from `awaiting <X>` to `todo`. 5006d7d moves A4 from
`awaiting A3` to `todo`, which is right. All seven have the same trailers
(`Co-Authored-By: Claude Opus 5`, `Claude-Session: …session_01V1AH6U…`), the same author, and a
body that names the batch, the sha and what §4 records.

Timing: every plan commit was made after CI on its code commit had finished green. For example,
CI on 2b3c499 ended at 00:00:48Z and 957149d is at 00:02:16Z; CI on 0c1e538 ended at 01:50:37Z and
040b194 is at 01:51:37Z. So §2's "CI green on the pushed tip before `done`" held for every batch.

## 2. Claims checked against git and the code

### 957149d (A3a)
- No `make conformance` target exists at 34c4369, 2b3c499 or 040b194 (`grep conformance Makefile`
  finds nothing). The phrase entered WORKPLAN.md in 998f1cd and was removed from §0.3 here. It now
  appears only in the §4 line itself. **ok**
- `collector/config.yaml` `service.telemetry.logs.level` goes `warn` → `info` in 2b3c499, with a
  comment giving the ready-line reason. **ok**
- "stand-in child process … run in CI": the 2b3c499 body says so (SPEC §4.9). **ok**
- "`problems` written, `zoo verify` does not yet read it … SPEC §4.6 says so": SPEC.md@2b3c499
  line 615, inside §4.6 (lines 545–662), says "verify reads `problems` in A3b". **ok**
- A3b's row already said "or any `problems`" at 34c4369, so it needed no change. **ok**

### 23d1ddb (A3b)
- The 810f2db body says, verbatim: "this commit: first 100 273 us/body last 100 288 us/body ratio
  1.05 / on 957149d: first 100 572 us/body last 100 4258 us/body ratio 7.44". The §4 numbers match.
  "On the parent" is right: 957149d is 810f2db's derived parent. Arithmetic: 288/273 = 1.055 and
  4258/572 = 7.44. **ok**
- The `files` key: `manifest.FILES = "files"` at 810f2db, re-hashed alongside `bodies`. **ok**
- `zoo sink` writes no manifest during a run: `run_sink` calls `manifest.finish(...)` in its
  `finally` (cli.py@810f2db). A capture without `ended_at` fails verify: SPEC §5.6 at line 991. **ok**
- "SPEC §5.3's four-outcome table": SPEC.md@810f2db line 883, "Four outcomes:", inside §5.3. **ok**

### 01cfb7e (A3c)
- The head is kept by a wrapper on the request stream as `readline` reads it, and written before
  the parse: sink.py@8af242d `_Head`, `setup()` wraps `rfile`, and `parse_request` calls
  `self._stream.end()`. **ok**
- `Recorder.record(..., head: bytes, ...)` is required. The startup refusal globs `HEADERS_GLOB` and
  reports "`N` headers file(s)". **ok**
- Mutation "caught only by the bare-CR test": the test's `HEAD` is a canonical head (`Name: value`,
  single space, CRLF). A head rebuilt from `self.headers` is therefore byte-identical to it, and
  the octet-identity test cannot fail under the mutation. Only `BARE_CR_HEAD` differs. **ok by
  inspection.** Not reproduced, because the tests bind ports.
- "a bare CR early in a head makes the stdlib drop every later header, `Content-Length` included":
  confirmed with `http.client.parse_headers` on
  `Host: x\r\nX-W: a\rb\r\nContent-Length: 5\r\n…`, which gives `[('Host','x'),('X-W','a')]`. **ok**
- The mutation and parent-run evidence appear **nowhere** in 8af242d (body or CHANGELOG). See P-6.

### 1c39f09 (A3d)
- `cli.verify(root: Path, *, named: bool = False)` exists at 52c33ba. The CI log for 38011882707
  shows `zoo verify` (no captures, exit 0), then `zoo verify tests/fixtures/capture` ("1
  capture(s) … 2 body/bodies, 0 problem(s)"), then install-check's out-of-repo `zoo verify`. **ok**
- `.gitattributes`: `tests/fixtures/capture/** -text`. **ok**, but "would be corrupted by
  checkout" overclaims (P-8).
- `EXEMPT_FILES = ("audit.py",)` at 01cfb7e became `EXEMPT_PATHS = ("spanweave_zoo/audit.py",)` at
  52c33ba, matched with `PurePath(path).as_posix()`. **ok**
- No generator script: nothing in `git ls-tree 52c33ba` outside `tests/fixtures/` produces the
  fixture. The provenance is in `tests/test_fixture_capture.py`'s docstring and SPEC §5.6
  (lines 1089–1100). **ok**. The docstring gives the method (`tests/otlp.py` → tee → Collector) but
  no date, collector version or command line.
- "three of four concerns red on the parent; drift test shown red by one byte": not in 52c33ba's
  body or CHANGELOG (P-6). `tests/test_readme.py` is new in 52c33ba, so "passes on the parent"
  means the new test was run against the parent tree, which is fine.

### 8cb6d7d (A0a)
- 91e91af: `LICENSE` MIT with the same holder line as `spanweave/LICENSE` and
  `spanweave-live/LICENSE`; `license = "MIT"` and `license-files = ["LICENSE"]` are in
  pyproject.toml; `install_check.py` asserts `.dist-info/licenses/LICENSE` is in the wheel;
  `test_readme.py` calls `cli._parser().parse_args`; the README's tee command was missing
  `--kind` and `--project-manifest` (91e91af body, F3); `OPEN_QUESTIONS.md` has §1 (manifest
  timing), §2 (licence) and §3 (the `started_at` corollary). **ok**
- **A2 CI line**, "success on all five legs": run 37989769269 (8c8299f, push) has
  check (ubuntu-latest, 3.11/3.12/3.13/3.14) all success and check (macos-latest, 3.12)
  success. **ok**
- **Force-push `c965c9b` → `9074ecd`**: the GitHub activity API for `refs/heads/zoo` shows
  `2026-10-09T21:15:11Z force_push c965c9b->9074ecd`. Both shas have a green CI run (37992144806,
  37992296368). **ok**
- **`b913e2b` subject**: "plan: A3 done, run 1 complete, and the project manifest's timing is
  open". The quote is right, but the framing is not (P-3).

### 5006d7d (A0b)
- 18 s: in run 38013640820 (222825f), job `collector` ran 01:33:38–01:33:56. **ok**
- 15 s: run 38013503089 is head 7dc4cb6 on `claude/a0b-trial` (parent 8cb6d7d), with `collector`
  at 01:31:29–01:31:44. **ok**. "Identical content": `git diff 7dc4cb6 222825f` touches only
  CHANGELOG.md, where `DURATION_PLACEHOLDER` became the 15 s line. The code is identical, so the
  claim holds in substance.
- "cold 4 s fetch": the `Run make collector` step took 01:33:44–01:33:48. The archive cache is now
  under `refs/heads/zoo` (`gh cache list`: `otelcol-…linux_amd64.tar.gz-fcc0637…`, ref
  `refs/heads/zoo`). No trial-branch cache remains. **ok**
- Log line: `collector-check: OK -- 3 tests ran against the real Collector, none skipped`. **ok**
- Branch deleted: `git ls-remote origin` shows only `HEAD`, `refs/heads/main` (d33059e) and
  `refs/heads/zoo` (040b194). **ok**
- No force-push: the activity API shows only `push` events after 21:15:11Z. **ok**
- **The job's name is `collector`, not `collector (ubuntu-latest)`** (P-1).

### 040b194 (A4 + run 2)
- 0c1e538: replay.py takes the head from `NNNN.headers.raw` (`body.stem + HEADERS_RAW_SUFFIX`),
  sends through `forward.HttpForward`, and orders by `manifest.recorded_bodies` (the journal
  order). The `otel\rpython/1.0` case is in tests/test_replay.py:508/517. Truncation to `otel` is
  confirmed with `http.client.parse_headers`. **ok**
- "seven batches, seven commits": 2b3c499, 810f2db, 8af242d, 52c33ba, 91e91af, 222825f, 0c1e538.
  **ok**
- "CI green on every pushed tip (six legs from A0b on)": see §3. All 14 pushed shas
  2b3c499..040b194 are push-event runs, all `success`, 5 jobs each through 8cb6d7d and 6 from
  222825f. **ok**, with P-7.
- "no force-push": activity API and reflog both show append-only pushes 34c4369 → … → 040b194.
  **ok**

## 3. CI per pushed sha (push events, branch zoo)

| sha | run | conclusion | jobs |
|---|---|---|---|
| 2b3c499 | 38007052719 | success | 5/5 check legs success |
| 957149d | 38007272551 | success | 5/5 |
| 810f2db | 38010029875 | success | 5/5 |
| 23d1ddb | 38010187854 | success | 5/5 |
| 8af242d | 38010993899 | success | 5/5 |
| 01cfb7e | 38011227124 | success | 5/5 |
| 52c33ba | 38011882707 | success | 5/5 |
| 1c39f09 | 38012022798 | success | 5/5 |
| 91e91af | 38012660536 | success | 5/5 |
| 8cb6d7d | 38012808308 | success | 5/5 |
| 222825f | 38013640820 | success | 6/6 (collector 18 s) |
| 5006d7d | 38013819446 | success | 6/6 |
| 0c1e538 | 38014662495 | success | 6/6 |
| 040b194 | 38014798470 | success | 6/6 |

All jobs for 040b194 (run 38014798470): `collector` success; `check (ubuntu-latest, 3.11)`
success; `check (ubuntu-latest, 3.12)` success; `check (ubuntu-latest, 3.13)` success;
`check (ubuntu-latest, 3.14)` success; `check (macos-latest, 3.12)` success.

## 4. Findings

- **P-1: the sixth job's name is recorded wrongly in three places.** The A0b row, the §3 CI (T25)
  decision and the 5006d7d §4 line all call it `collector (ubuntu-latest)`. CHANGELOG@222825f does
  too. ci.yml@222825f has `collector:` with no `name:`, so GitHub reports the check as
  `collector`, which every `gh run view` above shows. The §4 line is a factual claim that does not
  match the record, and anyone who greps the checks or sets branch protection by that name will
  miss the job. **Bin: next batch.** Fix with a one-line plan/CHANGELOG correction, or add
  `name: collector (ubuntu-latest)` to ci.yml in a code commit.
- **P-2: 040b194's subject breaks the clause rule that T18 already flagged.** The subject is
  "plan: A4 done and run 2 complete, with A3c's distinction paying for itself": two clauses after
  the batch id, where §0.1 step 5 allows one. The second is commentary, not "something a reader
  needs". It has the same shape T18 found in b913e2b, and it was made one run after that finding.
  **Bin: thread.** No rewrite: the branch is never force-pushed. Record it at close.
- **P-3: 8cb6d7d's §4 line on `b913e2b` turns T18 from a break into an allowance.** T18
  (REVIEW-2026-10-10.md:335) reads "`b913e2b`'s subject carries **two** clauses after the batch id
  where §0.1 step 5 allows one. The only form break in the four." The §4 line instead says step 5
  "allows a second clause … and the open question was that; T18 registered it so the allowance is
  visible". Counted by step 5's own wording ("a second clause after the batch id"), b913e2b has
  the batch clause plus two more, so it exceeds the allowance. **Bin: thread.** Reword at fold
  time so TASKS.md does not inherit the gloss.
- **P-4: two rows the batches showed wrong were explained in §4 but never corrected.** Step 5 says
  "correct the row in the same edit". 1c39f09 leaves A3d's "Tests red on the parent for each"
  unchanged, though §4 says one of the four concerns cannot be red on the parent. 5006d7d leaves
  A0b's "Say in the body how long the job takes" unchanged, though §4 says a body cannot hold that
  measurement, and also leaves the wrong job name (P-1). The A3a case is handled (§0.3 corrected).
  The A3c row's mutation sentence is accurate as written. **Bin: next batch** (plan-only edit). It
  matters because A6 folds rows into TASKS.md.
- **P-5: 957149d edited the §0.3 brief, which is outside step 5's literal remit, and left the
  brief's halt list stale.** Step 5 lets a plan commit correct a *row's* acceptance number or
  premise. §0.3 is protocol. The correction (`make conformance` → `make install-check`) is factually
  right and is disclosed in the subject, body and §4, but no §3 decision ratifies it. The same
  brief still says "a change in spanweave itself, a dialect read outside spanweave's adapters",
  text inherited from the spanweave repo. That does not match CLAUDE.md's halt points:
  spanweave_live, a runtime dependency, the pinned shas, parsing a payload, editing a capture.
  **Bin: thread.** The maintainer should ratify protocol edits in §3 and reconcile the brief's
  halt list with CLAUDE.md before run 3.
- **P-6: the plan is the only tracked record of three batches' mutation and parent-run
  evidence.** 01cfb7e (A3c: the mutation is caught only by the bare-CR test), 1c39f09 (A3d: three
  of four red on the parent; the drift test shown red by one appended byte) and 040b194 (A4: the
  `.headers.json` mutant sends a tidied head and exits 0) state evidence that appears in no code
  commit. 8af242d, 52c33ba and 0c1e538 have no mutation or parent-run text in their bodies or
  CHANGELOG entries, unlike 2b3c499, 810f2db, 91e91af and 222825f. The builder copied it from
  sub-agent reports that are not archived, and WORKPLAN.md is deleted at close. The A3c claim
  checks out by inspection (canonical `HEAD`), and the stdlib truncation was confirmed directly.
  **Bin: next batch**, to be joined with the code-commit sections' CONTRIBUTING-bar findings for
  those three shas. From the plan side, step 4 checks the report and not the commit body.
- **P-7: 040b194 claims "CI green on every pushed tip" before its own CI had run.** It is true
  after the fact (38014798470 success at 01:52:50Z), but at commit time the claim covered a tip
  that could not yet have been checked. This is the self-measurement shape the A0b §4 line itself
  warns about. **Bin: thread.**
- **P-8: 1c39f09 overclaims on `.gitattributes`.** It says "without it the record would be
  corrupted by checkout". A default checkout on Linux or macOS converts nothing. Corruption needs
  `core.autocrlf`/`eol` settings (the Windows default) or a `text=auto` attribute, which this repo
  does not have. The guard is right; the sentence should say "could be". **Bin: thread.**
- **P-9: two wording slips in 040b194's A4 lines.** "Socket-level sends therefore live in tests …
  and the import gate stays green": the only gate, `tests/gates.py` `no_analyser_imports`, checks
  spanweave/spanweave_live imports and has no bearing on where sockets live. "The committed fixture
  capture holds **one** body" is true per side, but `zoo verify` reports it as "2 body/bodies"
  (raw and json). "One request" would be exact. **Bin: thread.**
- **P-10: T19 is still unreconciled at 040b194, and the header drops one §2 step.** §0.1 step 8
  still reads as a single push per run, while §2 says "Every batch: CI green on the pushed tip
  before `done`". Run 2 followed §2 with 14 pushes, one per commit. The "Last updated" line is
  otherwise consistent with §1 and §2: runs 1–2 done, next the aux review then the Z4 captures,
  run 3 = A5 → A6, A5 `awaiting captures`. It omits §2's "decisions" step between the review and
  the captures. **Bin: thread** (T19 is already registered).

Nothing here blocks the Z4 capture.

## 5. Tree state

`git status --short` in /home/msi/git/spanweave-zoo was empty before and after this review.
This file is ignored by `.gitignore:12: patches/`.
