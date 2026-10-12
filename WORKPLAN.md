# WORKPLAN.md — spanweave-zoo, series 2: the hardening series, and the five audits

Status file for the zoo's second series. Series 1 (`TASKS.md`) built the
capture side and audited Z4; this series closes what two reviews of its
close found — Qodo's twelve items on PR #1 and the close review's threads —
and then audits each remaining pet project (Z1, Z2, Z3, Z5, Z6) as its
captures land, extending `PROBES.md` until all six are in. One batch = one
sub-agent = one commit = one concern. This file plus git is the only state;
any session can resume cold from it.

Last updated: 2026-10-12 (B1 decided — option 4, harness only; run 1 resumes B1 → B2 → B3.)

---

## 0. Operating protocol

### 0.1 Builder — orchestrator loop

The builder's own context must stay small. It reads this file, dispatches,
verifies, records, and moves on. It does not read source files itself,
does not debug itself, and does not carry batch detail in its context: all
of that happens inside a sub-agent whose context is discarded.

On the prompt `Execute WORKPLAN.md run N` (or `Resume WORKPLAN.md`):

1. `git status`. If the tree is dirty: dispatch one sub-agent with the
   **recovery brief** (0.4). Do not proceed until the tree is clean and
   `make check` is green (verify with a sub-agent; the builder runs no
   commands longer than `git status` / `git log --oneline -5` itself).
2. Read §1 and §2. Take the first batch of the requested run whose status is
   not `done` / `dropped` / `awaiting decision`. A status `awaiting <batch>`
   is `todo` once that batch is `done`.
3. Dispatch **one sub-agent** with the **batch brief** (0.3) for that batch.
   Wait for its ≤12-line report.
4. Verify: `git log --oneline -3` shows the batch commit; the report says
   `make check` passed. If not, dispatch the same batch once more with the
   report's failure appended. If it fails twice: set status
   `blocked: <one line>`, write the resume note, and continue to the next
   batch **unless** the blocked batch is a dependency of the next.
5. Edit this file: status → `done (<sha>)`, one line under §4 if anything
   was learned. If a row's acceptance number or premise was shown wrong by
   the batch, correct the row in the same edit and say why in the §4 line
   — a wrong criterion has an owner, and it is this step. Commit the plan
   edit together with nothing else (`plan: <batch> done`; a second clause
   after the batch id is allowed when it records something a reader needs).
6. Repeat from 2. Stop when: the run's batches are exhausted; a batch ends
   `awaiting decision`; or the same batch has failed twice.
7. Final step of a run: dispatch a sub-agent to `git format-patch main -o
   patches/` and print `git log --oneline main..HEAD`. Report to the human:
   batches done, blocked, awaiting decision, and the memo file paths to read.
8. `git push origin zoo`. A run is not finished until the push succeeds
   **and the GitHub checks on the pushed tip are green, or every failing
   check is explained in the run report**; local `make check` is not a
   substitute — the CI matrix runs interpreters the machine does not have.
   A series branch is never force-pushed. An amended batch is a new commit
   on top; the replaced sha is recorded in §4 with the reason.

### 0.2 Aux — cold reader

On the prompt `Review WORKPLAN.md commits since <sha>`: for each code commit,
in a sub-agent per commit, check against `CONTRIBUTING.md` and `CLAUDE.md`:
spec changed in the same commit where behaviour changed; the new test fails
on the parent commit, where the parent is `<sha>^` **derived**, never a sha a
brief names (`plan:` commits interleave) — and because a tests-only batch's
derived parent is a `plan:` commit, which makes the parent run vacuous, a
**mutation the new test catches** is required for every code commit, not only
the parent run; worktrees are created by **absolute path under the
scratchpad**, never relative, never inside the repo; no clock read, no
randomness, no network in `spanweave_zoo/` except behind the injected
`now`/`sleep`/socket seams the spec names; commit is one concern. Write
findings to `patches/REVIEW-<date>.md` (untracked) and print them. **Aux
never edits tracked files and never commits**: a finding that needs a commit
is made by the builder from the review file, never by the reviewer.

### 0.3 Batch brief (template the builder passes to a sub-agent)

```
You are executing batch <ID> of WORKPLAN.md in the spanweave-zoo repo.
Read, in this order: CLAUDE.md, the WORKPLAN.md row for <ID> and §5, then
the SPEC.md sections the row names, then only the source and test files
the batch touches. Rules: spec first (SPEC.md edited in this commit if
behaviour changes); write the failing test before the fix and confirm it
fails on the parent (`<sha>^`, in a worktree by absolute path under the
scratchpad); name one mutation the test catches and show it caught; then
implement; then `make check` and `make install-check`. Add a CHANGELOG
entry. Commit once: `<area>: <one line>` with a body naming <ID> and the
SPEC sections touched. Never edit WORKPLAN.md. If completing the batch
would require a change in spanweave itself, a dialect read outside
spanweave's adapters, a rule or a policy the spec does not already state —
stop, write the options to OPEN_QUESTIONS.md under a heading "<ID>: …",
commit that alone, and report `awaiting decision`. Report in ≤12 lines:
commit sha, files changed, tests added, mutation shown, make check result,
anything the orchestrator must know.
```

