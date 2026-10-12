# section-operator — the README's operator flow, run as the operator (lead reviewer)

Date 2026-10-10, HEAD `040b194`, branch `zoo`, tree clean before and after.
Pet project: `https://github.com/SigorMatt/streaming-concierge` cloned fresh to
`~/git/streaming-concierge` (it was absent), HEAD `553279a`.

## Steps, exactly as README §"Running a pet project's real run" prints them

| step | typed | result |
|---|---|---|
| 1 | `uv sync --extra dev` | rc 0 |
| 2 | `make collector` | rc 0 — `cached …otelcol-contrib_0.162.0_linux_amd64.tar.gz`, `sha256 fcc06374… matches collector/SHA256SUMS` |
| 3 | `uv run zoo capture --project z4 --run-id 2026-10-10T11-57-22Z --kind recorded --project-manifest ~/git/streaming-concierge/MANIFEST.json` | ready in <1 s; readiness line printed once |
| 4 | (in the pet checkout) `make run-recorded ENDPOINT=http://localhost:4318` | rc 0; venv built, stub on 18787, 3-turn conversation incl. one tool call |
| 5 | Ctrl-C — delivered as a terminal does, SIGINT to the capture's foreground process group (`setsid` + `kill -INT -- -<pgid>`) | **exit 1, `PROBLEM: collector exited: 0`** |
| 6 | `make verify` | **rc 2** (zoo verify rc 1): `MANIFEST.json records a problem from the run: collector exited: 0` |
| — | `make check` | **rc 2**: ruff/mypy clean, 297 passed, gates 31 passed, then `verify` red on the capture |

The `--project-manifest` path was given as `~/git/streaming-concierge/MANIFEST.json`
per the review prompt; from `~/git/spanweave-zoo` that is the README's
`../streaming-concierge/MANIFEST.json`.

