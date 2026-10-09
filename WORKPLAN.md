# WORKPLAN.md — spanweave-zoo, the stranger's-trace series

Status file for the zoo: the capture side of the pet-project programme
(`EXPORT-CONTRACT.md`, `ZOO-BRIEFS.md`) — a sink that records what real
exporters send, a Collector that re-encodes it, a replayer, and the audit
that runs spanweave and spanweave-live over every capture and writes the
next series' probes. One batch = one sub-agent = one commit = one concern.
This file plus git is the only state; any session can resume cold from it.

Last updated: 2026-10-09 (series opened; run 1 = A0 → A1 → A2 → A3).

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
implement; then `make check` and `make conformance`. Add a CHANGELOG
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
| A0 | **Repository skeleton, on `main`.** `pyproject.toml` (package `spanweave_zoo`, CLI `zoo`, Python 3.11–3.14; `spanweave @ git+https://github.com/SigorMatt/spanweave@fec7da27af517ad8b58ae3ec57827916aae60674` and `spanweave-live @ git+https://github.com/SigorMatt/spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` as an **`audit` extra only**); `uv.lock`; `Makefile` with `check` (ruff, format, `mypy --strict`, pytest, gates), `verify` (re-hash every capture), `install-check`; `.github/workflows/ci.yml` as spanweave-live's (`check` on 3.11–3.14 ubuntu and 3.12 macos); `CLAUDE.md` with §0.6; `CONTRIBUTING.md` with the batch bar; `SPEC.md` §1 non-goals (the zoo parses nothing, fixes nothing, improves nothing) and §2 the capture layout: `captures/<project>/<run-id>/raw/NNNN.body` + `NNNN.headers.json`, `captures/<project>/<run-id>/json/NNNN.json` (Collector re-encoding), `MANIFEST.json`; `tests/gates.py` with one gate: no module under `spanweave_zoo/` imports `spanweave` or `spanweave_live` except `audit.py`; `README.md`; `CHANGELOG.md`; copies of `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root, byte-identical to the ones handed to the projects (sha256 in README). `make check` green, CI green on `main`. Then `git switch -c zoo`; every later batch lands on `zoo`. | todo | 10 |
| A1 | **The sink records bytes, and nothing else.** `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` (SPEC §3): stdlib `http.server`; `POST /v1/traces` with **any** `Content-Type` and `Content-Encoding` is written as `NNNN.body` (the bytes exactly as received, still encoded if gzip) with `NNNN.headers.json` (method, path, every header, length, receipt time from an injected `now`), and answered `200` with an empty body and the request's content type echoed; any other path is `404` and still recorded under `rejected/`. The sink never decodes, decompresses or parses. Tests red on the parent: a protobuf body, a JSON body and a gzip body round-trip byte for byte; two POSTs in flight are numbered in receipt order; `zoo verify` on the result passes and fails after one byte of one body is changed. Mutation: a sink that decompresses before writing fails the gzip case. | awaiting A0 | 8 |
| A2 | **The Collector re-encodes beside the raw.** `collector/config.yaml` (SPEC §4): stock OpenTelemetry Collector (contrib, exact version pinned in `collector/VERSION`, fetched by `make collector` from the release URL with its sha256 checked), `otlp` receiver on 4317/4318, `otlphttp` exporter with `encoding: json` to the sink on a second port, batch processor at defaults; `zoo capture --project z4 --run-id <id>` starts two sinks (raw on 4318 for the app, json on 4319 for the Collector) **and** the Collector pointed at the raw sink's port — the app's traffic reaches the raw sink first and the Collector second (a tee: the raw sink forwards each body unchanged to the Collector after writing it; SPEC states this and that the forward is byte-identical). Tests: a synthetic protobuf export through the tee yields `raw/0001.body` (protobuf) and `json/0001.json` (valid OTLP JSON with the same span ids); the Collector version in the manifest equals `collector/VERSION`. If the Collector cannot run in CI, the test is marked and `make check` still runs it locally — say so in the body. | awaiting A1 | 12 |
| A3 | **The capture is a manifest, immutable.** `zoo capture` ends by writing `MANIFEST.json` (SPEC §5): the project's own `MANIFEST.json` (copied from a path the operator passes), the zoo's `sink_version`, `collector_version`, `kind` (`recorded` \| `real`), `started_at`/`ended_at` from the injected clock, and `bodies: [{"file": ..., "sha256": ..., "content_type": ..., "content_encoding": ..., "bytes": ...}]` for raw and json; `zoo verify [path]` re-hashes everything under `captures/` and exits non-zero on any difference or any body without a manifest entry; `make check` runs `zoo verify`. `README.md` §"Running a pet project's real run": the five commands an operator types. Tests red on the parent: a manifest with a stale hash fails verify; a body not listed fails verify; `kind` is required. **End of run 1: the sink is ready for the pilot project's real run.** | awaiting A2 | 6 |
| A4 | **The replayer re-sends what was captured.** `zoo replay captures/<project>/<run-id> --to http://host:port [--raw\|--json] [--timing]` (SPEC §6): re-sends each body with its captured headers (content type and encoding intact) in receipt order; `--timing` sleeps the captured inter-arrival gaps through an injected `sleep`; prints each response status; exits non-zero if any status is not 2xx but still sends the rest. Tests: replaying a capture into a fresh sink produces byte-identical bodies and headers; `--timing` on a fake clock sleeps the recorded gaps. | awaiting A3 | 6 |
| A5 | **The audit: every capture through spanweave-live and spanweave, and what broke.** `zoo audit captures/<project>/<run-id>` (SPEC §7; the one module that imports both): (1) `zoo replay --raw` into `spanweave-live serve` and record every response status and every receiver event — a 415 on protobuf is a finding, not an error; (2) `zoo replay --json` into `serve` with a completion policy of `Cap(0)`-at-end (replay then signal end of input), collect each trace's final graph and every event; (3) for each trace, the records the receiver fed, in order, through `spanweave.build` — the live graph must equal the batch graph byte for byte (prefix consistency on a stranger's trace); (4) `spanweave inspect` on each graph: diagnostics by code, unmapped attributes by size, unknown kinds; (5) `agentgolden`'s `Signature` computed on each graph as a smoke, no rules evaluated. Output `audit/<project>-<run-id>.md`: a table per step, every diagnostic code with its count, every event, every divergence — each as a reproduction with the capture path and the command. **Findings are never fixed here**: each names the repo that owns it. | awaiting captures (A4 done and at least one `real` capture present) | 15 |
| A6 | **The series closes.** `TASKS.md` registry A0–A6 with shas; §3 and §4 folded; `reviews/` with every review byte-for-byte and sha256; `audit/` findings consolidated into `PROBES.md`: the next series' probe list for spanweave and spanweave-live, each with its capture and command; WORKPLAN.md deleted; PR `zoo` → `main`. No `plan:` commit follows. | awaiting A5 | 6 |

