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

## Series 2 — the hardening series, and the five audits (2026-10-12 → 2026-10-14)

Branch `zoo`, opened from `main` at `25b2ef2`. The plan as it stood at the
close is `git show 1ed70a1:WORKPLAN.md` (the parent of the `close:` commit that
deleted it); its §1 rows are the full text of each batch below. The series
closed what two reviews of series 1's close found — Qodo's twelve items on
PR #1 and the close review's carried threads — and audited the five remaining
pet projects (Z3, Z5, Z1, Z2, Z6) as their captures landed; at the close every
captured project was audited again with one audit and `PROBES.md` was
consolidated across all six (B8).

The review that opened it is Qodo's of PR #1 (comment `6127903067`,
2026-10-12, `qodo-code-review[bot]`: 12 bugs, 0 rule violations), kept byte for
byte as `reviews/QODO-2026-10-12.md` — the comment's `body` exactly as the API
returns it, without the trailing newline `gh api --jq .body` adds. Qodo's PR
summary of the same PR (comment `6127869987`, 2026-10-12), which carries the
one design alternative Qodo raised, is kept the same way as
`reviews/QODO-SUMMARY-2026-10-12.md` (B8). `reviews/SHA256SUMS` lists 27
files: series 1's 25, and the two Qodo comments; `cd reviews && sha256sum -c
SHA256SUMS`. All twelve items were accepted (decisions log below,
2026-10-12, "series").

### Registry

| ID | Batch | Closed by |
|---|---|---|
| B0 | The two reviews of the close, archived and dispositioned | `d0debab` |
| B1 | The test harness does not lose a port race | `d99ba97` (question `b7165a0`, `OPEN_QUESTIONS.md` §6) |
| B2 | Signals cover the whole life of a capture, and of the sink | `202556c` |
| B2a | The per-body cost test measures the recorder, not the runner | `91e094d` |
| B2b | The per-body cost is a count, not a clock | `63e44bc` |
| B3 | Nothing writes to a capture after its seal | `12de782` |
| B3a | Standalone `zoo sink` seals only once nothing can write | `cae8168` |
| B4 | `verify` trusts nothing a manifest says about where a file is | `99edcbd` |
| B4a | The replayer refuses a path outside the run | `3dcd17a` (question `7275b12`, `OPEN_QUESTIONS.md` §7) |
| B5 | The wire is honest at its edges | `cafb8cd` |
| B5a | A request with `Transfer-Encoding` is never read by its `Content-Length`, and a negative length closes | `558ec4a` |
| B5b | A `Content-Length` is digits, once | `a48dfcc` |
| B5c | A folded `Content-Length` is unframeable | `9bcbaa0` |
| B5d | The sink frames by the record's own parse | `8aafdb4` |
| B6 | The audit says "not run" when it cannot vouch | `290fc1b` |
| B6a | The audit observes every policy and names every node | `07285bd` (question `a8502c3`, `OPEN_QUESTIONS.md` §8) |
| B6b | The node table names the span | `390eb24` |
| B6c | The node table names the record | `4b57f18` |
| B7r | Every captured project audited once more, with the one audit | `b63c0cf` |
| B7-Z3 | Audit Z3 (`echo-planner`) | `a180f06` |
| B7-Z5 | Audit Z5 (`flaky-fetcher`) | `54703f2` |
| B7-Z1 | Audit Z1 (`ledger-clerk`) | `184b70d` |
| B7-Z2 | Audit Z2 (`fan-out-researcher`) | `aebff51` |
| B7-Z6 | Audit Z6 (`crew-of-three`) | `13883dd` |
| B8 | The series closes | the `close:` commit that adds this section and deletes `WORKPLAN.md` (this commit) |

B7 was the per-project template, instantiated as the five B7-Z rows. Not a
batch, and in the series' history: the operator's captures — `9b0268f` (Z3),
`f081997` (Z5), `c24ab69` (Z1), `45305a8` (Z2), `88dbcfd` (Z6) — and
`691866a`, export contract 1.3 with the Z5 brief amendment.

### Dispositions of the reviews

**Qodo's review of PR #1** (`reviews/QODO-2026-10-12.md`), twelve items, all
accepted, each with the commit that closed it:

- Q1 Startup signals leave a Collector running (`run_capture` installs its stop handlers after `running.start()` returns). **B2** (a), `202556c`.
- Q2 A slow export invalidates its capture (a forward outcome appended to `forwards.jsonl` after the seal). **B3** (a), `12de782`; the standalone sink, **B3a**, `cae8168`.
- Q3 Skipped exports distort replay timing (`previous` not advanced past an unreadable request). **B5** (c), `cafb8cd`.
- Q4 Unmatched records still produce findings (step 3 incomplete, its findings emitted anyway). **B6** (a), `290fc1b`.
- Q5 The audit writes no report if `serve` cannot launch (`OSError` from `Popen` uncaught). **B6** (b), `290fc1b`.
- Q6 Terminating the sink skips its manifest (no SIGTERM/SIGHUP handler in `run_sink`). **B2** (c), `202556c`.
- Q7 Invalid journal bytes prevent completion (`UnicodeDecodeError` in `_journalled`). **B3** (b), `12de782`.
- Q8 A failed start can leave the Collector running (`Capture.start`'s tail outside its `try/except`). **B2** (b), `202556c`.
- Q9 Chunked exports get a stray 400 on the same connection (unframed body left on a keep-alive connection). **B5** (a), `cafb8cd`; every framing case after it, **B5a**–**B5d** (`558ec4a`, `a48dfcc`, `9bcbaa0`, `8aafdb4`).
- Q10 `verify` crashes on some malformed manifests (`"files": 1`, `"problems": 1` → `TypeError`). **B4**, `99edcbd`.
- Q11 Replay to an IPv6 address sends a bad `Host` (literal not bracketed). **B5** (b), `cafb8cd`.
- Q12 `verify` accepts files outside the capture (absolute, `..` or symlinked entries). **B4**, `99edcbd`; the replayer, **B4a**, `3dcd17a`.

**Qodo's PR summary of PR #1** (`reviews/QODO-SUMMARY-2026-10-12.md`, "High-Level
Assessment"): one alternative approach, a **wire-level TCP proxy** in place of
the application-level sink ("could preserve transport framing and support
requests beyond the current Content-Length-based HTTP sink"; "substantially
complicates request accounting, Collector forwarding, and the documented
OTLP/HTTP capture contract"). **Declined.** Qodo's own recommendation was to
keep the application-level sink and the pinned stock Collector for the stated
OTLP/HTTP scope, because they separate the authoritative request record from
the optional re-encoding, and to consider a proxy only if preserving HTTP
framing or chunked uploads became a requirement. Neither has: the record is
the head's octets and the body as the sink read it (`SPEC.md` §2.3), a request
the sink cannot frame is recorded as what it could see and its connection
closed (decisions 2026-10-12 "B5(a)", 2026-10-13 "B5a", 2026-10-13 "B5d"), and
the sink parses nothing (standing rule 3). Not reopened in this series; a
thread only if a pet project ever exports something the sink cannot frame.

**The close review of series 1** (`reviews/REVIEW-2026-10-12.md`): its findings
and A5's items were dispositioned at series 1's close (above, "Close review").
Its two threads carried into this series (`ROADMAP.md`, "Threads for zoo
series 2", at series 1's close):

- **The port race**: `test_the_collector_killed_by_hand_mid_capture_is_a_problem` failed once in CI (`e50a56e`, PR run attempt 1) with the Collector's port taken between the **harness's** pick and the Collector's bind; `zoo capture` picks no port (`OPEN_QUESTIONS.md` §6). **B1**, `d99ba97`: the harness picks no sink port (`--port 0`, `--json-port 0`) and retries a start lost to a race on `--collector-port`, bounded, naming every port tried.
- **The PR wording**: PR #1's body says the merge is a fast-forward; `--merge` wrote `ebe12cf`. **B8**: the closing PR `zoo` → `main` is a merge commit, as PR #1 was, and its text says so. The PR itself is opened after this commit.

No other review was taken in this series: no aux review file was written under
`patches/`, so none is archived beyond the two Qodo comments.

### Threads for series 3

Registered here at the close. None is acted on in this series. Each says where
it was raised.

- **A head the derivation marks `unparsed`, or that carries a bare CR, may
  close its connection** (decision 2026-10-14, "B5d"): after the answer,
  defensively, without changing the record. A thread, not a row.
- **The `PID set at arming:` wording** (`~/spanweave-ops/status_check.sh`):
  owned by **spanweave-ops**, not this repository; not acted on here (as
  series 1's R-8).
- **Contract 1.4 candidates** (decision 2026-10-14, "B8"), each from a project
  built against 1.3, to be weighed where contracts are issued (`CONTRIBUTING.md`,
  "Captures"):
  - a framework's own phone-home telemetry may be disabled, and the project
    says so — Z6 sets `CREWAI_DISABLE_TELEMETRY=true` and
    `CREWAI_TRACING_ENABLED=false` (its README, "Telemetry configuration");
  - the Python range follows the framework — Z6 needs 3.10–3.13 because CrewAI
    does not support 3.14 (its `pyproject.toml`, `requires-python =
    ">=3.10,<3.14"`);
  - a project that has never run has no manifest: one throwaway recorded run
    to a dead port writes it (Z6; `ROADMAP.md`'s checklist, step 3).
- **From `ROADMAP.md`, carried again** (series 1's close): contract 1.2
  manifests — confirm `verify` accepts 1.1 and 1.2 project manifests and
  records which; and a model pre-flight as a zoo command (`zoo preflight
  --base-url --model`).
- **Open in the resume notes, closed by no batch:**
  - B1 (2026-10-12): tests that expect a refusal still pick a port without
    retry, so a race there can change which refusal they see; and
    `tests/test_replay.py` (~l.640) picks a port it needs closed — a different
    race.
  - B2 (2026-10-12): `collector.Binary.start` stops the child on any exit once
    the process exists; a signal inside `Popen` itself can still leak it.
  - B7r (2026-10-13), and the audit as it stands: `--cap`, and any non-zero
    `--quiet` or `--root-grace`, are never run (decision 2026-10-13, "B6b":
    a non-zero value fires or not by wall clock); L3's and L4's *to establish*
    lines are what that leaves open.
  - B8: the generation graphs `serve --quiet 0` writes are compared with
    nothing, and the node table gives no id for a parent absent from the
    graph; `PROBES.md` reads both beside the audit or leaves them *to
    establish* (L3, S2, S12, S18).
- **Closed without a batch:** the "two workflow runs named `CI`" check
  (decision 2026-10-13, "ops"): `.github/workflows/` holds one file, `ci.yml`,
  so there is no duplicate to delete. `patches/` was cleared of series 1's
  files before series 2's set was written (decision 2026-10-13, "patches").
- Series 1's threads above that series 2 did not close stay as series 1
  registered them (notably A3b's `started_at` preference, `OPEN_QUESTIONS.md`
  §3, and the run-1/run-2/run-2b review threads). Series 2 closed the macOS
  wall-clock cost test (B2a, then B2b: a count, not a clock) and the port race
  (B1).

### Decisions log (`WORKPLAN.md` §3, folded verbatim)

Section references inside (`§0.1`, `§3`, `§4`, a row) are to `WORKPLAN.md` as
it stood at `1ed70a1`.

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
| 2026-10-13 | B6a | Confirmed as built: `audit()` takes `sleep` (a seam); the policy runs observe and produce no findings, step 3 judges; "reason" is the `completed` event's `detail` to its first colon and "generation" is counted from the receiver's own events, because the receiver carries neither field — both stated in the report's Method. The decision's premise was weaker than written: `serve` ticks after every request, so at `0` the sequence is the same timed or untimed; `--timing` is dropped from the policy runs by B6b. The observations stand: Z3 real under `--quiet 0` is four generations with three `late_arrival`s; under `--root-grace 0` one completion at the last request; Z5's two `error` tool nodes carry their exception events. | maintainer |
| 2026-10-13 | B7r | Confirmed: reports replaced in place; a second run differs only in ports and timestamps, so no finding about the method. | maintainer |
| 2026-10-13 | B5d | The sink frames a body by **its own parse of the head** — the strict CRLF-only rule `headers.json` is derived by — and never by the stdlib's header object, which splits on bare CR and LF. The record and the framing then cannot disagree by construction; B5a, B5b and B5c become cases of this one rule, and their tests stay. | maintainer |
| 2026-10-13 | B6b | The per-node table gains span name, parent id, the unmapped keys on the node (names, not values) and payload presence, so "which node is which" is answered by the report. `--timing` leaves the policy runs. `--cap` and non-zero policy values stay out: a non-zero value fires or not by wall clock, and the audit asserts nothing a clock decides. | maintainer |
| 2026-10-13 | ops | Two workflow runs named `CI` on `24e483a`: the aux checks whether two workflow files share the name and reports; not a zoo batch unless one is a duplicate to delete. | maintainer |
| 2026-10-14 | B5d | Confirmed, both edge changes: a `Transfer-Encoding` the record's derivation does not see is not in the record, so the record's `Content-Length` frames the body; an LF-only head has no `Content-Length` in the record, so zero bytes and close. Thread for series 3, not a row: a head the derivation marks `unparsed`, or that carries a bare CR, may close the connection after the answer, defensively, without changing the record. | maintainer |
| 2026-10-14 | B6b | Confirmed: `sleep` removed with the timed replay; the payload column shows spanweave's own states. | maintainer |
| 2026-10-14 | B7-Z1 | Confirmed: the row correction stands. The two observations made beside the report name the node table's last gap, closed by B6c. | maintainer |
| 2026-10-14 | B6c | The node table gains **record index and body** per node (`json/NNNN.json`, record *n*), so parent-before-child ordering (S14/S15) and "which body carried the root" (L3, Z6) are read from the report. | maintainer |
| 2026-10-14 | captures | Z6's real run did not follow its one-send-back script (two delegations, one `Ask question to coworker`, four lint passes); the contract allows randomness in the real run and the recorded capture is the script. Recorded as the capture's own fact, not a defect. Z6 had no manifest before its first run; the operator's throwaway recorded run against a dead port wrote one and captured nothing — the method for any project that has never run, noted in ROADMAP's checklist. | maintainer |
| 2026-10-14 | B8 | The close regenerates **all twelve** reports with the final audit (B6c), so every probe cites one method; PROBES.md is consolidated across six projects, grouped by owner, each probe with its captures and command; `ROADMAP.md`'s six rows are complete, repository shas read from the local checkouts (`git -C ~/git/<project> rev-parse HEAD`); contract 1.4 candidates registered as threads (a framework's phone-home telemetry may be disabled, Z6; the Python range follows the framework, Z6; a project that has never run has no manifest). `TASKS.md` carries the decline of Qodo's wire-level-proxy alternative (PR #1 summary, 2026-10-12) with its reason. | maintainer |

### Resume notes (`WORKPLAN.md` §4, folded verbatim)

Section references inside are to `WORKPLAN.md` as it stood at `1ed70a1`.

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
- 2026-10-13: B7r done (`b63c0cf`), CI 38413673522 green on all seven
  jobs. Six reports replaced in place; findings unchanged (Z4 3, Z3 1,
  Z5 1); no new probe, counts stay (spanweave-live 4, spanweave 13,
  agentgolden 0). Observed now: L3, L4 (at 0), S5, S9, S10, S11, S12;
  further but still partly open: L2, S2, S3, S6, S13. Still open because
  the node table carries no span name, parent id, unmapped key or payload
  per node (S2/S12 parent identity, S6 names, S8's 18 nodes, S10 records,
  S11 outputs, S13 graph bytes) — a candidate row widening the table; and
  `--cap` or non-zero policy values are never run. Re-run differs only in
  `listening` ports and the clocks of `completed` and `late_arrival`
  (PROBES.md corrected to say `late_arrival` too, as SPEC §7.3 does): no
  method finding. Run 4 done.
- 2026-10-13: run 4 confirmed; B5d (the sink frames by its own parse) and
  B6b (the node table names the span) added; run 5 waits for Z1's captures
  so its audit is in the same run. Z1's captures landed at `c24ab69`, so B7-Z1 is `todo`.
- 2026-10-14: B5d done (`8aafdb4`), CI 38484508107 green on all seven
  jobs. `sink.framing_of(head)` frames from the record's CRLF split;
  `folds_a_length` stays as one case. Two consequences of the rule beyond
  the row's two heads, for the maintainer to confirm (SPEC §3.7 lists
  both): a `Transfer-Encoding` only the stdlib sees (`X: a\rTransfer-
  Encoding: chunked` beside `Content-Length: 5`) is now framed by its 5
  bytes and keeps the connection — less strict than the parent; and an
  LF-only head (A3g) has no `Content-Length` in the record, so its body is
  now zero bytes and the connection closes. Two existing tests changed
  for the latter (`test_an_lf_only_head_is_one_unparsed_entry_and_nothing_
  else`, and the `lf-only` case of the replay host-line test); their head
  assertions unchanged.
- 2026-10-14: B6b done (`390eb24`), CI 38485122335 green on all seven
  jobs. Beyond the row, for the maintainer to confirm: with no timed replay
  left, `audit()`'s `sleep` seam is removed (SPEC §7.6 row gone, the policy
  table's "gap slept" column too); the payload column shows spanweave's own
  state, so `empty`, `redacted`, `truncated` can appear beside `present` /
  `absent` (§7.5 says so); §7.5 states that a report keeps the layout it
  was written with until audited again. Committed `audit/` reports not
  regenerated, as the row says.
- 2026-10-14: B7-Z1 done (`184b70d`), CI 38485886518 green on all seven
  jobs. F1 per report (L1 again); L3, S3, S7, S9 again; S14 (PROMPT spans
  become two `unknown` `ChatPromptTemplate` nodes) and S15 (the row's
  points) new; counts spanweave-live 4, spanweave 15, agentgolden 0. One
  trace of 31 records per capture, 30 explicit parent edges, no
  `orphan_parent` at end of input; depth 8 edges to five `fx_rate` tool
  nodes under `_fetch_rates`. Parent-before-child holds nowhere: every
  child's record precedes its parent's (30 of 30), the root is the last
  record of the last body. Ordering was observed beside the audit (records
  fed one by one to a pinned `spanweave.Builder`; command in S15), as were
  `serve`'s written graphs (`--quiet 0` first generation: 6
  `orphan_parent`) — the report does not show which record a node came
  from; marked in PROBES.md. Row premise wrong: `summarize` is a `chain`
  node (depth 4, child of `categorize`) whose LLM child is `ChatOpenAI`,
  off the `fx_rate` path — row corrected. PROBES.md's "re-running
  reproduces the committed reports" corrected: since B6b, Z3/Z4/Z5's
  committed reports keep the old layout until B8. Z1's project manifest
  names no repository, so ROADMAP's Repository cell is "—". Run 5 done.
- 2026-10-14: run 5 confirmed; Z2 and Z6 captured by the operator (Z6's
  real run improvised past its script — recorded as its own fact); B6c
  added so the final reports name the record; run 6 is the close.
- 2026-10-14: B6c done (`4b57f18`), CI 38491811516 green on all seven
  jobs. Body and Record sit after Node; both read *absent* when spanweave
  does not place the node's record. They come from spanweave's
  `Node.raw.line_number` (public, in memory only, not serialized — SPEC
  §7.3 says so). Row premise: `tests/fixtures/capture` has one body, so
  the two-body test uses the committed Z4 real capture; red on the parent
  (5 failed), mutation (feed position for index) caught.
- 2026-10-14: B7-Z2 done (`aebff51`), CI 38492770732 green on all seven
  jobs. F1 per report (L1 again); L3, S3, S7, S9 again; S16 (the three
  tool calls' order), S17 (the LLM streams), S18 (`--quiet 0` partial
  graphs: sibling start-time edges join orphans whose stated parents
  differ — to establish against spanweave SPEC §4.3) new; counts
  spanweave-live 4, spanweave 18, agentgolden 0. One trace of 23 records
  per capture, 22 parent and 14 temporal edges. Row premises wrong, row
  corrected: the `acall` nodes are not siblings — each is the only child
  of its own `call_tool` chain, the chains are siblings under the root;
  they start A,B,C and end B,C,A, records arrive in end order, temporal
  edges order the `call_tool` parents and touch no `acall`. The two
  `astream_chat` per step are nested, beside a third `llm` node
  (`_prepare_chat_with_tools`); each inner stream's first-token event is
  stamped after its span ended. `unpaired_call` ×3 sits on the first
  step's inner `astream_chat`; tool records carry no call id, so nothing
  pairs (spanweave SPEC §4.4). Root record last of the last body.
- 2026-10-14: B7-Z6 done (`13883dd`), CI 38493651797 green on all seven
  jobs. F1 per report (L1 again, 11 of 11 real, 1 of 1 recorded); L3, S3,
  S7, S9, S18 again, S6 in another shape; S19 (task-level nesting), S20
  (delegation spans), S21 (record order within a body), S22 (real against
  recorded, two shapes of one crew) new; counts spanweave-live 4,
  spanweave 22, agentgolden 0. Row premises wrong, row corrected: tasks
  are `<role>._execute_core` spans directly under the crew (two levels);
  no model call appears twice — all 14 real and 8 recorded `llm` nodes are
  the OpenAI instrumentor's. Delegation spans are `tool` nodes, each with
  one `ChatCompletion` child; no `agent` node stands for the coworker.
  Records carry `graph.node.parent_id` naming the previous agent while the
  span parent is the crew; spanweave leaves it unmapped (S19, to
  establish). `empty` payload state appears for the first time
  (`list_commits.run` inputs `{}`). Z2's and Z6's Repository cells are
  "—"; B8 fills them from the local checkouts (`~/git/crew-of-three` at
  `78adcaf`). B8 is `todo`.