### 0.4 Recovery brief (dirty tree or interrupted batch)

```
The previous batch was interrupted. Read WORKPLAN.md §4. Run git status
and git diff --stat. If the in-progress work is complete enough to pass
`make check`, finish it under the batch brief rules and commit. Otherwise
`git stash` it with the message `wip <ID> <date>` and report what was
stashed and where it stopped. Leave the tree clean either way.
```

### 0.5 Context management (for the human)

- Builder: **clear context** before `Execute WORKPLAN.md run N` and before
  any `Resume WORKPLAN.md`. Continuity lives in this file and git, not in
  the session. The only time not to clear is when the builder has asked a
  question and is waiting for the answer.
- Aux: **always clear** before a review or a status check. Every aux task
  is stateless.
- A prompt that starts a run names `run N` within its first 100 characters,
  so the watcher's transcript derivation can see it. Decisions files are
  copied to `patches/` by the relay before the builder is prompted.

### 0.6 Standing rules (from CLAUDE.md, repeated because load-bearing)

The zoo captures what exporters send and never improves it. A capture is
immutable: bytes as received, with the request headers beside them and a
sha256 of each body in the manifest; `zoo verify` re-hashes every capture
and `make check` fails if any differs. The sink parses nothing and answers
every POST the same way; the Collector is the stock OpenTelemetry Collector
at a pinned version with a checked-in config, and its JSON re-encoding is
kept *beside* the raw bytes, never instead of them. The replayer re-sends
bytes and headers as captured and adds nothing. Nothing under
`spanweave_zoo/` imports spanweave or spanweave-live except the audit
module, and a gate holds that. An audit finding is a reproduction (a
capture, a command, an observed and an expected result), never a fix: fixes
belong to the repo that owns the defect, in its own series. `spanweave` and `spanweave-live` are pinned by git sha in
`pyproject.toml` and used only by the audit batch; the sink, the Collector
config and the replayer import neither.

TASKS.md is the item registry (one line per batch, written at series
close); this file is execution state only and is deleted at series close
with §3 folded into TASKS.md.

### 0.7 Watch (aux, read-only, report-then-stop)

While the builder is on a run, aux may run `~/spanweave-ops/watch_monitor.sh`
with `--base` set to the run's plan commit; it derives the branch and the
builder PIDs itself. Triggers and tripwires are as `~/spanweave-ops/WATCH.md`
states; the series-close commit that deletes this file is the one plan
commit that cannot say `plan:`, and the watcher exempts it once per series.

---

## 1. Batch list

