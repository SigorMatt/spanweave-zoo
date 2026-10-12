# TASKS.md — the registry between series

`CLAUDE.md` names this file: while a series is open its execution state lives in
a `WORKPLAN.md`; at the close that file is deleted and what outlives it lands
here — one line per batch with the commit(s) that closed it, the series'
decisions log and resume notes folded in verbatim, and the threads the next
series inherits. Nothing here is normative: `SPEC.md` says what the zoo does,
`CLAUDE.md` how work is done, `OPEN_QUESTIONS.md` why a question was answered
the way it was.

---

## Series 1 — the stranger's-trace series (2026-10-09 → 2026-10-12)

Branch `zoo`, opened from `main` at `d33059e`. The plan as it stood at the
close is `git show 22be077:WORKPLAN.md`; its §1 rows are the full text of each
batch below. The reviews it took are kept byte for byte under `reviews/`
(`reviews/SHA256SUMS`, 25 files: four review files and the 21 section files
the first three were assembled from; `cd reviews && sha256sum -c SHA256SUMS`).
The fourth is the scoped review of the close, below. The audit's
findings are the next series' probes, in `PROBES.md`.

### Registry

| ID | Batch | Closed by |
|---|---|---|
| A0 | Repository skeleton, on `main` | `d33059e` |
| A1 | The sink records bytes, and nothing else | `69fb6bd` |
| A2 | The Collector re-encodes beside the raw | `8c8299f` |
| A3 | The capture is a manifest, immutable | `9074ecd` (replaced `c965c9b` by a force-push, before the rule against it existed) |
| A3a | A capture exists only once it is ready, and a refusal writes nothing | `2b3c499` |
| A3b | The manifest is written once, at the end, and covers every file | `810f2db` |
| A3c | The header octets are the record | `8af242d` |
| A3d | `verify` refuses what it did not check, and CI checks something | `52c33ba` |
| A0a | The README is true, the licence exists, and the open question has a home | `91e91af` |
| A0b | CI proves the Collector claim | `222825f` |
| A4 | The replayer re-sends what was captured | `0c1e538` |
| A3e | Ctrl-C stops the capture and nothing else | `89b8dbf`, `9f23d12` |
| A3f | The manifest is sealed, and the parse cannot invent | `46b2c15` |
| A4a | Replay sends the captured head | `29c9d5c` |
| A0c | The README survives its own rehearsal | `c48e093` (question `af667c8`, `OPEN_QUESTIONS.md` §4) |
| A3g | The run-2b review's `next batch` items, closed | `487bbc1` |
| A5 | The audit: every capture through spanweave-live and spanweave, and what broke | `f60f69c`, `701fc80` (question `639485a`, `OPEN_QUESTIONS.md` §5) |
| A6 | The series closes | the `close:` commit that adds this file and deletes `WORKPLAN.md` |

Not a batch, and in the series' history: `47cb06c`, the operator's Z4 captures
(`real` and `recorded`), taken with the README's commands.

### Threads the next series inherits

Registered here at the close, as the decisions log and the three reviews ask.
None is acted on in this series. Each says where it was raised.

**From the decisions log and the resume notes.**

- **macOS wall-clock cost test** (decision 2026-10-12, "CI"):
  `test_sixteen_hundred_bodies_cost_the_same_each` failed once on the macOS leg
  at A3g (675 → 2,168 µs/body on the runner) and passed on a re-run of that job
  alone with no code change. A wall-clock ratio on a shared runner is not a test
  of the recorder. **Fix the registry names:** measure the per-body cost by CPU
  time (`time.process_time`) or by counting the writes per body, not by wall
  clock. Until then a macOS failure of this one test, green on a re-run with no
  code change, does not block `done`. (Same root as run-2 thread A3b-5.)
- **A3g's four readings where SPEC was silent** (decision 2026-10-12, "A3g"),
  open for the scoped review of the close: a head with no CRLF carries no
  `request_line`/`method`/`path` (`headers: []`); the `forward` seam is
  `(head, body)`; the README's readiness `timeout` is 60 s; `Trailer` is in
  SPEC's hop-by-hop list.
- **A5's four items for the scoped review of the close** (resume note
  2026-10-12, A5): (1) CI gained a seventh leg, `audit`, which the row did not
  name; (2) SPEC §7.4's owner table is the batch's reading, notably that the
  unclaimed root counts against both spanweave and spanweave-live; (3) the
  reports differ between runs in the `listening` port and the `completed` clock
  readings, stated in their method section; (4) `CLAUDE.md` rules 6 and 8 named
  only two of the three gated libraries — **made true in A6's commit**, which
  writes the decided third name (`agentgolden`) into both; the other three stay
  open for the review.
- **A3b's `started_at` preference** (`OPEN_QUESTIONS.md` §3): a project
  manifest present but with no readable `started_at` is kept **and** recorded as
  a problem; the maintainer may prefer `project_manifest: null`, or no problem.
  Open as a preference, blocking nothing.

**Run-1 review** (`reviews/REVIEW-2026-10-10.md` §2, "Thread"), T1–T25, registered
at close by the decision of 2026-10-10. Acted on in the series: T1 and T24 (A3d),
T5, T18 and T20 (A0a), T25 (A0b), T17 (A0c: the Layout lists `json/NNNN.headers.*`).
Open, as the review states them:

- T2 `make check` never type-checks `tests/`; `strict = false` for `tests.*` is dead config.
- T3 `README.md` called `zoo verify` "the capture re-hash" at A0, where it re-hashed nothing.
- T4 The README says both root copies are contract version 1.1; `ZOO-BRIEFS.md` carries no version marker.
- T6 §4's "both runs are vacuous" for A1 over-claims: two `test_cli.py` tests failed the parent by assertion.
- T7 The sink's answers carry a `Date` from the stdlib's real clock, which the AST clock gate cannot see.
- T8 The exporter's `200` is serialized behind the forward (`200 after 5.01s` against a wedged Collector); no test asserts the bound.
- T9 No `fsync`: "on disk before the forward" means visible, not crash-durable.
- T10 The manifest-equals-`VERSION` test is tautological for the pin's value; the `SHA256SUMS` cross-check is what holds it.
- T11 `.gitignore`'s "(A2)" Collector line was pre-added in A0.
- T12 A capture that fails to bind after labelling verified green as `kind=real, 0 bodies`; `MANIFEST.json.partial` reported as unlisted when verify races a live capture.
- T13 SPEC §1.1's "two things named here" list omits `headers.json`, the third document read.
- T14 No gate for the no-clock invariant; it is grep-and-discipline.
- T15 `--project probe` is accepted silently though `--help` prints `z1 ... z6`.
- T16 The Collector download lands as 389 MiB on disk; the README says ~100 MB.
- T19 The plan's "push once per run" contradicted "CI green per batch"; the next series' plan should state one.
- T21 Suite totals in the resume notes are the builder's word, unverifiable from git.
- T22 A3's note cites a brief requirement absent from its row.
- T23 "Holds only by counting the keystroke" describes a miscount as a tightening.