## 2. Execution order

Run 1 = A0 → A1 → A2 → A3, then stop: cold review (aux), decisions, and
the sink is handed to the pilot pet project for its real run. Run 2 = A4 →
A5 → A6 once at least one `real` capture is in `captures/`, then the scoped
review of the close and the PR. Every batch: CI green on the pushed tip
before `done`. A0 lands on `main` because the repository is empty; A1 onward
land on `zoo`.

## 3. Decisions log

| Date | Batch | Decision | By |
|---|---|---|---|
| 2026-10-09 | series | The fixture is what the exporter sent, not what the receiver understood: raw bytes are the record, the Collector's JSON re-encoding is a standards-made convenience kept beside them, and the receiver's answer to raw protobuf (expected: 415 today) is the audit's first finding, not something the zoo works around. The zoo fixes nothing; findings go to the owning repo's next series as probes. Pet projects know nothing of spanweave and are given only `EXPORT-CONTRACT.md` and one brief. | maintainer |

## 4. Resume note

- 2026-10-09: series opened. Nothing has run. The pilot pet project (Z4,
  streaming-concierge) is being built elsewhere; A3 is the point at which
  it can make its real run.

## 5. Origins

| ID | Origin |
|---|---|
| A0–A6 | The stranger's-trace decision of 2026-10-09 (this conversation): pet projects instrumented by stock instrumentors as the step before outside users; `EXPORT-CONTRACT.md`, `ZOO-BRIEFS.md`. |
| A2, A5(1) | The Python OTLP/HTTP exporter sends protobuf, not JSON (opentelemetry-python #1003, #2104); spanweave-live `serve` accepts JSON only (its R6). |