| ID | Batch | Status | Calls |
|---|---|---|---|
| B0 | **The two reviews of the close, archived and dispositioned.** Fetch the Qodo comment on PR #1 (`gh api repos/SigorMatt/spanweave-zoo/issues/comments/6127903067 --jq .body`) and keep it byte for byte as `reviews/QODO-2026-10-12.md`, its sha256 appended to `reviews/SHA256SUMS` (26 files, `sha256sum -c` green). `TASKS.md`: a "Series 2" heading with the twelve Qodo items Q1–Q12 and the close review's two carried threads (the port race; the PR wording), each pointing at the batch below that closes it. Docs only; no code. | done (d0debab) | 3 |
| B1 | **The test harness does not lose a port race.** Close-review thread; `OPEN_QUESTIONS.md` §6, option 4. No product change: `zoo capture` names its ports and a held port is the refusal `SPEC.md` §4.6 specifies. `ZooCapture` in `tests/test_shutdown.py` (and any other harness that picks ports with `free_port()`) stops picking: it passes `0` for `--port` and `--json-port` and reads the bound ports back from the two lines after the ready line (§4.2) — if `0` is not accepted today, accepting it for the two sinks is a one-line CLI change with a test, and §4.6's table says `0` means an ephemeral port the ready lines report; for `--collector-port`, where the child must be told a number, the harness keeps a pick and **retries the whole start, bounded (5), when the refusal names an address in use**, logging every port tried. Tests red on the parent: a stand-in Collector whose first bind fails with the address-in-use line and whose second succeeds reaches readiness through the harness; a `--port 0 --json-port 0` run prints two ports the test can POST to. The mutation "no retry in the harness" fails the first. `test_the_collector_killed_by_hand_mid_capture_is_a_problem` and every `needs_collector` test go through the new harness. | todo | 5 |
| B2 | **Signals cover the whole life of a capture, and of the sink.** Q1, Q6, Q8. (a) `run_capture` installs the stop handlers **before** `running.start()`, so SIGTERM/SIGHUP during readiness (up to 52.5 s) runs the stop path and the Collector, in its own session, does not outlive the parent; a refusal still writes nothing. (b) `Capture.start`'s tail — `_now()`, `manifest.label`, `serve()`, the log lines — inside the same `try/except BaseException: self.stop(); raise` as the steps before it. (c) `run_sink` installs the same handlers so SIGTERM/SIGHUP end `serve_forever` normally and `manifest.finish` runs. Three tests red on the parent, one per letter: SIGTERM to the process while the stand-in Collector is still becoming ready → no Collector process remains and no run directory exists; a `manifest.label` that raises → the Collector is stopped; SIGTERM to a standalone sink → a sealed manifest. SPEC §4.6 and §3 say so. | todo | 8 |
| B3 | **Nothing writes to a capture after its seal.** Q2, Q7. (a) `Capture.stop` seals only once every POST handler has returned: after the Collector is stopped (which fails any forward still waiting), settle again with a bound; a handler still running at that bound is recorded as a `problems` entry naming the body, and the journals are **closed** — an append after closing is refused by the recorder and recorded nowhere, so the sealed manifest's hashes hold. (b) A journal that does not decode as UTF-8 is a `problems` entry, and `finish` still writes `ended_at` and the seal. Tests red on the parent: a forward whose completion is held past the flush bound (injected) completes after the seal and `zoo verify` is **still green**; a journal with an invalid byte yields a sealed manifest with the problem listed. SPEC §5.5/§5.6 say what the seal covers and when writing ends. | todo | 7 |
| B4 | **`verify` trusts nothing a manifest says about where a file is.** Q10, Q12. A manifest field that should be a list and is not → a problem, not a `TypeError` (`_listed`, `_incomplete`, as `_rehashed` already does); a file entry that is absolute, contains `..`, or resolves (symlinks followed) outside `run.resolve()` → a problem naming the entry, and the file is not read. SPEC §5.4: entries are normalized relative paths under the run directory. Tests red on the parent for `"files": 1`, `"problems": 1`, an absolute entry, a `..` entry, and a symlink out; mutation shown. The seal decision of 2026-10-11 stands: a resealed manifest still verifies — within the run directory. | todo | 5 |
| B5 | **The wire is honest at its edges.** Q9, Q11, Q3. (a) A POST the sink cannot frame — no `Content-Length`, a non-numeric one, or a non-positive one with `Transfer-Encoding` present — is still recorded as a zero-byte body (SPEC §3.7), **and the connection is closed** after the answer (`close_connection`, `Connection: close`), so leftover framing can never be parsed as the next request; test red on the parent: a chunked POST followed on the same connection by a well-formed one yields exactly one recorded body and no stray 400. (b) A `Host` value for an IPv6 literal is bracketed, in `replay` and in `HttpForward`; test: `--to http://[::1]:<port>` sends `Host: [::1]:<port>`. (c) `replay --timing` advances `previous` past an unreadable head using the body's own `received_at`, so the next gap is measured from the right receipt; tests for a skipped first and a skipped middle request. | todo | 7 |
| B6 | **The audit says "not run" when it cannot vouch.** Q4, Q5. (a) When step 3's in-process re-read does not match `serve` (statuses or routed count), step 3 is incomplete **and** its partition comparisons and steps 4–5 are not run and rendered as such — as SPEC §7.3 already says; today the findings are emitted anyway. (b) A `serve` command that cannot start (`OSError` from `Popen`) is `served.problem = "serve did not start: …"`, the report is still written, exit 1 — as SPEC §7.5 lists it. Tests red on the parent: a mismatch injected through the `reread` seam yields a report with steps 3–5 "not run" and no library finding; a nonexistent serve command yields a written report and exit 1. | todo | 5 |
| B7 | **Per-project audit, one row per capture pair.** Template, instantiated by a `plan:` commit when a project's captures land on `zoo` (operator commit `captures: zN real and recorded, <date>`): `zoo audit` on both captures, reports under `audit/zN-<date>-{real,recorded}.md`, `PROBES.md` extended with every new probe (owner, capture, command, observed, expected or "to establish"), `ROADMAP.md`'s row for Zn updated, CI's `audit` job still green with the new reports. Findings are never fixed here. First instance: **B7-Z3** or **B7-Z5**, whichever lands first. | awaiting captures | 6 each |
| B8 | **The series closes.** When every project's row in `ROADMAP.md` reads audited: `TASKS.md` registry B0–B8 with shas, §3 and §4 folded; `reviews/` complete with sha256; `PROBES.md` consolidated across all six projects, grouped by owner; WORKPLAN.md deleted; PR `zoo` → `main` (a merge commit, as PR #1 was). No `plan:` commit follows. | awaiting B7 | 6 |