Step 3 had to run in the background, because the reviewer has no second interactive terminal. Its output went to a
scratchpad log (not the README's `capture.log` in the checkout).

## What was captured

- `raw/0001.body` — **1 body**, 6,884 bytes, `content-type: application/x-protobuf`,
  no content-encoding, `user-agent: OTel-OTLP-Exporter-Python/1.45.1`.
- `json/0001.json` — 9,543 bytes, `application/json` (the Collector's re-encoding).
- Run directory: MANIFEST.json, bodies.jsonl, forwards.jsonl, raw/0001.{body,headers.raw,headers.json},
  json/0001.{json,headers.raw,headers.json}; manifest `files` = 6 entries, `bodies` = 2 — every
  file except MANIFEST.json listed.
- `forwards`: `[{"file": "raw/0001.body", "status": 200}]`.
- **Span ids: equal.** A hand protobuf walk of `raw/0001.body` gives 5 spans of one trace
  `d68bcee76ca741f33daa26355b80eb26` — root `7d6f4e93051044aa concierge.conversation` and four
  `chat stub-concierge-1` children `6697fb0009da4116`, `9c99ae045a27a521`, `a39a8668aaa4cb7c`,
  `e8c0fa1b7a8c2183`. The `(trace, span, parent, name)` set from `json/0001.json` is identical.
- **project manifest `started_at` is from this run:** capture `started_at`
  `2026-10-10T11:57:22.740797+00:00`; the copied project manifest's `started_at`
  `2026-10-10T11:58:00.324198+00:00` (after the capture began, before `ended_at`
  `11:58:14.198178`). The file on disk before the run said `2026-10-09T18:57:48…` —
  the end-of-run copy is the one the recorded run wrote (F4 / A3b holds).

## OP-1 — Ctrl-C, the README's only way to end a capture, marks every capture failed  (blocks Z4 capture)

A terminal's Ctrl-C sends SIGINT to the whole foreground process group. `otelcol-contrib` is
spawned in zoo's group (no `start_new_session` / `process_group` anywhere in `spanweave_zoo/` —
`grep -n "start_new_session\|process_group\|setsid" spanweave_zoo/*.py` is empty), so it receives
the SIGINT itself, shuts down (`Received signal from OS … "signal": "interrupt"` … `Shutdown complete.`)
and exits 0 *before* zoo's orderly stop reaches it; zoo then records it as a mid-capture death:

```
zoo capture: stopping
…otelcol… Received signal from OS {"signal": "interrupt"} … Shutdown complete.
  ! collector exited: 0 -- the raw bytes are still being recorded, json/ is not (SPEC.md section 4.6)
zoo capture: 2 body/bodies under captures/z4/2026-10-10T11-57-22Z/, MANIFEST.json written: kind=recorded, PROBLEM: collector exited: 0
```

Reproduced in scratch captures (ports 4481–4484, `--captures` under the scratchpad, one
fixture body by curl, a project manifest dated after the start):

| how it was stopped | runs | exit | problems | verify |
|---|---|---|---|---|
| SIGINT to the process group (= terminal Ctrl-C) | 4 / 4 | 1 | `["collector exited: 0"]` | fails |
| SIGINT to the zoo python PID only | 2 / 2 | 0 | none | OK |
| SIGTERM to the zoo python PID only | 1 / 1 | 0 | none | OK |

So the README's step 5 produces a capture that `zoo verify` and `make check` reject, and the
operator cannot tell it from a real Collector death. A capture is immutable, so a Z4 capture
taken this way is permanently marked failed. Workaround until fixed: end the capture with
`kill -INT <zoo pid>` / `kill -TERM <zoo pid>`. That is not what the README says. Root-cause detail and the commit
that introduced it: section-a3a.

## OP-2 — `zoo verify`'s closing line is false for a problems-only failure  (next batch)

On a capture whose every byte re-hashes and whose only failure is a recorded problem, verify
ends `zoo verify: 1 problem(s). A capture is immutable (CLAUDE.md section 0.6): these bytes are
not the bytes that were recorded.` The bytes are the bytes that were recorded. The operator is told
the capture was tampered with when the run itself reported a problem.

## README vs behaviour — every difference seen

1. **Step 5 (Ctrl-C)** — README: Ctrl-C "stops the raw sink, lets the Collector flush its last
   batch, stops the json sink, copies the project's MANIFEST.json, completes the capture" and exits
   non-zero only for a forward failure, a Collector death or a manifest problem. Behaviour: Ctrl-C
   *is* reported as a Collector death (OP-1), exit 1. ("SIGTERM does the same" is true only of a
   SIGTERM sent to the zoo PID — and that one does *not* produce the problem.)
2. **Step 6** — README: `make verify` "re-hashes every capture … from then on every run of the gates
   re-checks this capture's bytes". Behaviour: red, so `make check` is red from then on until the capture is removed.
3. **Step 3** — README §"The tee": "then `zoo capture` prints one line -- `the raw bytes are the
   record. Ctrl-C to stop.`". Behaviour: the readiness line is preceded by 7 Collector `info` log
   lines (A3a moved the log level warn → info to read the ready line), and the Collector's
   shutdown log lines are interleaved at stop. The readiness line itself is printed exactly once.
4. **Step 3 progress** — README: "one line per recorded body". Behaviour: one line per body *on
   each side* (`raw/0001.body …`, `json/0001.json …`), and the summary says `2 body/bodies` for a
   run where the project sent one export. `zoo verify` says the same. A reader counting
   exports from either is off by ×2 (thread).
5. **Step 2** — README: "checks its sha256 against the release's own digest". Behaviour: against
   the checked-in `collector/SHA256SUMS` (copied from the release's `.sha256`), and from the
   cache when present: `cached …`, no download. (Also found by section-a0a, A0a-4.)
6. **Supervisor form** — writes `capture.log` into the zoo checkout, and `captures/` is
   deliberately not ignored but `capture.log` is not either, so an operator who follows it gets an
   untracked file beside the capture (thread).
7. **Not a zoo difference, but the operator meets it:** the pet project commits its
   `MANIFEST.json`, so step 4 leaves `~/git/streaming-concierge` with ` M MANIFEST.json` (left
   as is: the clone is the operator's).

## Cleanup

`rm -rf captures/z4/2026-10-10T11-57-22Z` (then the empty `captures/z4`, `captures/`).
`git status --short` in `~/git/spanweave-zoo`: empty; `## zoo...origin/zoo`. Scratch captures
live only under the scratchpad; no listener left on 4317–4320 or 4481–4484.