**Run-2 review** (`reviews/REVIEW-2026-10-10-run2.md` §2 "Thread" and §3),
registered at close per its §5 item 4:

- A3b-4 The Collector log echo bypasses `Progress`: not flushed per line, no BrokenPipe guard in the drain thread.
- A3b-5 The cost test reads `perf_counter` against a real-time bar (see the macOS thread above).
- A3b-6 `EXPORT-CONTRACT.md` does not require an offset on `started_at`, and an offset-less one fails every capture.
- A3a-4 The connect half of readiness is untested.
- A3a-5 A refusal prints the Collector's log twice.
- A3a-6 A failing stub test leaks its 600 s child.
- A3d-3 One `zoo capture` hang after a double SIGINT (0 in 10 retries).
- A3d-4 `.gitattributes` does not cover `EXPORT-CONTRACT.md` / `ZOO-BRIEFS.md`, so an `autocrlf=true` clone fails `test_readme`.
- A3d-5 The fixture's project `started_at` is after the capture's `ended_at`; a seconds-precision `started_at` in the capture's first second is rejected.
- A3d-6 The `Makefile` comment on `gates` still says "except audit.py" (a basename, where the gate exempts a path), and names only two of the three gated libraries.
- A0a-2 README command extraction depends on the fence being labelled `bash`.
- A0b-2 The check legs' "skips loudly" is a count only; there is no `-rs`.
- A4-3 No test distinguishes manifest order from directory order.
- A4-4 After a bad timestamp, the next replay gap is measured from it.
- OP The supervisor form's log location and the pet project's committed `MANIFEST.json` (the log moved by A0c; the rest as the review states).
- P-2 … P-10 Plan-hygiene threads (review §3); P-10 is T19.
- (A0a-3 and A0a-4 are closed: `WORKPLAN.md` is gone, and A0c fixed the digest wording.)

**Run-2b review** (`reviews/REVIEW-2026-10-11.md` §2 "Thread" and §3),
registered at close per its §5 item 3:

- A3e: "214 s → 46 s" is pytest time and red-vs-green, not a speed-up (P-3); `89b8dbf` stays red on macOS on `zoo` (P-9); the timed waits sit outside the `sleep` seam; Ctrl-C during the readiness wait gives a traceback and exit -2; a `TimeoutExpired` after SIGKILL is uncaught, so the manifest is never finished; a Collector exit during the flush counting as a problem narrows the decision (P-10).
- A3f: the obs-fold note; two decisions in one commit; the fixture's `collector.log` is on the real wall clock; the fixture's project `started_at` is after its `ended_at`.
- A4a: an LF-only head carries the old Host to the new target (T-A4a-1); `collector.py`'s `_accepts` is a third outbound connect behind no named seam (T-A4a-2); an over-long hand-edited body is delivered as an extra request (T-A4a-3).
- A0c: the README's anchor rationale names a line the pattern does not contain (A0c-6); the `../streaming-concierge` sibling-checkout assumption is unstated (A0c-7).
- Plan: "ten of ten locally" was unevidenced (P-4); `b012fe5` is a `plan:` commit that also edits `OPEN_QUESTIONS.md` (P-5); option 2's maintainer provenance exists only in a builder commit, and a maintainer-signed decision row was rewritten in place (P-6); `OPEN_QUESTIONS.md` §4 lacked "where the decision now lives" (P-7).
- Operator: `collector.log` publishes the machine's UTC offset (OP-1).

