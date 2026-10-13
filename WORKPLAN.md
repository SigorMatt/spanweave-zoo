# WORKPLAN.md — spanweave-zoo, series 2: the hardening series, and the five audits

Status file for the zoo's second series. Series 1 (`TASKS.md`) built the
capture side and audited Z4; this series closes what two reviews of its
close found — Qodo's twelve items on PR #1 and the close review's threads —
and then audits each remaining pet project (Z1, Z2, Z3, Z5, Z6) as its
captures land, extending `PROBES.md` until all six are in. One batch = one
sub-agent = one commit = one concern. This file plus git is the only state;
any session can resume cold from it.

Last updated: 2026-10-13 (B6a decided, B5b confirmed, B5c added; run 4 resumes B5c → B6a → B7r.)

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
| B1 | **The test harness does not lose a port race.** Close-review thread; `OPEN_QUESTIONS.md` §6, option 4. No product change: `zoo capture` names its ports and a held port is the refusal `SPEC.md` §4.6 specifies. `ZooCapture` in `tests/test_shutdown.py` (and any other harness that picks ports with `free_port()`) stops picking: it passes `0` for `--port` and `--json-port` and reads the bound ports back from the two lines after the ready line (§4.2) — if `0` is not accepted today, accepting it for the two sinks is a one-line CLI change with a test, and §4.6's table says `0` means an ephemeral port the ready lines report; for `--collector-port`, where the child must be told a number, the harness keeps a pick and **retries the whole start, bounded (5), when the refusal names an address in use**, logging every port tried. Tests red on the parent: a stand-in Collector whose first bind fails with the address-in-use line and whose second succeeds reaches readiness through the harness; a `--port 0 --json-port 0` run prints two ports the test can POST to. The mutation "no retry in the harness" fails the first. `test_the_collector_killed_by_hand_mid_capture_is_a_problem` and every `needs_collector` test go through the new harness. | done (d99ba97) | 5 |
| B2 | **Signals cover the whole life of a capture, and of the sink.** Q1, Q6, Q8. (a) `run_capture` installs the stop handlers **before** `running.start()`, so SIGTERM/SIGHUP during readiness (up to 52.5 s) runs the stop path and the Collector, in its own session, does not outlive the parent; a refusal still writes nothing. (b) `Capture.start`'s tail — `_now()`, `manifest.label`, `serve()`, the log lines — inside the same `try/except BaseException: self.stop(); raise` as the steps before it. (c) `run_sink` installs the same handlers so SIGTERM/SIGHUP end `serve_forever` normally and `manifest.finish` runs. Three tests red on the parent, one per letter: SIGTERM to the process while the stand-in Collector is still becoming ready → no Collector process remains and no run directory exists; a `manifest.label` that raises → the Collector is stopped; SIGTERM to a standalone sink → a sealed manifest. SPEC §4.6 and §3 say so. | done (202556c) | 8 |
| B2a | **The per-body cost test measures the recorder, not the runner.** Registry thread (series 1, "macOS wall-clock cost test"), failed again at B2's first CI run. `test_sixteen_hundred_bodies_cost_the_same_each` compares the first and last hundred bodies by **CPU time** (`time.process_time`) or by the **number of writes per body** (a counting seam on the recorder), not by wall clock; the bound stays, the method is stated in the test's docstring, and the test is red on the parent through a mutation that makes the recorder's cost grow with the run (an O(n) rescan per body). No re-run ratification remains after this row. | done (91e094d) | 4 |
| B2b | **The per-body cost is a count, not a clock.** Registry thread, failed again at `7275b12` on CPU time. A counting seam on the recorder (writes, or the file operations the recorder performs per body — one definition, stated in SPEC §3.6) replaces the timing assertion in `test_sixteen_hundred_bodies_cost_the_same_each`: the count for body 1,600 **equals** the count for body 1. The timing figures may be printed for a reader and are asserted nowhere. Red on the parent through the same mutation as B2a (an O(n) rescan per body) — which the count catches and the clock did not reliably. | done (`63e44bc`) | 3 |
| B3 | **Nothing writes to a capture after its seal.** Q2, Q7. (a) `Capture.stop` seals only once every POST handler has returned: after the Collector is stopped (which fails any forward still waiting), settle again with a bound; a handler still running at that bound is recorded as a `problems` entry naming the body, and the journals are **closed** — an append after closing is refused by the recorder and recorded nowhere, so the sealed manifest's hashes hold. (b) A journal that does not decode as UTF-8 is a `problems` entry, and `finish` still writes `ended_at` and the seal. Tests red on the parent: a forward whose completion is held past the flush bound (injected) completes after the seal, every sealed file is byte-identical, and `zoo verify` fails **only** on the one recorded problem (§5.6), never on a digest or the seal (corrected 2026-10-12, §4); a journal with an invalid byte yields a sealed manifest with the problem listed. SPEC §5.5/§5.6 say what the seal covers and when writing ends. | done (12de782) | 7 |
| B3a | **Standalone `zoo sink` seals only once nothing can write.** B3's rule extended to `run_sink`: on a stop signal the server stops accepting, every POST handler has returned or is bounded out and recorded as a problem, the journals are closed, then `manifest.finish`. Test red on the parent: a POST handler held past the bound (standalone `zoo sink` has no forward; corrected 2026-10-13, §4) completes after the seal and `zoo verify` fails only on the recorded problem; mutation shown. SPEC §3 says the sink and the capture seal the same way. | done (cae8168) | 4 |
| B4 | **`verify` trusts nothing a manifest says about where a file is.** Q10, Q12. A manifest field that should be a list and is not → a problem, not a `TypeError` (`_listed`, `_incomplete`, as `_rehashed` already does); a file entry that is absolute, contains `..`, or resolves (symlinks followed) outside `run.resolve()` → a problem naming the entry, and the file is not read. SPEC §5.4: entries are normalized relative paths under the run directory. Tests red on the parent for `"files": 1`, `"problems": 1`, an absolute entry, a `..` entry, and a symlink out; mutation shown. The seal decision of 2026-10-11 stands: a resealed manifest still verifies — within the run directory. | done (99edcbd) | 5 |
| B4a | **The replayer refuses a path outside the run.** `OPEN_QUESTIONS.md` §7, option 1. `zoo replay` applies B4's check (the function `verify` uses) to every `files`/`bodies` entry of the manifest, on both sides, before sending anything: an absolute entry, a `..` entry, or one resolving outside the run directory is a refusal naming the entry, exit 2, nothing sent. The audit is unchanged: it already refuses a run that fails `verify` (§7.2), and one test asserts that refusal names the entry (an absolute entry and a `..` entry, on fixture copies). Tests red on the parent for replay: the two bad entries, each on the sent side and on the other side; mutation shown. SPEC §6 says replay trusts a manifest only as far as `verify` would. | done (`3dcd17a`) | 4 |
| B5 | **The wire is honest at its edges.** Q9, Q11, Q3. (a) A POST the sink cannot frame — no `Content-Length`, a non-numeric one, or a non-positive one with `Transfer-Encoding` present — is still recorded as a zero-byte body (SPEC §3.7), **and the connection is closed** after the answer (`close_connection`, `Connection: close`), so leftover framing can never be parsed as the next request; test red on the parent: a chunked POST followed on the same connection by a well-formed one yields exactly one recorded body and no stray 400. (b) A `Host` value for an IPv6 literal is bracketed, in `replay` and in `HttpForward`; test: `--to http://[::1]:<port>` sends `Host: [::1]:<port>`. (c) `replay --timing` advances `previous` past an unreadable head using the body's own `received_at`, so the next gap is measured from the right receipt; tests for a skipped first and a skipped middle request. | done (cafb8cd) | 7 |
| B5a | **A request with `Transfer-Encoding` is never read by its `Content-Length`, and a negative length closes.** Review of B5's remainder. Any `Transfer-Encoding` header: zero-byte body, the answer, `Connection: close`, connection closed — regardless of `Content-Length`. A negative `Content-Length` with no `Transfer-Encoding`: zero-byte body, the answer, closed. Tests red on the parent: a POST with both headers followed on the same connection by a well-formed POST yields one recorded zero-byte body, no second request parsed from the chunk frames; a negative length likewise; mutation shown. SPEC §3.7's table lists every framing case and its outcome. | done (`558ec4a`) | 4 |
| B5b | **A `Content-Length` is digits, once.** Review of B5a's remainder. `1*DIGIT` only; `+5`, a whitespace character other than SP/HTAB before the `5` (a leading SP is OWS, dropped before the value — corrected at B5b's close, §4), `5_0`, and two `Content-Length` headers with differing values are unframeable: zero-byte body, the answer, `Connection: close`, closed; identical duplicates are one length. Tests red on the parent for each of the five cases, each followed on the same connection by a well-formed POST that must not be parsed from leftovers; mutation shown. SPEC §3.7's table gains the rows. | done (`a48dfcc`) | 3 |
| B5c | **A folded `Content-Length` is unframeable.** B5b's open case. A head whose `Content-Length:` value continues on a following line (obs-fold) yields a zero-byte body, the answer, `Connection: close`, closed — the sink frames by nothing the record does not show. Test red on the parent: the folded head followed on the same connection by a well-formed POST yields one zero-byte body and no second request from leftovers; `headers.json` unchanged (the fold stays `unparsed`); mutation shown. SPEC §3.7's table gains the row. | done (`9bcbaa0`) | 3 |
| B6 | **The audit says "not run" when it cannot vouch.** Q4, Q5. (a) When step 3's in-process re-read does not match `serve` (statuses or routed count), step 3 is incomplete **and** its partition comparisons and steps 4–5 are not run and rendered as such — as SPEC §7.3 already says; today the findings are emitted anyway. (b) A `serve` command that cannot start (`OSError` from `Popen`) is `served.problem = "serve did not start: …"`, the report is still written, exit 1 — as SPEC §7.5 lists it. Tests red on the parent: a mismatch injected through the `reread` seam yields a report with steps 3–5 "not run" and no library finding; a nonexistent serve command yields a written report and exit 1. | done (290fc1b) | 5 |
| B6a | **The audit observes every policy and names every node.** `OPEN_QUESTIONS.md` §8, option 1 over a timed replay. (1) Step 2 runs `serve` three times per capture: `--requests N` untimed (the end-of-input `Cap(0)`, as today; step 3's graphs); `--quiet 0 --requests N` with `zoo replay --timing`; `--root-grace 0 --requests N` with `zoo replay --timing` — recording per run every `completed` event with its index, reason and generation, every `late_arrival`, `written`, `released`, `finished`. The Method names the values as the audit's. (2) Step 4 adds a per-node table: node id, kind, status, model, parent present (yes / no / absent from graph), diagnostic codes on the node, span events as the record carries them. SPEC §7.3 and §7.5 say so. Tests red on the parent through the `serve_command` seam (three invocations with the flags given, the replay's `--timing` on two) and on a fixture graph with one ERROR node (the row appears with its status); mutation shown. | done (`07285bd`) | 6 |
| B7r | **Every captured project audited once more, with the one audit.** After B6a: `zoo audit` on Z4's, Z3's and Z5's six captures; the six reports under `audit/` replaced; PROBES.md updated — every "to establish" or "not observable" line that B6a's report answers gets its observation, each probe cites the new report, the counts and the pins paragraph restated; `ROADMAP.md`'s three rows cite the re-audit. No capture touched; findings never fixed. | awaiting B6a | 6 |
| B7 | **Per-project audit, one row per capture pair.** Template, instantiated by a `plan:` commit when a project's captures land on `zoo` (operator commit `captures: zN real and recorded, <date>`): `zoo audit` on both captures, reports under `audit/zN-<date>-{real,recorded}.md`, `PROBES.md` extended with every new probe (owner, capture, command, observed, expected or "to establish"), `ROADMAP.md`'s row for Zn updated, CI's `audit` job still green with the new reports. Findings are never fixed here. First instance: **B7-Z3** or **B7-Z5**, whichever lands first. | template | 6 each |
| B7-Z3 | **Audit Z3 (`echo-planner`): `captures/z3/2026-10-13-real` (4 bodies, the root in the last) and `-recorded` (1 body).** As the B7 template. Of particular interest, to be reported as observed and never asserted: the real capture's root span arriving in the fourth body (what `serve`'s completion did with a trace whose root came last); the 599 `Attributes dict is full` lines (which attributes the SDK dropped, visible as `unmapped_attributes` or as absence); two instrumentors on one client (`generation` and `ChatCompletion` for every turn — whether spanweave claims both, one, or neither). `PROBES.md` extended; `ROADMAP.md`'s Z3 row reads audited. | done (`a180f06`) | 6 |
| B7-Z5 | **Audit Z5 (`flaky-fetcher`): `captures/z5/2026-10-13-real` and `-recorded` (one body each, four spans, no root).** As the B7 template. Of particular interest: a trace with no root in either capture (what `Quiet`, `RootEnded` and `Cap` each did with it); two `http_get` spans in ERROR with `exception` events (how spanweave renders a failed tool call and its exception); the real and recorded bodies (believed identical when the row was written; they are not — same length, 380 bytes differ — corrected at B7-Z5's close, §4). `PROBES.md` extended; `ROADMAP.md`'s Z5 row reads audited. | done (`54703f2`) | 6 |
| B8 | **The series closes.** When every project's row in `ROADMAP.md` reads audited: `TASKS.md` registry B0–B8 with shas, §3 and §4 folded; `reviews/` complete with sha256; `PROBES.md` consolidated across all six projects, grouped by owner; WORKPLAN.md deleted; PR `zoo` → `main` (a merge commit, as PR #1 was). No `plan:` commit follows. | awaiting B7 | 6 |

## 2. Execution order

Run 1 = B0 → B1 → B2 → B3, done (`8c5941a`). Run 2 = B2a → B3a → B4 → B5 →
B6, done (`4c021c7`). Run 3 = B2b → B4a → B5a → B7-Z3 → B7-Z5, done
(`99d5e60`). Run 4 = B5b (done, `a48dfcc`) → B5c → B6a → B7r. Then B7 rows
for Z1, Z2, Z6 as their captures land, and B8 when the sixth is audited.
Every batch: CI green on the pushed tip before `done`.

## 3. Decisions log

| Date | Batch | Decision | By |
|---|---|---|---|
| 2026-10-12 | series | Qodo's twelve items on PR #1 are **all accepted**, each verified against the code at `25b2ef2` before this plan was written: Q1/Q8 (handlers after `start()`, the untried tail of `start`), Q2 (a late journal append after the seal), Q3 (`previous` not advanced), Q4 (findings emitted after a step-3 mismatch, against SPEC §7.3's own words), Q9 (unframed body left on a keep-alive connection) were confirmed by reading; Q5, Q6, Q7, Q10, Q11, Q12 are small and plausible and are taken on their tests. None conflicts with a series-1 decision: the Collector keeps its own session (A3e) and the fix for Q1 is to cover startup, not to rejoin the group; the seal still verifies a resealed manifest (2026-10-11) — B4 confines *where*, not *whether*. | maintainer |
| 2026-10-12 | B1 | A refusal on a port taken between pick and bind is correct behaviour and bad luck at once; the retry is bounded and every port tried is named, so the refusal after N is as honest as the refusal after one. | maintainer |
| 2026-10-12 | B5(a) | The sink still decodes no framing. Closing the connection is the only answer consistent with "the sink parses nothing": it records what it could see and refuses to guess where the next request begins. | maintainer |
| 2026-10-12 | B7 | Audits are one batch per project, never one batch for several: each report is reproducible from its own pair of captures and the pins. | maintainer |
| 2026-10-12 | B1 | **Option 4.** The 2026-10-12 "B1" row above described the harness, not `zoo capture`, and is read that way: the retry is bounded and every port tried is named — in the test harness. `zoo capture` picks no port and refuses a held one, as §4.6 says; a CLI meaning and a socket seam added for the test suite's convenience would be product scope the product does not need. `--port 0`/`--json-port 0` for the sinks, if accepted, is the one product-side allowance, because the sinks bind themselves and the ready lines already report their ports. | maintainer |
| 2026-10-12 | B1 | The row's premise was the maintainer's error (it read the Collector's port as picked); the builder's correction under §0.1 step 5 was right, and the stop was right. | maintainer |
| 2026-10-13 | B2 | A stop signal before readiness is a refusal and exits 2: a refusal writes nothing, and 2 is the refusal's status. Confirmed. | maintainer |
| 2026-10-13 | B3 | A body arriving on a still-open connection after the journals close gets no answer and the connection is closed — **confirmed**, and stated as a rule rather than an exception: after the close the sink is, to a client, gone, exactly as a stopped listener is. "Answers every POST the same way" (0.6) applies to the POSTs the sink accepts; a closed sink accepts none. A `503` would be an answer without a record, which is the worse breach. SPEC §3.3/§5.5 say it this way. | maintainer |
| 2026-10-13 | B3 | The row's verify criterion was wrong and the builder's correction stands: a late forward is a `problems` entry, and §5.6 fails any recorded problem; what the batch proves is that `verify` fails on *that* problem alone, never on a digest or the seal. | maintainer |
| 2026-10-13 | B3a | Standalone `zoo sink` gets the same close-then-seal as `zoo capture`: "nothing writes after the seal" has no exception. | maintainer |
| 2026-10-13 | B2a | `test_sixteen_hundred_bodies_cost_the_same_each` failed on the macOS leg again (B2's first CI run) and the series-1 ratification covered series 1 only. It is fixed now, as the registry names: the per-body cost measured by CPU time (`time.process_time`) or by the count of writes per body, never by wall clock; the bound and the method stated in the test. | maintainer |
| 2026-10-13 | patches | `patches/` is gitignored and holds series 1's 63 files beside series 2's. At the next close-out step the builder clears `patches/*.patch` once before writing (review files stay); series 2's set then numbers from 0001 without overlap. | maintainer |
| 2026-10-13 | B7 | Z3 (`SigorMatt/echo-planner` at `71bc477`, captures `9b0268f`) and Z5 (`SigorMatt/flaky-fetcher` at `2a3e778`, captures `f081997`) are captured; their audit rows are instantiated below and run as run 3, after run 2's hardening, so the audit code they exercise is the hardened one (B6). | maintainer |
| 2026-10-13 | B3a | Confirmed: the row's test is a slow POST held past the bound (the standalone sink has no forward); `zoo sink` exits 1 when its sealed manifest records a problem, as `zoo capture` does. | maintainer |
| 2026-10-13 | B5 | Confirmed: a POST the sink cannot frame is answered as every POST is and the connection is then closed, with `Connection: close` on that answer. Standing rule 3 reads: the **answer** — status and body — is the same for every POST; what happens to the connection after the answer is not part of the answer, and a request the sink could not frame must end its connection or the next request is a guess (SPEC §3.3). | maintainer |
| 2026-10-13 | B6 | Confirmed: a step-3 mismatch withholds the findings of steps 3–5 only. Steps 1 and 2 report the receiver's answers to real bytes and stand on their own; the 415 of step 1 is never withheld. | maintainer |
| 2026-10-13 | B4a | The replayer and the audit read manifest file paths with the same check as `verify` (B4): a path that is absolute, contains `..`, or resolves outside the run directory is refused and named. The manifest is the only thing between a capture's claims and a reader's filesystem. | maintainer |
| 2026-10-13 | B5a | Two framing cases closed the same way as B5: a request carrying `Transfer-Encoding` is never read by `Content-Length`, whatever that header says — the sink decodes no framing, records a zero-byte body, answers, and closes the connection (that pair of headers is the request-smuggling shape, and the record says what the sink could see); a negative `Content-Length` is a zero-byte body and a closed connection too. | maintainer |
| 2026-10-13 | B2a | Confirmed as built: median of the first and last hundred bodies by CPU time, bound 2.0. No re-run ratification remains. | maintainer |
| 2026-10-13 | B4a | **Option 1.** The audit stands behind `verify` (§7.2): a run whose manifest fails `verify` is refused before the audit reads anything, and the refusal names the entry — the row's "incomplete report" was the maintainer's error, written before B4 made such a manifest fail `verify`. `replay` alone lacks the check and gets it; it refuses a bad entry on **either** side, the one it sends and the one it does not, because a manifest is one document and one bad claim makes all of it untrusted. | maintainer |
| 2026-10-13 | B2b | `test_sixteen_hundred_bodies_cost_the_same_each` failed on macOS again at `7275b12` with CPU time (510 → 1,333 µs/body, ratio 2.6), so CPU time is not the measure either on that runner. The measure that cannot be noisy is structural: the **number of write operations per body**, counted through a seam on the recorder, must be **equal** for the first and the last body of the run — that is what "cost the same each" means. Wall-clock and CPU figures may still be printed, never asserted. | maintainer |
| 2026-10-13 | run 3 | B2b runs first: a flaky leg blocks "CI green on the tip" for every batch after it. | maintainer |
| 2026-10-13 | B2b | Confirmed: the count is the recorder's file operations per body, reads included — the mutation it exists to catch is a re-read. SPEC §3.6 says so. | maintainer |
| 2026-10-13 | B4a | Confirmed as built: the audit's refusal shows `verify`'s first problem. The audit stands behind `verify`; what `verify` says is what the audit says. | maintainer |
| 2026-10-13 | B7-Z3, B7-Z5 | The two row corrections stand. The 599 `Attributes dict is full` lines are the SDK's stderr and not part of the record; `droppedAttributesCount` is what the record carries of them (S8). Z5's real and recorded bodies are the same length, not the same bytes (S13) — timestamps and ids. | maintainer |
| 2026-10-13 | B5b | A `Content-Length` is `1*DIGIT` and nothing else: `+5`, ` 5`, `5_0` are not lengths and make the request unframeable (zero-byte body, the answer, `Connection: close`). Two `Content-Length` headers with differing values are unframeable the same way; identical duplicates are one length (RFC 9110 §8.6). | maintainer |
| 2026-10-13 | B6a | The audit's blind spots are the audit's. Step 2 runs `serve` under **each** completion policy — the end-of-input `Cap(0)` as today, then `--quiet` and `--root-grace` at the receiver's documented defaults — and records, per policy, every `completed` event with its index and reason, so what each policy did with a rootless trace (L4) or a root that arrived last (L3) is observed, not "to establish". Step 4 reports **per node**: id, kind, status, model, whether its parent is present, and the diagnostic codes on it — so S6, S10, S11 and S12's "the report names no node" is closed by the report. Span events are listed per node as the record carries them. The report's size may grow; a per-node table is what a stranger's trace needs. | maintainer |
| 2026-10-13 | B7r | After B6a, every captured project is audited again with the one audit — Z4, Z3, Z5 — and the committed reports are **replaced**, never kept beside the old ones: a report is reproducible from the pins and the audit at one sha, and two audit versions in `audit/` would make PROBES.md cite two methods. PROBES.md's "to establish" lines that B6a makes observable get their observation; the rest stay. | maintainer |
| 2026-10-13 | relay | Two of the run-3 prompts put `run 3` past the transcript's 200-character cap, against §0.5, so the watcher could not derive the builder. Every run prompt from now on starts `Run N of WORKPLAN.md …`. | maintainer |
| 2026-10-13 | B6a | **Option 1, over a timed replay.** The row's "documented defaults" was the maintainer's error: the pinned receiver has none. The two policy runs use `--quiet 0` and `--root-grace 0` and replay with `--timing`, so the captured inter-body gaps — the SDK's 5-second batch ticks — separate the bodies and each body gets the policy's verdict; a gap that long always contains a receiver tick, so the sequence of `completed` events is deterministic. The end-of-input run (`--requests N`, untimed) stays as today and is the one whose graphs step 3 compares. The report's Method states the values are the audit's choice. Option 4 (defaults in the receiver) is declined: the pin is the record. If a re-run ever differs beyond the port and clock lines, that is a finding about the audit's method and is recorded as one. | maintainer |
| 2026-10-13 | B5b | Confirmed: a leading space never reaches the sink (the test's vertical tab stands); trailing whitespace after the digits is a valid length (RFC 9110 §5.5 OWS). | maintainer |
| 2026-10-13 | B5c | A `Content-Length` continued on a folded line (obs-fold) is unframeable: the stdlib would frame by it while the record's derivation lists the fold as `unparsed` with an empty value, and the record and the framing must agree. Zero-byte body, the answer, `Connection: close`. | maintainer |

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
- 2026-10-12 B1 (d99ba97): `--port 0`/`--json-port 0` were already
  accepted on the parent, so no CLI change; SPEC §4.6/§4.2 now say what `0`
  means for the sinks. The harness also picks `--collector-grpc-port` (the
  real Collector binds it), covered by the same retry. Tests that expect a
  refusal still pick without retry, so a race there can change which
  refusal they see; `tests/test_replay.py` (~l.640) picks a port it needs
  closed — a different race, not B1. CI 38310803935 green.
- 2026-10-12 B2 (202556c): the row named no exit status for a stop signal
  during readiness; the batch made it a refusal (exit 2, `refusing to
  start: <SIG> arrived before the capture was ready …`), reading "a refusal
  still writes nothing" — a maintainer may revisit. Once the run directory
  exists a signal only asks the run to stop, so the capture is sealed.
  Beyond the row: `collector.Binary.start` stops the child on any exit once
  the process exists; a signal inside `Popen` itself can still leak it.
  CI 38311763209: macOS 3.12 failed once on
  `test_sixteen_hundred_bodies_cost_the_same_each` (1054 vs 2×505 us/body,
  a timing ratio on a shared runner; B2 touches no manifest code), green on
  re-run of the failed job. The test is a flake candidate, not owned here.
- 2026-10-12 B3 (12de782): row criterion wrong — "`zoo verify` is still
  green" after a late forward cannot hold: (a) requires a `problems` entry
  and §5.6 fails any recorded problem. Row corrected: verify fails only on
  that problem, never on a digest or the seal. Beyond the row, for the
  maintainer to confirm: a body arriving on a still-open keep-alive
  connection after the journals close gets **no answer** and the
  connection is closed (a `200` would claim "recorded", §3.3); written into
  SPEC §3.3/§5.5 — it sits against 0.6's "answers every POST the same
  way". Not done: `run_sink` (standalone `zoo sink`) neither settles nor
  closes its journals before `finish`; a late write there still shows as
  a verify failure. A separate row if wanted. CI 38312749085 green.
- 2026-10-13: run 1 confirmed (B2's exit status, B3's no-answer rule);
  B2a and B3a added from the run's open items; Z3 and Z5 captured by the
  operator and their audits instantiated for run 3; `patches/` to be
  cleared of series 1's files at the next close-out.
- 2026-10-13 B2a (91e094d): CPU time (`time.process_time`), median of
  first vs last hundred `record` calls, bound 2.0 kept; the write-count
  option was not taken because the row's own mutation (an O(n) rescan) is
  reads, not writes. Tests-only, so the parent run is vacuous (green, 1.07);
  the rescan mutation fails it (6.89). `make check` runs pytest without
  `-s`, so CI shows no ratio, only the pass. CI 38319431533 green (macOS too).
- 2026-10-13 B3a (cae8168): row premise wrong — standalone `zoo sink`
  has no forward; the test holds a POST handler past `FLUSH_WAIT` through
  the `before_record` seam (a slow client still sending). Row corrected.
  B3's mechanism reused (stop listening, settle, `Recorder.close()`, seal).
  Beyond the row, for the maintainer to confirm: `zoo sink` now **exits 1**
  when the sealed manifest records a problem (it always exited 0), as
  `zoo capture` does; that includes an unreadable journal found by
  `finish`. SPEC §3.7 says so. CI 38319984732 green.
- 2026-10-13 B4 (99edcbd): SPEC §5.4 holds the path rule beside the
  `file` key, §5.6 the `verify` behaviour. `"bodies": 1` was already
  refused by `manifest.read`, so not tested. Open, beyond the row: the
  replayer and the audit read `run / file` through `recorded_bodies`
  without this confinement, so a crafted manifest can still point them
  outside the run directory — a candidate row. CI 38320426656 green.
- 2026-10-13 B5 (cafb8cd): for the maintainer to confirm: the unframed
  answer carries one extra header, `Connection: close`, chosen by the
  request's framing headers, never its bytes — SPEC §3.3 states it against
  0.6's "answers every POST the same way". Still as before, outside the
  row: a negative `Content-Length` without `Transfer-Encoding` keeps the
  connection; a positive `Content-Length` with `Transfer-Encoding` is read
  by length. `--timing` with no `headers.json` reports the next gap as not
  computable. IPv6 test ran in CI (not skipped). CI 38321090784 green.
- 2026-10-13 B6 (290fc1b): "no library finding" read as no finding from
  steps 3–5; steps 1–2 findings (e.g. the 415) still appear because they
  are `serve`'s answers seen directly — §7.3 says so. New `reread`
  parameter on `audit.audit()` is the seam. The committed `audit/*.md`
  reports were not regenerated (no Z4 capture hits a mismatch). Audit
  tests ran locally (24, none skipped). CI 38321569193 green. Run 2 done;
  run 3 (B7-Z3 → B7-Z5) is unblocked.
- 2026-10-13: run 2 confirmed (B3a's two points, B5's `Connection: close`,
  B6's reading); B4a and B5a added from run 2's open items and placed
  before the audits, because B4a changes how the audit reads a capture.
- 2026-10-13 B4a (7275b12): awaiting decision, `OPEN_QUESTIONS.md` §7.
  Premise wrong for the audit half: since B4 a manifest with an absolute
  or `..` entry fails `verify`, and SPEC §7.2 refuses an unverified run
  (exit 2, no report) — tried on fixture copies, the refusal names the
  entry. The live defect is `zoo replay`: it never runs the check, and
  `raw/../../../outside.body` passes its `raw/` prefix filter. Options in
  §7; the sub-agent recommends 1 (keep §7.2, the audit test asserts the
  refusal; `replay.planned` gets B4's check). Run 3 stopped here per 0.1
  step 6; B5a does not depend on B4a. CI 38322519071 on the docs-only
  tip: macOS 3.12 failed `test_sixteen_hundred_bodies_cost_the_same_each`
  (510 vs 1333 us/body CPU, bound 2.0) — B2a's CPU-time fix does not hold
  on the macOS runner; a candidate row. The six other jobs passed.
- 2026-10-13: B4a decided (option 1; the audit half of the row was the
  maintainer's error, the replayer half stands); B2b added for the macOS
  cost test, ahead of everything else in run 3.
- 2026-10-13: B2b done (`63e44bc`), CI green on all seven jobs including
  macOS 3.12. The counted cost is every file the recorder opens per body
  through the `open_file` seam, as (mode, octets read, octets written) —
  not writes alone: B2a's mutation is a rescan, a read, which a pure write
  count (or open count) cannot see; the row's "file operations" allows it,
  and §3.6 states the definition. Maintainer to confirm the reading.
- 2026-10-13: B4a done (`3dcd17a`), CI green on all seven jobs. B4's
  check is `manifest.outside_run`; `manifest.misplaced` applies it to every
  `bodies`/`files` entry on both sides, and `replay.planned` calls it first
  (so the audit's `serve` gets it too). At the parent a `raw/../` entry was
  really sent. SPEC §7.2 now says the audit's refusal shows `verify`'s
  *first* problem — the bad entry only when it is the run's one fault —
  narrower than the decision's "names the entry"; maintainer to confirm.
- 2026-10-13: B5a done (`558ec4a`), CI green on all seven jobs. SPEC §3.7
  ends in a table of every framing case. At the parent, a POST with both
  headers was read by its length and its chunk frames drew a stray `501`.
  Two shapes no rule covers, left undecided (candidate rows): two
  `Content-Length` headers (read by the first), and `int()` accepting
  `+5`, ` 5`, `5_0` as a length.
- 2026-10-13: B7-Z3 done (`a180f06`), CI green on all seven jobs. One
  finding per report (spanweave-live: every protobuf body answered 415,
  L1 again); probes L3, S3 again, S6–S10 added, observed only. B7-Z5's
  status `awaiting B6` read as `todo` (B6 is done). The row's premise "the
  599 `Attributes dict is full` lines" is not in the record: nothing under
  `captures/z3/` holds those lines, so S8 says the audit cannot tie them to
  a span. The figure stays in the row as the operator's report, not a
  capture fact.
- 2026-10-13: B7-Z5 done (`54703f2`), CI green on all seven jobs. F1 per
  report (L1 again); S3, S7 again; L4, S11, S12, S13 new. The row's premise
  "identical real and recorded bodies" was wrong: the two `raw/0001.body`
  files are 5,934 bytes each and differ in 380 bytes (json bodies and
  sha256s differ too), and the graphs differ at least by trace id — row
  corrected. `Quiet`/`RootEnded` are not observable from the audit (it
  passes no `--quiet`/`--root-grace`/`--cap`), nor is span status in the
  report; both marked *to establish* in PROBES.md. Run 3 done.
- 2026-10-13: run 3 confirmed; B5b from B5a's remainder; B6a and B7r from
  the audits' own blind spots (L3, L4, S6, S10, S11, S12 all "to establish"
  because the report could not show it). Run prompts now start `Run N of
  WORKPLAN.md` so the watcher can read them.
- 2026-10-13: B5b done (`a48dfcc`), CI 38407030173 green on all seven
  jobs. Lengths go through `sink.declared_length`: each value trimmed of
  SP/HTAB, then ASCII `1*DIGIT`; repeats count only if all equal. Row
  premise corrected: a literal leading space (` 5`) never reaches the sink
  as part of the value (the stdlib parse drops it; RFC 9110 §5.5, SPEC
  §2.3), so the test uses a vertical tab, which `int()` ignored; a trailing
  SP/HTAB (`5 `) is still a length — maintainer to confirm. Left open, a
  candidate row: an obsolete folded `Content-Length:` with ` 5` on the
  next line is framed by `5` by the stdlib, while `headers.json` records
  an empty value and lists ` 5` as unparsed.
- 2026-10-13: B6a awaiting decision (`a8502c3`, `OPEN_QUESTIONS.md` §8).
  The row's premise "the receiver's documented defaults" fails: at the
  pinned spanweave-live `cddc694`, `--quiet` and `--root-grace` are
  `type=float` with no default, `serve --help` names none, and the README
  says the number is the caller's (its 30 / 5 are examples). Options in §8;
  the sub-agent recommends 1, `--quiet 0 --root-grace 0` (deterministic).
  Every policy run still needs `--requests N` or `serve` never stops. The
  per-node table half of the row does not depend on the question and was
  not started (one commit). Nothing compares committed `audit/` reports to
  a fresh audit, so B6a can land without B7r. CI 38407522096 green on
  `a8502c3`. Run 4 stopped here per 0.1 step 6; B7r awaits B6a.
- 2026-10-13: B6a decided (option 1 over a timed replay; the "documented
  defaults" premise was the maintainer's); B5b confirmed; B5c added from
  B5b's open case. Run 4 resumes B5c → B6a → B7r.
- 2026-10-13: B5c done (`9bcbaa0`), CI 38410939714 green on all seven
  jobs. `sink.folds_a_length(head)` reads the record's CRLF split: an empty
  `Content-Length:` followed by an SP or HTAB continuation is unframed; a
  digits-then-fold value was already unframed at the parent. Left open, a
  candidate row: the stdlib also splits header lines on a bare CR or LF,
  so it can still frame by a length the record does not show —
  `Content-Length:\n 5` (record value `\n 5`) and `X: a\rContent-Length: 5`
  (no `Content-Length` in the record). Not written to OPEN_QUESTIONS.
- 2026-10-13: B6a done (`07285bd`), CI 38412476908 green on every job,
  `audit` included. Choices the row did not settle, for the maintainer to
  confirm: `audit.audit()` takes a required `sleep` seam (§7.6); the two
  policy runs yield no findings, and one that fails makes the audit exit 1
  while step 3 still runs; `completed` events carry no policy or
  generation field, so "reason" is `detail` up to its first colon and
  "generation" is counted from the receiver's own events (`forgotten`
  resets it). Decision premise weaker than stated: `serve` ticks after
  every request, so at `0` the policies fire at the same tick timed or
  untimed — `--timing` costs wall clock (Z3 real ~23 s) and does not
  change the sequence. A trial (scratchpad only) observes L3: on Z3 real
  `--quiet 0` makes 4 generations with 3 `late_arrival`, `--root-grace 0`
  completes once at the last request; Z5 real's node table shows its two
  `error` tool nodes with their exception events. B7r is unblocked.

## 5. Origins

| ID | Origin |
|---|---|
| B0, B2–B6 | Qodo's review of PR #1 (comment 6127903067, 2026-10-12): 12 bugs, 0 rule violations. |
| B1 | The close review's thread (`TASKS.md`, series 1): `test_the_collector_killed_by_hand_mid_capture_is_a_problem` failed once in the PR run at `e50a56e` on a port taken between pick and bind, green on re-run. |
| B7, B8 | `ROADMAP.md`: the per-project checklist, step 4. |
