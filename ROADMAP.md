# ROADMAP.md — the pet-project programme

What the zoo is for, in order: six small agents built by people who know
nothing about spanweave produce telemetry under stock instrumentation; the
zoo records it; the audit runs both libraries over every capture; the
findings become the probes each library's next series starts from. This
file is the programme's state and its checklist. `TASKS.md` is the registry
of what each zoo series did; `PROBES.md` is what the audits found;
`EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` are what an implementer gets.

## Status

| Project | Brief | Framework / instrumentation | Repository | Contract | Captured | Audited |
|---|---|---|---|---|---|---|
| Z1 `ledger-clerk` | nesting | LangChain / OpenInference | — | 1.3 | `captures/z1/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 2 bodies, the root in the last), `-recorded` (1 body) — `c24ab69` | series 2 (B7-Z1), `audit/z1-*.md`, with B6b's audit; PROBES L1 (again), L3 (again), S3, S7, S9 (again), S14–S15 — depth 8 to the five `fx_rate` tool nodes, every child's record before its parent's |
| Z2 `fan-out-researcher` | parallel tools | LlamaIndex / OpenInference | — | — | — | — |
| Z3 `echo-planner` | 25-turn history-resending loop, two instrumentors on one client | OpenAI Agents SDK / OpenInference ×2 | [SigorMatt/echo-planner](https://github.com/SigorMatt/echo-planner) `71bc477` | 1.2 | `captures/z3/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 4 bodies, the root in the last), `-recorded` (1 body) — `9b0268f` | series 2 (B7-Z3), `audit/z3-*.md`, PROBES L1 (again), L3, S3 (again), S6–S10; re-audited by B7r with B6a's audit (every policy, a row per node), reports replaced — L3, S6, S9, S10 observed further |
| Z4 `streaming-concierge` | streamed tool call, one manual root span | bare `openai` / OTel GenAI | [SigorMatt/streaming-concierge](https://github.com/SigorMatt/streaming-concierge) `553279a` | 1.0 (built), 1.1 (reviewed) | `captures/z4/2026-10-12-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`), `-recorded` — `47cb06c` | series 1, `audit/z4-*.md`, PROBES L1–L2, S1–S5; re-audited in series 2 by B7r with B6a's audit (every policy, a row per node), reports replaced — L2, S2, S5 observed further |
| Z5 `flaky-fetcher` | retries, `os._exit(0)` with no shutdown | LangGraph / OpenInference | [SigorMatt/flaky-fetcher](https://github.com/SigorMatt/flaky-fetcher) `2a3e778` | 1.2 | `captures/z5/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`), `-recorded` — one body each, four spans, no root — `f081997` | series 2 (B7-Z5), `audit/z5-*.md`, PROBES L1 (again), L4, S3 (again), S7 (again), S11–S13; re-audited by B7r with B6a's audit (every policy, a row per node), reports replaced — L4, S11, S12, S13 observed further |
| Z6 `crew-of-three` | agents nested under a crew, one client seen twice | CrewAI / OpenInference | — | — | — | — |

Suggested order for the rest: Z3 and Z5 first (each built to produce a shape
Z4 could not), then Z1, Z2, Z6 in any order. Projects are built with the
contract version current when they start; the version is in their
`MANIFEST.json`.

## The checklist, per project

1. **Build** — in its own repository, from `EXPORT-CONTRACT.md` (current
   version) and its brief in `ZOO-BRIEFS.md`, with no access to the spanweave
   repositories. Push. Report back under the contract's §6: every point where
   the contract or the brief left the implementer guessing.
2. **Contract feedback** — the §6 guesses are read before the next project
   starts; if any of them is a hole, the contract is bumped and the change
   listed at its end. (1.0 → 1.1 came from Z4's ten; 1.1 → 1.2 from Z4's
   captures.)
3. **Capture** — by the operator session, never by hand, with the README's
   commands: a pre-flight of the model against the gateway outside the
   instrumented app (a streamed completion with one tool; the model must
   stream one complete call), then `zoo capture --kind real` with
   `OPENAI_BASE_URL`/`OPENAI_API_KEY`/`MODEL=` from the machine's environment,
   then `--kind recorded`; fresh run-ids `<date>-real` and `<date>-recorded`;
   `make verify` after each; the project's `MANIFEST.json` restored;
   delegated commit `captures: zN real and recorded, <date>` with the gateway
   and model in the body; push. A run the gateway breaks is not the capture
   (contract §3): pick another model.
4. **Audit** — a zoo series batch: `zoo audit` on both captures, the reports
   under `audit/`, `PROBES.md` extended with every new probe (owner, capture,
   command, observed, expected or "to establish"), CI green. One batch per
   project, or one run for several that arrive together.
5. **Registry** — the project's row above updated; the series' `TASKS.md`
   row closed.

## After the sixth

When `PROBES.md` holds all six projects: the spanweave series written from
the S-probes (S1, the unclaimed attribute-less root, first — it reshapes the
rest), then the spanweave-live series from the L-probes (L2 and the
§1.1/§4.3 tension). Each library's series pins the zoo at the sha whose
captures it reproduces.

## Threads for zoo series 2

- **Port hand-off race**: `test_the_collector_killed_by_hand_mid_capture_is_a_problem`
  failed once in CI (`e50a56e`, PR run attempt 1) with the Collector's port
  taken between the zoo's pick and the Collector's bind; green on re-run
  with no code change. Fix: a bounded retry on bind failure, with a test
  that plants the collision.
- **Contract 1.2 manifests**: the zoo checks the project manifest it copies;
  1.2 adds `base_url` and fixes `started_at` to UTC `Z`. Confirm `verify`
  accepts 1.1 and 1.2 manifests and records which.
- **PR body wording**: PR #1's body says the merge is a fast-forward;
  `--merge` wrote `ebe12cf`. Future PR texts say "merge commit".
- **Model pre-flight as a zoo command**: the pre-flight in step 3 is a
  script in the operator prompt today; `zoo preflight --base-url --model`
  would make it a recorded fact beside the capture.

## Operating notes

- Credentials and gateway live on the operator's machine as environment
  variables (`NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, `NEBIUS_MODEL`); no prompt
  and no file in any repository carries them.
- `openai/gpt-oss-120b` through Nebius streams one tool call's deltas across
  two indices, the second without a name; a per-index assembler (the OpenAI
  convention) gets invalid JSON. `Qwen/Qwen3-235B-A22B-Instruct-2507` streams
  one complete call. Pre-flight before every real capture regardless.
- The OpenAI Agents SDK reads `vendor/` in a model id as a provider prefix,
  so `Qwen/Qwen3-...` reached no gateway until Z3 passed the id through
  unchanged (fixed at `71bc477`; contract 1.3 §4 now says so for everyone).
- With the stock batch span processor, a run shorter than its 5 s schedule
  delay that exits via `os._exit` exports nothing: no flush ever fires. Z5's
  brief gained a scripted 3 s retry backoff so the run outlasts the delay;
  the SDK defaults stay as they are (contract 1.3, "Changes from 1.2").
