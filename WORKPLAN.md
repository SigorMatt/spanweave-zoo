# WORKPLAN.md — spanweave-zoo, the stranger's-trace series

Status file for the zoo: the capture side of the pet-project programme
(`EXPORT-CONTRACT.md`, `ZOO-BRIEFS.md`) — a sink that records what real
exporters send, a Collector that re-encodes it, a replayer, and the audit
that runs spanweave and spanweave-live over every capture and writes the
next series' probes. One batch = one sub-agent = one commit = one concern.
This file plus git is the only state; any session can resume cold from it.

Last updated: 2026-10-10 (run 1 complete: A0, A1, A2, A3 done; the run-1
cold review is read and decided, see §3. Run 2 is under way: A3a done,
then A3b → A3c → A3d → A0a → A0b → A4, then a cold review.)

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
| A0 | **Repository skeleton, on `main`.** `pyproject.toml` (package `spanweave_zoo`, CLI `zoo`, Python 3.11–3.14; `spanweave @ git+https://github.com/SigorMatt/spanweave@fec7da27af517ad8b58ae3ec57827916aae60674` and `spanweave-live @ git+https://github.com/SigorMatt/spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` as an **`audit` extra only**); `uv.lock`; `Makefile` with `check` (ruff, format, `mypy --strict`, pytest, gates), `verify` (re-hash every capture), `install-check`; `.github/workflows/ci.yml` as spanweave-live's (`check` on 3.11–3.14 ubuntu and 3.12 macos); `CLAUDE.md` with §0.6; `CONTRIBUTING.md` with the batch bar; `SPEC.md` §1 non-goals (the zoo parses nothing, fixes nothing, improves nothing) and §2 the capture layout: `captures/<project>/<run-id>/raw/NNNN.body` + `NNNN.headers.json`, `captures/<project>/<run-id>/json/NNNN.json` (Collector re-encoding), `MANIFEST.json`; `tests/gates.py` with one gate: no module under `spanweave_zoo/` imports `spanweave` or `spanweave_live` except `audit.py`; `README.md`; `CHANGELOG.md`; copies of `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root, byte-identical to the ones handed to the projects (sha256 in README). `make check` green, CI green on `main`. Then `git switch -c zoo`; every later batch lands on `zoo`. | done (d33059e) | 10 |
| A1 | **The sink records bytes, and nothing else.** `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` (SPEC §3): stdlib `http.server`; `POST /v1/traces` with **any** `Content-Type` and `Content-Encoding` is written as `NNNN.body` (the bytes exactly as received, still encoded if gzip) with `NNNN.headers.json` (method, path, every header, length, receipt time from an injected `now`), and answered `200` with an empty body and the request's content type echoed; any other path is `404` and still recorded under `rejected/`. The sink never decodes, decompresses or parses. Tests red on the parent: a protobuf body, a JSON body and a gzip body round-trip byte for byte; two POSTs in flight are numbered in receipt order; `zoo verify` on the result passes and fails after one byte of one body is changed. Mutation: a sink that decompresses before writing fails the gzip case. | done (69fb6bd) | 8 |
| A2 | **The Collector re-encodes beside the raw.** `collector/config.yaml` (SPEC §4): stock OpenTelemetry Collector (contrib, exact version pinned in `collector/VERSION`, fetched by `make collector` from the release URL with its sha256 checked), `otlp` receiver on 4317/4318 **by default, overridable** (4318 is the raw sink's own port, so `zoo capture` moves the Collector's HTTP receiver to 4320), `otlp_http` exporter (`otlphttp` is a deprecated alias at 0.162.0, same component) with `encoding: json` to the sink on a second port, batch processor at defaults; `zoo capture --project z4 --run-id <id>` starts two sinks (raw on 4318 for the app, json on 4319 for the Collector) **and** the Collector pointed at the raw sink's port — the app's traffic reaches the raw sink first and the Collector second (a tee: the raw sink forwards each body unchanged to the Collector after writing it; SPEC states this and that the forward is byte-identical). Tests: a synthetic protobuf export through the tee yields `raw/0001.body` (protobuf) and `json/0001.json` (valid OTLP JSON with the same span ids); the Collector version in the manifest equals `collector/VERSION`. If the Collector cannot run in CI, the test is marked and `make check` still runs it locally — say so in the body. | done (8c8299f) | 12 |
| A3 | **The capture is a manifest, immutable.** `zoo capture` ends by writing `MANIFEST.json` (SPEC §5): the project's own `MANIFEST.json` (copied from a path the operator passes), the zoo's `sink_version`, `collector_version`, `kind` (`recorded` \| `real`), `started_at`/`ended_at` from the injected clock, and `bodies: [{"file": ..., "sha256": ..., "content_type": ..., "content_encoding": ..., "bytes": ...}]` for raw and json; `zoo verify [path]` re-hashes everything under `captures/` and exits non-zero on any difference or any body without a manifest entry; `make check` runs `zoo verify` (already wired in A0; A3 extends it from refusal to manifest re-hashing). `README.md` §"Running a pet project's real run": the commands an operator types — **the commands the README lists**, in two terminals. Tests red on the parent: a manifest with a stale hash fails verify; a body not listed fails verify; `kind` is required. **End of run 1: the sink is ready for the pilot project's real run.** | done (9074ecd) | 6 |
| A3a | **A capture exists only once it is ready, and a refusal writes nothing.** Review F2, F8. Readiness is: three listeners accepting **and** the Collector child alive with its ready line read from its log; only then is `captures/<project>/<run-id>/` created and the single readiness line `zoo capture: the raw bytes are the record. Ctrl-C to stop.` printed. A refusal before readiness (any port held, the Collector exiting, a bad config) names the port or the cause, exits 2, and leaves no directory. During a capture, the Collector child exiting is recorded (`problems: ["collector exited: <code>"]`) and reported at exit non-zero. Tests red on the parent: a foreign listener on 4320 → refusal naming 4320, no directory; the Collector killed mid-capture → non-zero exit and the problem in the manifest; `zoo sink`'s banner is distinct from the readiness line. Mutation: a probe that only connects to the port passes the foreign-listener test's inverse. | done (2b3c499) | 8 |
| A3b | **The manifest is written once, at the end, and covers every file.** Review F4, F7, F9, F10, F12. Bodies journalled to `bodies.jsonl` (one line per POST, flushed); the manifest assembled at `Ctrl-C` from the journal; the project manifest copied then, with the `started_at` check of §3 and `project_manifest: null` + `problems` on failure; a sha256 entry for every file in the run directory except `MANIFEST.json`; `kind` ∈ {recorded, real}; `ended_at` set last. `zoo verify` re-hashes every listed file and fails on an unlisted one, a missing one, a missing `ended_at`, or any `problems`. Progress lines flushed on every write; `BrokenPipeError` on stdout finalizes and exits 0 with the manifest complete. Tests red on the parent: a project manifest rewritten mid-run lands as the end-of-run copy; a project manifest older than the capture → `problems`, exit non-zero, verify fails; a rewritten `Content-Type` in `headers.json` fails verify; `kind` flipped fails verify; 1,600 bodies at constant per-body cost (measure and put the three numbers in the body). Mutation: a verify that skips `headers.json` passes the rewritten-content-type test's inverse. | todo | 10 |
| A3c | **The header octets are the record.** Review F6. `NNNN.headers.raw`: the request line and header block as received, CRLFs intact, up to the blank line; `NNNN.headers.json` unchanged beside it; SPEC §2.3 says the raw file is the unmodified record and the json is the parse. Test red on the parent: a bare CR inside a header value is present in `.raw` and absent as a header in `.json`; `.raw` is byte-identical to what the client sent. Mutation: writing the stdlib's reconstructed headers to `.raw` fails the bare-CR test. | awaiting A3b | 5 |
| A3d | **`verify` refuses what it did not check, and CI checks something.** Review F1, F5, T1, T24. `zoo verify <path>` on a path that is not a capture → exit 2 naming the path; `cli.py`'s docstring says what the code does. A test recomputes the two contract sha256s in README and fails on drift. The import gate exempts `spanweave_zoo/audit.py` by path, not basename. `tests/fixtures/capture/` holds one real capture (one protobuf span through the real tee, both sides, headers raw and json, manifest) and CI's `make verify` is shown to read it. Tests red on the parent for each. | awaiting A3c | 6 |
| A0a | **The README is true, the licence exists, and the open question has a home.** Review F3, F15, F14, T5, T18, T20, F16. README: the operator section lists the exact commands, each complete and runnable as printed, numbered, with `uv sync --extra dev` as the first; the row and §4 stop counting and cite the README. `LICENSE` MIT and `license` in `pyproject.toml`. `OPEN_QUESTIONS.md` created with §1 = the manifest-timing question and its decision (§3). §4 gains: the A2 CI line; the `c965c9b` → `9074ecd` force-push; the `b913e2b` two-clause subject. Docs only; say so in the body. | awaiting A3d | 5 |
| A0b | **CI proves the Collector claim.** Review T25. A sixth job `collector (ubuntu-latest)`: `make collector` with the release archive cached by its sha256, then the `@needs_collector` tests run and are shown **not skipped** (the job fails if any is). Pin the Collector download's sha in `collector/SHA256SUMS` as today. Say in the body how long the job takes. | awaiting A0a | 5 |
| A4 | **The replayer re-sends what was captured.** `zoo replay captures/<project>/<run-id> --to http://host:port [--raw\|--json] [--timing]` (SPEC §6): re-sends each body with its captured headers (content type and encoding intact) in receipt order; `--timing` sleeps the captured inter-arrival gaps through an injected `sleep`; prints each response status; exits non-zero if any status is not 2xx but still sends the rest. Tests: replaying a capture into a fresh sink produces byte-identical bodies and headers; `--timing` on a fake clock sleeps the recorded gaps. | awaiting A3 | 6 |
| A5 | **The audit: every capture through spanweave-live and spanweave, and what broke.** `zoo audit captures/<project>/<run-id>` (SPEC §7; the one module that imports both): (1) `zoo replay --raw` into `spanweave-live serve` and record every response status and every receiver event — a 415 on protobuf is a finding, not an error; (2) `zoo replay --json` into `serve` with a completion policy of `Cap(0)`-at-end (replay then signal end of input), collect each trace's final graph and every event; (3) for each trace, the records the receiver fed, in order, through `spanweave.build` — the live graph must equal the batch graph byte for byte (prefix consistency on a stranger's trace); (4) `spanweave inspect` on each graph: diagnostics by code, unmapped attributes by size, unknown kinds; (5) `agentgolden`'s `Signature` computed on each graph as a smoke, no rules evaluated. Output `audit/<project>-<run-id>.md`: a table per step, every diagnostic code with its count, every event, every divergence — each as a reproduction with the capture path and the command. **Findings are never fixed here**: each names the repo that owns it. The `real` capture is Z4's, taken by the operator after run 2 with the commands README names. | awaiting captures (A4 done and at least one `real` capture present) | 15 |
| A6 | **The series closes.** `TASKS.md` registry A0–A6 with shas; §3 and §4 folded; `reviews/` with every review byte-for-byte and sha256; `audit/` findings consolidated into `PROBES.md`: the next series' probe list for spanweave and spanweave-live, each with its capture and command; WORKPLAN.md deleted; PR `zoo` → `main`. No `plan:` commit follows. | awaiting A5 | 6 |

## 2. Execution order

Run 1 = A0 → A1 → A2 → A3 (done). Run 2 = A3a → A3b → A3c → A3d → A0a → A0b
→ A4, then stop: cold review (aux), decisions. Then the operator captures Z4
— `real` and `recorded` — with the README's commands, and commits the
captures. Run 3 = A5 → A6, then the scoped review of the close and the PR.
Every batch: CI green on the pushed tip before `done`.

## 3. Decisions log

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

## 4. Resume note

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

## 5. Origins

| ID | Origin |
|---|---|
| A0–A6 | The stranger's-trace decision of 2026-10-09 (this conversation): pet projects instrumented by stock instrumentors as the step before outside users; `EXPORT-CONTRACT.md`, `ZOO-BRIEFS.md`. |
| A2, A5(1) | The Python OTLP/HTTP exporter sends protobuf, not JSON (opentelemetry-python #1003, #2104); spanweave-live `serve` accepts JSON only (its R6). |