## 2. Execution order

Run 1 = B0 → B1 → B2 → B3. Run 2 = B4 → B5 → B6. Then B7 rows as captures
land, in their own runs, and B8 when the sixth is audited. Every batch: CI
green on the pushed tip before `done`. The branch is `zoo`, fast-forwarded
to `main` at the series open.

## 3. Decisions log

| Date | Batch | Decision | By |
|---|---|---|---|
| 2026-10-12 | series | Qodo's twelve items on PR #1 are **all accepted**, each verified against the code at `25b2ef2` before this plan was written: Q1/Q8 (handlers after `start()`, the untried tail of `start`), Q2 (a late journal append after the seal), Q3 (`previous` not advanced), Q4 (findings emitted after a step-3 mismatch, against SPEC §7.3's own words), Q9 (unframed body left on a keep-alive connection) were confirmed by reading; Q5, Q6, Q7, Q10, Q11, Q12 are small and plausible and are taken on their tests. None conflicts with a series-1 decision: the Collector keeps its own session (A3e) and the fix for Q1 is to cover startup, not to rejoin the group; the seal still verifies a resealed manifest (2026-10-11) — B4 confines *where*, not *whether*. | maintainer |
| 2026-10-12 | B1 | A refusal on a port taken between pick and bind is correct behaviour and bad luck at once; the retry is bounded and every port tried is named, so the refusal after N is as honest as the refusal after one. | maintainer |
| 2026-10-12 | B5(a) | The sink still decodes no framing. Closing the connection is the only answer consistent with "the sink parses nothing": it records what it could see and refuses to guess where the next request begins. | maintainer |
| 2026-10-12 | B7 | Audits are one batch per project, never one batch for several: each report is reproducible from its own pair of captures and the pins. | maintainer |
| 2026-10-12 | B1 | **Option 4.** The 2026-10-12 "B1" row above described the harness, not `zoo capture`, and is read that way: the retry is bounded and every port tried is named — in the test harness. `zoo capture` picks no port and refuses a held one, as §4.6 says; a CLI meaning and a socket seam added for the test suite's convenience would be product scope the product does not need. `--port 0`/`--json-port 0` for the sinks, if accepted, is the one product-side allowance, because the sinks bind themselves and the ready lines already report their ports. | maintainer |
| 2026-10-12 | B1 | The row's premise was the maintainer's error (it read the Collector's port as picked); the builder's correction under §0.1 step 5 was right, and the stop was right. | maintainer |

## 4. Resume note

- 2026-10-12: series 2 opened on `zoo` from `main` `25b2ef2`. Pet projects
  Z3 and Z5 are being built in parallel; their captures arrive as operator
  commits on `zoo` and instantiate B7 rows.
- 2026-10-12 B0: `gh api --jq .body` appends a newline the raw body lacks;
  the archive keeps the raw body (38083 bytes). `reviews/SHA256SUMS` gained
  its 26th line at the end, so it is no longer in filename order — nothing
  checks the order. The PR-wording thread is mapped to B8.
- 2026-10-12 B1: premise wrong — `zoo capture` picks no Collector port; the
  port is `--collector-port`, and SPEC §4.6 makes a held named port a refusal
  (tested). The race was the harness's `free_port()` (CI run 38273980263, port
  43383, Errno 98); the harness's raw/json sink ports share it. Row corrected;
  four options in OPEN_QUESTIONS §6 (b7165a0). Run 1 stopped here per 0.1
  step 6; B2 and B3 do not depend on B1 and can run once it is decided.
- 2026-10-12: B1 decided (option 4, harness only). B2 and B3 did not depend
  on B1 and were not run because the protocol stops a run at `awaiting
  decision`; run 1 resumes B1 → B2 → B3.

## 5. Origins

| ID | Origin |
|---|---|
| B0, B2–B6 | Qodo's review of PR #1 (comment 6127903067, 2026-10-12): 12 bugs, 0 rule violations. |
| B1 | The close review's thread (`TASKS.md`, series 1): `test_the_collector_killed_by_hand_mid_capture_is_a_problem` failed once in the PR run at `e50a56e` on a port taken between pick and bind, green on re-run. |
| B7, B8 | `ROADMAP.md`: the per-project checklist, step 4. |