**Close review** (`reviews/REVIEW-2026-10-12.md`, "Findings" and "A5's review
items"), the scoped cold review of the close, taken after it and decided
2026-10-12 (b). Its dispositions, each with the commit that closed it:

- R-1 A live/batch divergence reaching the report had no test: accepted, a
  test drives one through `serve_command` (`partition_findings`' owner
  mutation now fails it). `1ddf386`.
- R-2 PROBES.md L2 cited only the route: accepted, it cites spanweave-live
  `cddc694` §1.1/§1.5 beside §4.3/§5.4/§8.5, names their tension, says its
  command runs without `--deltas`, and notes what `serve --deltas` writes.
  The `docs:` commit that archives this review.
- R-3 The hop-by-hop list's citation: accepted, the list is the zoo's own with
  a reason per name, `Proxy-Connection` and the fields `Connection` names are
  dropped. `441e1d5`.
- R-4 `CONTRIBUTING.md:10` read `WORKPLAN.md` as present: accepted, made
  conditional, pointing at this file between series. The `docs:` commit that
  archives this review.
- R-5 Stale "two" for three: accepted, every item (`pyproject.toml`,
  `spanweave_zoo/__init__.py`, the gate test's name), and `pyproject.toml`'s
  agentgolden comment cites step 5 at `SPEC.md` §7.3 and its seam at §7.6.
  The `docs:` commit that archives this review.
- R-6 701fc80's test was red on its parent by a collection error, not the CI
  skip: accepted, the shadow packages raise `ModuleNotFoundError`. `1ddf386`.
- R-7 The audit's uninjected bounded waits: ruled — a bounded wait on a stdlib
  timeout with a named constant is not a clock read; the audit's seams and
  each timeout are written as `SPEC.md` §7.6. The seventh CI leg, `audit`, is
  accepted. The `docs:` commit that archives this review.
- R-8 `selftest.sh`'s reused `$TMP/repo4`: **owned by spanweave-ops**, not this
  repository; not acted on here.
- A5's four items: (1) the seventh leg accepted (R-7); (2) §7.4's owner table
  counting the unclaimed root against both libraries accepted; (3) the
  reports' run-to-run difference confirmed exact; (4) CLAUDE.md rules 6/8 done
  in the `close:` commit. A3g's four readings: 1–3 stand, 4 is R-3. These
  close the two threads above that were left open for this review.
- The no-skip guard's hint named the wrong cause on `f60f69c` (it said the
  binary was absent; a module-level skip was): `701fc80` did not change it.
  `tests/collector_check.py`'s hint names both causes. The `docs:` commit
  that archives this review.

### Decisions log (`WORKPLAN.md` §3, folded verbatim)

Section references inside (`§0.1`, `§3`, `§4`, a row) are to `WORKPLAN.md` as
it stood at `22be077`.

| Date | Batch | Decision | By |
|---|---|---|---|
| 2026-10-09 | series | The fixture is what the exporter sent, not what the receiver understood: raw bytes are the record, the Collector's JSON re-encoding is a standards-made convenience kept beside them, and the receiver's answer to raw protobuf (expected: 415 today) is the audit's first finding, not something the zoo works around. The zoo fixes nothing; findings go to the owning repo's next series as probes. Pet projects know nothing of spanweave and are given only `EXPORT-CONTRACT.md` and one brief. | maintainer |
| 2026-10-10 | review run 1 | The four blockers (F1–F4) and the twelve `next batch` items are closed before A4 is dispatched and before Z4's real run, as six short batches made by the builder from the review file. Threads T1–T25 are registered at close; T1, T5, T20, T24 and T25 are acted on now because they shape run 2. | maintainer |
| 2026-10-10 | manifest timing (F4) | The project's `MANIFEST.json` is copied **at the end** of the capture, after `Ctrl-C`, so the copy is the one the recorded run wrote. If its `started_at` predates the capture's `started_at`, or the file is absent, the capture is finalized with `project_manifest: null` and a `problems` entry naming why, and `zoo capture` exits non-zero; `zoo verify` fails on any capture with `problems`. A capture is never silently fine. | maintainer |
| 2026-10-10 | readiness and refusal (F2, F8) | A capture exists on disk only once it is ready: the run directory is created after all three listeners accept **and** the Collector child is alive with its own ready line in its log; a refusal for any reason before that writes nothing. During a capture, the Collector child exiting is a failure recorded in the manifest and reported at exit, never a silent empty `json/`. | maintainer |
| 2026-10-10 | the record (F6, F7, F9, F10, F12) | The header octets are the record: `NNNN.headers.raw` holds the request line and header block exactly as received; `NNNN.headers.json` stays as the stdlib's parse for convenience and SPEC §2.3 says which is "unmodified". Bodies are journalled to `bodies.jsonl` during the capture and the manifest is assembled once at the end; it lists **every** file in the run directory except itself with a sha256, so `zoo verify` covers headers, raw and json alike, and checks `kind` and `ended_at`. Progress lines are flushed on every write; a closed stdout finalizes the manifest and exits rather than tracebacks. | maintainer |
| 2026-10-10 | verify (F1, F11, T24) | `zoo verify <path>` exits non-zero on anything it did not check: a path that is not a capture is an error, a capture without `ended_at` is a failure naming the directory and the command that removes it. A capture with zero bodies and an `ended_at` is valid. A tiny real capture (one protobuf body through the real tee) is committed under `tests/fixtures/capture/` so CI's `verify` checks something. | maintainer |
| 2026-10-10 | CI (T25) | A sixth CI leg, `collector (ubuntu-latest)`, runs `make collector` (release download cached by sha) and the real-Collector tests, so A2's claim is proven on a machine that is not the maintainer's. | maintainer |
| 2026-10-10 | protocol (F14, T18, T20) | A batch that reaches "a spec decision, not a patch" ends `awaiting decision` with an `OPEN_QUESTIONS.md` entry, never `done`; the repo gains `OPEN_QUESTIONS.md` with F4 recorded as its §1. Force-pushing a series branch is forbidden: an amended batch is a new commit, and the replaced sha is recorded in §4. `c965c9b` → `9074ecd` is recorded now. | maintainer |
| 2026-10-10 | run 2 | A3a → A3b → A3c → A3d → A0a → A0b → A4, then stop for a cold review. Then the operator captures Z4 (`real` and `recorded`). Run 3 = A5 → A6. §2's gate on a `real` capture moves from run 2 to A5. Licence: MIT, in A0a. | maintainer |
| 2026-10-11 | Ctrl-C | The decision of 2026-10-10 that "the Collector child exiting is a failure" collided with how a terminal delivers Ctrl-C to the foreground process group. The Collector child is started in its own session (`start_new_session=True`), so only `zoo capture` receives the terminal's SIGINT; `zoo capture` then stops the Collector itself — SIGTERM after the final flush, SIGKILL after a bounded wait — and a Collector exit during that shutdown is not a problem. A Collector exit at any other time still is. The test signals the **process group**, as a terminal does. | maintainer |
| 2026-10-11 | the seal | A capture's manifest carries `seal`: the sha256 of the manifest's canonical JSON with `seal` absent. `zoo verify` recomputes it and fails on any difference, so `kind`, `problems`, `project_manifest` and the file list cannot be changed by hand afterwards. Z4's captures are taken only after the seal exists, because a seal cannot be added to a capture after it is taken. | maintainer |
| 2026-10-11 | the parse | `NNNN.headers.json` is derived by the zoo from `NNNN.headers.raw` with a strict split on CRLF only — a bare CR or LF inside a value stays inside the value — never from the stdlib's parse, so the json cannot assert a header the client did not send. The stdlib's parse is still what the sink *handled* the request with; SPEC §2.3 says so. | maintainer |
| 2026-10-11 | replay | `zoo replay` sends the captured head bytes itself over a socket, substituting only the `Host` line, followed by the captured body; it does not go through `http.client`. The replayed head is byte-identical to `.headers.raw` except `Host`, and a test holds that. | maintainer |
| 2026-10-11 | the run's record | The Collector's stdout and stderr go to `collector.log` in the run directory, listed and sealed like every other file, so the operator's terminal shows the readiness line and the per-body lines only. The body count reports bodies, not files. The README's optional log-to-file variant writes outside the checkout and outside the run directory (`"${TMPDIR:-/tmp}"/zoo-capture-<run-id>.log`); the operator log is not part of the record, because `collector.log` is. Amended 2026-10-11 (A0c, `OPEN_QUESTIONS.md` §4, option 2): "under the run directory" was false against the code. | maintainer |
| 2026-10-11 | run 2b | A3e → A3f → A4a → A0c, then a scoped review of the four (aux) with the operator rehearsal repeated; then the operator captures Z4 (`real` and `recorded`); then run 3 = A5 → A6. | maintainer |
| 2026-10-11 | header rule | A3f's unparsed-line rule is **ratified** as the derivation of `NNNN.headers.json` from `NNNN.headers.raw`: split on CRLF only; a line is a header when the text before its first colon is a non-empty token, with spaces and tabs trimmed from the value; every other line verbatim under `unparsed`, absent when empty. Amendment, not affecting the Python exporter's head: the request line is recorded verbatim under `request_line`, so nothing after the path is dropped; an LF-only head is one `unparsed` entry. The raw file is the record; the json is a derivation and may be re-derived from the raw by a later rule without touching the capture. | maintainer |
| 2026-10-11 | the seal | The seal catches accidental and incidental edits; a manifest resealed by hand verifies. SPEC says exactly that and no more. | maintainer |
| 2026-10-11 | A3e | `9f23d12` under A3e was the right call under §0.1 (a batch whose CI fails is dispatched again with the fix on top); the macOS job went red → green, not slow → fast, and §4 says so. | maintainer |
| 2026-10-11 | run 3 | After this commit the operator captures Z4 (`real`, then `recorded`) with the README's commands and commits the captures. Run 3 = A3g → A5 → A6. | maintainer |
| 2026-10-12 | A5 | **Option 1.** `agentgolden` is pinned by git sha in the `audit` extra beside the two existing pins: `agentgolden @ git+https://github.com/SigorMatt/agentgolden@aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0; requires `spanweave>=0.9.1,<1.0`, which `spanweave@fec7da27` = 0.9.1 satisfies, so the resolver adds no second spanweave). Relock. The audit must reproduce from `pyproject.toml` alone; a third recorded sha is the price, and it is the right one: agentgolden is the consumer the receiver series was built around, so its `Signature` on a stranger's graph is the smoke worth taking. | maintainer |
| 2026-10-12 | A5 | **The import gate confines agentgolden exactly as it confines the other two.** `agentgolden` joins `ANALYSER_MODULES` in `tests/gates.py`; it is importable from `spanweave_zoo/audit.py` and nowhere else, and the gate's test covers the third name. The audit report's header records all three pinned shas, so every finding that cites step 5 carries agentgolden's. | maintainer |
| 2026-10-12 | A5 | **Step 5 stays as written**: `agentgolden.signature.signature(graph)` on each final graph, no rules evaluated. A raise on any graph is a finding like the others — reproduction with the capture path and the command — naming the repo that owns it (agentgolden if the signature code fails on a graph spanweave built; spanweave if the graph itself is the cause). Not fixed here. | maintainer |
| 2026-10-12 | A5 | **Completion policy: no decision needed**, as the batch found. Step 2 uses `spanweave-live serve --requests N` at the pinned sha; the end of input runs `Run.finish()`, which is the `Cap(0)`-at-end the row names. The report states this once in its method section. | maintainer |
| 2026-10-12 | CI | **`test_sixteen_hundred_bodies_cost_the_same_each` on the macOS leg.** A wall-clock ratio on a shared runner is not a test of the recorder; the builder's call (re-run of that job alone, green with no code change, logged) was right and is ratified **for this test only**: a macOS failure of this one test, green on a re-run with no code change, does not block `done`. A6 registers it in `TASKS.md` for the next series with the fix the registry entry names: measure the per-body cost by CPU time (`time.process_time`) or by counting the writes per body, not by wall clock. Nothing changes in this series. | maintainer |
| 2026-10-12 | A3g | A3g's four readings where SPEC was silent (no-CRLF head carries no `request_line`/`method`/`path`; `forward` seam `(head, body)`; README readiness timeout 60 s; `Trailer` in the hop-by-hop list) stand until the scoped review of the close; none of them touches A5. | maintainer |

### Resume notes (`WORKPLAN.md` §4, folded verbatim)

Section references inside are to `WORKPLAN.md` as it stood at `22be077`.

- 2026-10-09: series opened. Nothing has run. The pilot pet project (Z4,
  streaming-concierge) is being built elsewhere; A3 is the point at which
  it can make its real run.
- 2026-10-09 A0 (d33059e): skeleton landed on `main`, CI green on all five
  legs (ubuntu 3.11/3.12/3.13/3.14, macos 3.12); `zoo` branched at the same
  sha. The repository did not exist on GitHub and was created public; the
  root `EXPORT-CONTRACT.md` / `ZOO-BRIEFS.md` are contract **1.1** while the
  Z4 pilot was built against 1.0, so the README states both sha256s, names
  the version, and cites the contract's own changes-from-1.0 section — the
  A0 row's "byte-identical to the ones handed to the projects" holds for
  every project started from now on, not for Z4.
- 2026-10-09 A0: `zoo verify` today **refuses** any capture directory it
  finds (exits non-zero, saying manifest re-hashing is SPEC §5 / A3) rather
  than hashing it. It never reports an unchecked capture as verified, but
  A1's row requires verify to pass on a real capture and fail after one
  byte changes, so A1 replaces the refusal with the real check. A3's row
  was annotated: `make check` already depends on `verify` as of A0, one
  batch earlier than that row implied.
- 2026-10-09 A0: no `LICENSE` and no `license` field in `pyproject.toml`.
  The A0 row did not say and the batch did not invent one; both sibling
  repos are MIT. Awaiting the maintainer; it blocks nothing in run 1 and
  should land before the A6 PR.
- 2026-10-09 A1 (69fb6bd): the sink records and parses nothing; CI green on
  all five legs. The digest tension in A1's row (verify needs a recorded
  hash; §0.6 puts it in the manifest; the manifest is A3's) was resolved by
  having the sink write `MANIFEST.json` incrementally with **`bodies:
  [{file, sha256, bytes}]` only** — one home for the digest, nothing copied
  into `headers.json`. `content_type`/`content_encoding` were deliberately
  **not** copied into the manifest: SPEC §1.1 says the sink does not look at
  the content type except to echo it, and both values are already verbatim
  in `NNNN.headers.json`. A3 still owns the rest, and SPEC §5 now lists it.
- 2026-10-09 A1: "a body present on disk but absent from the manifest fails
  verify" was left **deliberately unimplemented** so that A3's row test is
  not pre-satisfied. A3's row stands as written.
- 2026-10-09 A1: for A2 — `zoo sink` defaults to `--port 4318 --host
  127.0.0.1` with `--out` required, and refuses a `--out` that already
  holds a body. The tee's two sinks must therefore be given **different**
  `--out` directories (`raw/` and `json/`); two Recorders on one directory
  would share `rejected/` and `MANIFEST.json`, which A2 must specify rather
  than discover. `received_at` comes straight from the `now` seam, so A3's
  `started_at`/`ended_at` can reuse `cli._system_clock` unchanged.
- 2026-10-09 A1 (process, for the cold reader): the batch ran its parent
  check against `d33059e` rather than its own derived parent `0bdab8e`
  (`69fb6bd^`). Neither contains the sink, so both runs are vacuous and the
  named mutation is what carried the bar; no re-run was ordered. §0.2's
  derived-parent rule is unchanged and still binds later batches.
- 2026-10-09 A2 (8c8299f): the stock Collector re-encodes beside the raw.
  `otelcol-contrib 0.162.0` pinned with per-platform sha256 copied from each
  release asset's own `.sha256`; `make collector` fetched and verified it for
  real; the binary is gitignored. The integration test ran against the real
  binary: a hand-built OTLP protobuf through the tee comes back as
  `json/0001.json` with the **same ids** (trace `4bf92f35…4736`, span
  `00f067aa0ba902b7`). `make check` is green **both ways** — 94 passed with
  the binary, 91 passed + 3 skipped without, verified by moving it aside.
- 2026-10-09 A2: **two row premises were wrong and the row is corrected
  above.** (1) "`otlp` receiver on 4317/4318" collides with the raw sink,
  which A1 put on 4318; the config's endpoints are now
  `${env:NAME:-default}` whose defaults are exactly 4317/4318/4319 and
  `zoo capture` moves the Collector's HTTP receiver to 4320 (SPEC §4.2 says
  why). (2) `otlphttp` is a deprecated alias at 0.162.0; the config uses
  `otlp_http`, the same component.
- 2026-10-09 A2: manifests, for A3 — **one `MANIFEST.json` per run
  directory**, written by both recorders under one lock keyed by the run
  dir. `bodies` carries `raw/NNNN.body` and `json/NNNN.json` interleaved in
  record order; A1's three-key entries are untouched. A2 added only
  `collector_version` (the pin) and `forwards` (delivery, not bytes). The
  two sinks have separate `--out` (`raw/`, `json/`) and separate rejected
  dirs (`rejected/`, `rejected-json/`).
- 2026-10-09 A2: a real defect was found by running it, and fixed in the
  same commit — `SIGINT` did **not** stop a capture (the main thread parked
  in an untimed `Event.wait` while the signal went to a `select` thread),
  leaving the Collector holding its port. Handlers are installed and the
  wait polls (SPEC §4.6). This is the kind of thing only the real binary
  surfaces; A3's five-command README section must be exercised the same way.
- 2026-10-10 A3 (9074ecd): the capture declares what it is and verify
  checks both directions. CI green on all five legs; `make check` green with
  the binary (121 passed) and without (118 + 3 skipped). The parent run was
  **not** vacuous for once: on `4122152` an unlisted body on disk made
  `verify` exit **0**, and `verify <run dir>` printed "no captures" and
  exited 0 — both are 1 now. A1's missing `content_type`/`content_encoding`
  are carried across by `manifest.finish()` from each body's own
  `headers.json`, so the sink still inspects nothing; **SPEC §1.1 was
  amended** in the same commit to say so rather than leave the two texts
  contradicting. The row no longer counts commands: it cites the README,
  which A0a makes complete and runnable as printed.
- 2026-10-10 A3: a second real defect found by running it — the sink's
  "already holds a body" refusal globbed `*` + suffix, and the json sink's
  suffix is `.json`, so `0001.headers.json` counted as a body and a re-used
  run id was refused with "2 body file(s)". Bodies and headers are counted
  apart now; a directory holding only a headers file is still refused
  (SPEC §3.1 amended, two tests).
- 2026-10-10 **A3 — open for the maintainer, and it affects the Z4
  handover.** The brief required the capture to fail loudly at the *start*
  if the project's `MANIFEST.json` is missing, but `EXPORT-CONTRACT.md` has
  the project write its manifest *during* its run. So `zoo capture` copies
  the manifest the project's **previous** run left behind, and SPEC §5.3 and
  the README say that plainly rather than implying it belongs to the
  recorded run. Taking the copy at the **end** instead would make the
  manifest contemporaneous with the bytes; that is a spec decision, not a
  patch, and it is unresolved. Z4's first real run will carry a manifest
  from its recorded run unless this is decided first.
- 2026-10-10 **A3 — process.** That open question was A3's own halt trigger
  ("a rule or a policy `SPEC.md` and this file do not already state", §0.3
  and CLAUDE.md "Halt points"), so the batch should have ended `awaiting
  decision` with an `OPEN_QUESTIONS.md` entry rather than `done`. The status
  `done (9074ecd)` stays — what it shipped is right — and the rule is
  restated as a decision in §3 so a later batch halts instead of deciding.
- 2026-10-10 A3: `zoo verify` now accepts a single run directory — A4/A5 may
  rely on it. `manifest.set_collector_version` was folded into
  `manifest.label`.
- 2026-10-10: run-1 cold review read and decided (§3). The capture pipeline
  is right in shape and wrong in four places that would let a capture be
  quietly wrong (a foreign listener satisfying readiness; a refusal leaving
  a labelled manifest; verify exiting 0 on a path it never checked; headers
  recorded as a parse). All are closed before A4 and before Z4's real run.
  The manifest is copied at the end; the licence is MIT; CI gains a
  Collector leg; force-pushes are forbidden from here.

- 2026-10-10 A3a (2b3c499): the F2 race was real and worse than the review
  put it — on the parent, a foreign listener on the Collector's port did not
  refuse *at all*, because readiness was a connect-only probe. Readiness is
  now three listeners accepting **and** the Collector's own ready line in
  its own log, which required `collector/config.yaml`'s log level to go
  `warn` → `info` (the ready line is info-level). The tests drive a stand-in
  child process rather than the 100 MB binary, so they run in CI. Two
  corrections to the plan's vocabulary: this repo has **no `make
  conformance` target** — the §0.3 brief named one that does not exist, so
  the brief now says `make check` (which runs `zoo verify`) and `make
  install-check`, which is what A3a ran. And `problems` is written to the manifest
  now but `zoo verify` does not yet read it — that is A3b's row, and
  SPEC §4.6 says so, so A3b must also cover the manifest's new `problems`
  key when it makes verify cover every file.

- 2026-10-10 A3b (810f2db): the manifest is assembled once at `Ctrl-C`
  from `bodies.jsonl`, and the end-of-run copy of the project manifest
  settles F4. The row's cost criterion was met and the parent shows why it
  was worth asking: 1,600 bodies cost 273 µs → 288 µs per body (ratio
  1.05); on the parent the same run went 572 µs → 4,258 µs (ratio 7.44),
  so the old per-POST manifest rewrite was quadratic in the body count.
  Two consequences a later batch inherits: `zoo sink` now writes **no**
  manifest during a run and assembles it in its own `finally` (a capture
  without `ended_at` no longer verifies; SPEC §5.6), and the manifest has a
  new `files` key — bodies stay in `bodies`, every other file in the run
  directory gets one `files` entry — so A3c's `NNNN.headers.raw` is covered
  without a change to verify.
- 2026-10-10 **A3b — one edge the F4 decision did not cover**, decided as a
  corollary rather than halted on: a project manifest that is present but
  has no readable `started_at`. A3b keeps the document **and** records a
  problem, so the capture fails verify rather than passing with an
  undatable manifest (SPEC §5.3's four-outcome table). That follows from
  "a capture is never silently fine" plus losslessness, but the maintainer
  may prefer `project_manifest: null` or silence there; it is open as a
  preference, not as a defect.

- 2026-10-10 A3c (8af242d): `NNNN.headers.raw` is the head octets as the
  client sent them, kept by a wrapper on the request stream as `readline`
  reads them, written **before** the parse; `.headers.json` stays beside it
  as the stdlib's parse, and SPEC §2.3 now says which is which. The row's
  mutation is more load-bearing than it looked: writing the stdlib's
  *reconstructed* head to `.raw` is caught **only** by the bare-CR test —
  on a well-formed head the reconstruction is byte-identical, so the
  octet-identity test passes under the mutation. A degenerate case worth
  knowing before Z4's run: a bare CR early in a head makes the stdlib drop
  every later header, `Content-Length` included, so such a request records
  a zero-byte body — honest, and `.raw` is the file that explains it.
- 2026-10-10 A3c: two things A3d inherits. `Recorder.record` now requires a
  `head=` argument, and the startup refusal counts header files per file,
  so a one-request directory reports 2 — A3d's `tests/fixtures/capture/`
  must carry `NNNN.headers.raw` on both the raw and the json side or
  `verify` will flag a missing or unlisted file.

- 2026-10-10 A3d (52c33ba): `zoo verify` exits 2 on a path the operator
  typed that is not a capture, while the default `captures/` root still
  exits 0 when empty — `cli.verify(root, *, named=False)` keeps the two
  apart, and `make verify` and `install-check`'s out-of-repo `zoo verify`
  both rely on that. One real capture (one protobuf body through the real
  tee, both sides, heads raw and json) is committed under
  `tests/fixtures/capture/`, and CI's log now shows `make verify` reading
  it. A `.gitattributes` marks the fixture `-text` so the CRLF heads
  survive a clone — without it the record would be corrupted by checkout,
  which is exactly the failure A3c's octets guard against.
- 2026-10-10 **A3d — one criterion the row stated more strongly than a
  test can hold.** "Tests red on the parent for each" is true of three of
  A3d's four concerns; the README contract-sha test **passes** on the
  parent, because nothing has drifted yet — a drift test is green until
  something drifts. It was shown red by appending one byte to
  `EXPORT-CONTRACT.md` on the parent (reverted), which is the mutation
  form of the same evidence. A later row asking for a drift guard should
  ask for that demonstration, not for a red parent.
- 2026-10-10 A3d: `tests/gates.EXEMPT_FILES` became
  `EXEMPT_PATHS = ("spanweave_zoo/audit.py",)`, matched by path — so **A5
  must put the audit at exactly that path**. The fixture capture has no
  generator script on purpose: it is never regenerated, and its provenance
  lives in `tests/test_fixture_capture.py`'s docstring and SPEC §5.6.

- 2026-10-10 A0a (91e91af): docs only. The README's operator flow is a
  numbered list of the commands themselves, `uv sync --extra dev` first,
  and **every printed `zoo` command is now parsed by `cli._parser()` in a
  test** — which is how the batch found that the README's tee command was
  not runnable as printed (it was missing `--kind` and
  `--project-manifest`). `LICENSE` is MIT (holder as in both sibling
  repos), `license`/`license-files` are in `pyproject.toml`, and the wheel
  is asserted to ship it in `install-check`, so CI proves it off this
  machine. `OPEN_QUESTIONS.md` exists: §1 is the manifest-timing question
  **with** its resolution (§3's F4 decision, implemented by A3b), and §3
  registers A3b's `started_at` corollary as a preference, blocking nothing.
  No row or §4 note counts commands any more; they cite the README.

The three items A0a's row asked §4 to gain, recorded here by the builder
because a batch never edits this file:

- 2026-10-10 A2 (8c8299f) — the CI line its own note omitted: success on
  all five legs (ubuntu 3.11/3.12/3.13/3.14, macos 3.12).
- 2026-10-10 **a force-push happened before the rule existed**: `c965c9b`
  was replaced by `9074ecd` on `zoo` by force. §3's protocol decision now
  forbids that — an amended batch is a new commit on top — and §0.1 step 8
  says so. The replaced sha is recorded here, which is the remedy the rule
  asks for.
- 2026-10-10 `b913e2b`'s subject carries two clauses ("A3 done, run 1
  complete, and the project manifest's timing is open"). §0.1 step 5
  allows a second clause when it records something a reader needs, and the
  open question was that; T18 registered it so the allowance is visible
  rather than assumed.

- 2026-10-10 A0b (222825f): CI has a sixth job, `collector
  (ubuntu-latest)`, and A2's claim is now proven on a machine that is not
  the maintainer's: **18 s**, cold cache, logging `collector-check: OK -- 3
  tests ran against the real Collector, none skipped`. The guard reads
  pytest's junit-xml rather than its exit code, because **pytest exits 0
  when every selected test skips** — the exact shape of the failure T25
  was worried about. It also fails when nothing is selected, which is what
  caught the mutation (dropping the marker but keeping the `skipif`).
  Actions caches are branch-scoped, so the first run on any branch pays a
  cold 4 s fetch; the archive is now cached under `refs/heads/zoo`.
- 2026-10-10 **A0b — process, and a number that disagrees with itself.**
  The row required the job's duration in the commit body, which cannot be
  measured before the commit exists, so the batch measured it on a
  throwaway branch `claude/a0b-trial` with identical content (run
  38013503089, 15 s) and wrote that. `zoo`'s own run measured **18 s**;
  both cold-cache, the difference is runner variance. The branch and its
  caches are deleted (`git ls-remote` shows only `main` and `zoo`) and no
  force-push was involved. A row that wants a measurement in its own
  commit body should expect this, or ask for the number in §4 instead.

- 2026-10-10 A4 (0c1e538): the replayer sends a capture's bytes with the
  head from `NNNN.headers.raw` — the octets, never the parse — and reuses
  the tee's own `forward.HttpForward`, so §4.3's Host and hop-by-hop rule
  has exactly one home. Order comes from the manifest's `bodies`, not from
  sorting the directory. Its mutation is the sharpest of the run: building
  the request from `.headers.json` makes the replayer **tidy a head the
  wire refuses into one it accepts** — the parse truncates
  `otel\rpython/1.0` to `otel`, so the mutant sent a request no exporter
  ever made and exited 0. That is A3c's record-versus-parse distinction
  paying for itself one batch later.
- 2026-10-10 A4: the committed fixture capture holds **one** body, so the
  multi-body, non-2xx and bare-CR cases are crafted through the real sink
  inside the tests. Socket-level sends therefore live in tests, not under
  `spanweave_zoo/`, and the import gate stays green.
- 2026-10-10 **run 2 complete.** Seven batches, seven commits, CI green on
  every pushed tip (six legs from A0b on). No batch halted, no batch
  failed, no force-push. A5's prerequisite "A4 done" is met; it still
  waits on a `real` capture, which is the operator's next move, not a
  batch's. The replayer is the only thing a capture needs to reach
  `spanweave-live serve`, and `--json` is ready for A5's step 2.
- 2026-10-11: run-2 cold review read and decided (§3). The rehearsal with
  the real Z4 project captured correctly and then failed on Ctrl-C, because
  the 2026-10-10 "Collector exit is a failure" rule met the terminal's
  process-group SIGINT; the Collector now lives in its own session and the
  capture stops it. The manifest gains a seal before the first real capture;
  the header parse is derived from the raw head; replay sends the raw head.
  Run 2b is four batches; then Z4.
- 2026-10-11 A3e (89b8dbf, 9f23d12): Ctrl-C to the process group stops
  the capture, exit 0, no `problems`, ten of ten locally. 89b8dbf failed
  CI's macOS leg only: `http.server` does a reverse lookup on bind, which
  took tens of seconds on the runner, so a fresh `zoo capture` printed
  nothing in 60 s. 9f23d12 binds without the lookup (SPEC §3.7) and has a
  test; the macOS job failed at `89b8dbf` (four
  tests each at the 60 s limit) and passed at `9f23d12` in 46 s, as before
  A3e; the fix made it green, not faster. New commit on top, no
  force-push. The row's mutation said "in its own group"; the mutation
  that fails the test is the child left in the *parent's* group, corrected.
  Readings taken: a Collector exit is a problem until the zoo sends
  SIGTERM (a crash while forwards drain still counts); the flush is a
  bounded (10 s) wait for in-flight forwards; the count reads
  `N body/bodies in raw/, M in json/` for capture and verify alike (A0c's
  README must match); a `zoo capture` killed by SIGKILL leaves its
  Collector running, stated in SPEC §4.6.
- 2026-10-11 A3f (46b2c15): manifests sealed (SPEC §5 states the
  canonical form); `headers.json` split from `.headers.raw` on CRLF only,
  method and path from the raw request line. A rule the decision did not
  spell out, set in SPEC §2.3 and open to the next review: head lines that
  are not `name: value` go to an `unparsed` list (absent when empty);
  values are trimmed per RFC 9110. The fixture was regenerated through the
  real tee, bodies byte-identical to A3d's, now with `collector.log`. An
  unsealed manifest fails verify (no captures exist yet). Still open: the
  sink forwards the stdlib's parse of the headers to the Collector, so a
  CR-injected header still reaches it — not A4a's row, for the review.
- 2026-10-11 A4a (29c9d5c): replay writes the captured head's octets
  over the socket seam, only `Host` substituted; the review's four
  differences are gone. Consequences of "only Host", stated in SPEC §6.2
  and for the review: a bare-CR head is now sent as captured (was
  refused); hop-by-hop headers are sent (the tee's forward still drops
  them); a `Host:` after a bare LF is left alone; an empty or
  unterminated head is refused per body (exit 1); a captured chunked POST
  will time out on replay. `--json` replays `json/NNNN.headers.raw` by the
  same rule. Still open: N-7, the summary counts unsent bodies as sent.
- 2026-10-11 A0c (af667c8): awaiting decision. The rehearsal in a
  scratch clone made six of the seven differences true and closable by
  docs (Ctrl-C exit 0 with no Collector left; `make verify`/`make check`
  green with a capture present; no Collector lines in the terminal; the
  body count; step 2's digest wording; the pet's `MANIFEST.json`
  rewritten). The seventh is false against the code: a log redirected
  into the run directory is hashed before `zoo capture` writes its last
  line, so `zoo verify` fails, and the redirect creates the directory
  before readiness (SPEC §4.6). Options in OPEN_QUESTIONS.md §4. No README
  edit landed; A0c is re-dispatched whole once decided. Side findings
  there: README Layout and SPEC §2 lack `collector.log` and
  `json/NNNN.headers.*`; `make collector` is once per checkout; N-1.
- 2026-10-11: A0c decided, option 2 (`OPEN_QUESTIONS.md` §4): the
  log-to-file variant writes to `"${TMPDIR:-/tmp}"/zoo-capture-<run-id>.log`,
  and the README says in one sentence that the operator log is not part
  of the record because `collector.log` is. §3's "the run's record" row
  amended. A0c re-runs in full: the six differences, this one as decided,
  and the side findings (Layout and SPEC §2 tree list `collector.log` and
  `json/NNNN.headers.*`; the Makefile comment names `collector/SHA256SUMS`;
  `make collector` once per checkout; N-1's verify wording). Run 2b ends
  with A0c.
- 2026-10-11 A0c (c48e093): the README rehearsed as printed in a scratch
  clone, both flows, every exit 0, no run directory before readiness, the
  TMPDIR log outside the checkout. Docs only except N-1: `zoo verify`'s
  closing line is now neutral for every failure (per-problem lines still
  name a sha256 mismatch). For the scoped review: SPEC §4.2's list of
  terminal lines omits the two lines after readiness and `zoo capture:
  stopping`. Run 2b complete; next is its scoped cold review (aux) with
  the operator rehearsal repeated.
- 2026-10-11: run-2b scoped review read and decided (§3). The rehearsal
  with the real Z4 project was green end to end. The header-derivation rule
  is ratified so Z4's sealed json carries a maintainer's rule, not a
  batch's; the request-line amendment is A3g's. Z4's captures come next.
- 2026-10-12: Z4 captured by the operator (`real` and `recorded`,
  47cb06c); run 3 opened.
- 2026-10-12 A3g (487bbc1): every `next batch` item of the run-2b review
  closed; 361 passed locally, `collector-check` ran 4 real-Collector tests.
  Readings taken where SPEC was silent, for the next review: a head with
  no CRLF carries no `request_line`/`method`/`path` (`headers: []`); the
  `forward` seam is `(head, body)`; the README's readiness `timeout` is
  60 s (the zoo's own wait can reach 52.5 s); `Trailer` joined SPEC's
  hop-by-hop list to match the code. The fixture was regenerated through
  the real tee (its json gains `request_line`; bodies byte-identical);
  Z4's sealed captures keep their json and SPEC §2.3 says they predate
  `request_line`. Stale "captures/ is empty" wording removed. Patch set
  `patches/0023`–`0035` (run 2b). CI: the macOS leg failed once on
  `test_sixteen_hundred_bodies_cost_the_same_each` (675 → 2,168 µs/body
  on the runner) and passed on a re-run of that job alone with no code
  change — a wall-clock ratio test on a shared runner; registered as a
  thread for A6, not acted on.
- 2026-10-12 A5 (639485a): awaiting decision, no code. Step 5 needs
  `agentgolden`'s `Signature`, and the `audit` extra pins only spanweave
  and spanweave-live; adding a dependency is a policy §3 does not state.
  Options in `OPEN_QUESTIONS.md` §5: (1) pin `agentgolden@aa1847f2`
  (0.1.0, needs `spanweave>=0.9.1,<1.0`, which the pin satisfies) and
  decide whether the import gate confines it to `audit.py`; (2) drop step
  5 or carry it to `PROBES.md` as a probe not run; (3) an unpinned side
  environment (not recommended). Cap(0)-at-end needs no decision:
  `spanweave-live serve --requests N` at the pinned sha ends input after N
  requests. SPEC §7 is still an empty heading; A5 writes it. Once decided,
  A5 is re-dispatched whole; A6 waits on it.
- 2026-10-12: A5's question (OPEN_QUESTIONS §5) decided — option 1, the pin,
  with the gate extended to the third name; the macOS wall-clock test
  ratified as re-runnable for this series and registered for the next. A5 is
  dispatched whole; A6 follows.
- 2026-10-12 A5 (f60f69c, 701fc80): `zoo audit` replays each capture
  into `spanweave-live serve`, rebuilds every written trace through
  `spanweave.build`, inspects it and takes agentgolden's `Signature`;
  `audit/` holds the two Z4 reports. Findings, identical on `real` and
  `recorded`: every protobuf body is a 415 (spanweave-live); Z4's root span
  `concierge.conversation` is claimed by no adapter (spanweave), so `serve`
  routes it to a no-trace builder that is never written and no event names
  (spanweave-live), and the four chat spans come out `orphan_parent`. Live
  equals batch byte for byte on every written trace; the signature ran
  clean. f60f69c failed CI's `collector` leg only: the audit test module's
  collection-time `importorskip` surfaced as a skip in the
  `needs_collector` selection and the guard refused it; 701fc80 skips per
  item instead and a test holds it; all seven legs green at 701fc80. New
  commit on top, no force-push. For the scoped review of the close: (1) CI
  gained a seventh leg, `audit` (installs the extra, `make audit-check`),
  which the row did not name — without it the 20 extra-only tests only
  ever skip; (2) SPEC §7.4's owner table is the batch's reading, notably
  that the unclaimed root counts against both spanweave and
  spanweave-live; (3) the reports differ between runs in the `listening`
  port and the `completed` clock readings, stated in their method
  section; (4) CLAUDE.md rules 6 and 8 and §0.6 still name only spanweave
  and spanweave_live — the third name decided in §3 is not yet in either.

---

## Series 2 — the hardening series, and the five audits (opened 2026-10-12)

Branch `zoo`, opened from `main` at `25b2ef2`. While the series is open its
batches are `WORKPLAN.md` §1; this section registers what the series was opened
to close, each item with the batch that closes it. The registry and the folded
logs land here at the close (B8).

The review that opened it is Qodo's of PR #1 (comment `6127903067`,
2026-10-12, `qodo-code-review[bot]`: 12 bugs, 0 rule violations), kept byte for
byte as `reviews/QODO-2026-10-12.md` — the comment's `body` exactly as the API
returns it, without the trailing newline `gh api --jq .body` adds
(`reviews/SHA256SUMS`, now 26 files; `cd reviews && sha256sum -c SHA256SUMS`).
All twelve were accepted (`WORKPLAN.md` §3, 2026-10-12, "series").

### Qodo's twelve items

- Q1 Startup signals leave a Collector running (`run_capture` installs its stop handlers after `running.start()` returns). **B2** (a).
- Q2 A slow export invalidates its capture (a forward outcome appended to `forwards.jsonl` after the seal). **B3** (a).
- Q3 Skipped exports distort replay timing (`previous` not advanced past an unreadable request). **B5** (c).
- Q4 Unmatched records still produce findings (step 3 incomplete, its findings emitted anyway). **B6** (a).
- Q5 The audit writes no report if `serve` cannot launch (`OSError` from `Popen` uncaught). **B6** (b).
- Q6 Terminating the sink skips its manifest (no SIGTERM/SIGHUP handler in `run_sink`). **B2** (c).
- Q7 Invalid journal bytes prevent completion (`UnicodeDecodeError` in `_journalled`). **B3** (b).
- Q8 A failed start can leave the Collector running (`Capture.start`'s tail outside its `try/except`). **B2** (b).
- Q9 Chunked exports get a stray 400 on the same connection (unframed body left on a keep-alive connection). **B5** (a).
- Q10 `verify` crashes on some malformed manifests (`"files": 1`, `"problems": 1` → `TypeError`). **B4**.
- Q11 Replay to an IPv6 address sends a bad `Host` (literal not bracketed). **B5** (b).
- Q12 `verify` accepts files outside the capture (absolute, `..` or symlinked entries). **B4**.

### The close review's carried threads

Carried from series 1's close (`ROADMAP.md`, "Threads for zoo series 2"):

- **The port race**: `test_the_collector_killed_by_hand_mid_capture_is_a_problem` failed once in CI (`e50a56e`, PR run attempt 1) with the Collector's port taken between the zoo's pick and the Collector's bind; green on re-run with no code change. **B1** (a bounded retry on bind failure).
- **The PR wording**: PR #1's body says the merge is a fast-forward; `--merge` wrote `ebe12cf`. **B8** (the closing PR `zoo` → `main` is a merge commit, as PR #1 was, and its text says so).
