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
| Z1 `ledger-clerk` | nesting | LangChain / OpenInference | [SigorMatt/ledger-clerk](https://github.com/SigorMatt/ledger-clerk) `4c150cc` | 1.3 | `captures/z1/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 2 bodies, the root in the last), `-recorded` (1 body) — `c24ab69` | series 2 (B8; audit code `4b57f18`), `audit/z1-*.md`; first audited by B7-Z1. PROBES L1, L3, S3, S7, S9, S14, S15 |
| Z2 `fan-out-researcher` | parallel tools | LlamaIndex / OpenInference | [SigorMatt/fan-out-researcher](https://github.com/SigorMatt/fan-out-researcher) `5883f9b` | 1.3 | `captures/z2/2026-10-14-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 3 bodies, the root in the last), `-recorded` (1 body) — `45305a8` | series 2 (B8; audit code `4b57f18`), `audit/z2-*.md`; first audited by B7-Z2. PROBES L1, L3, S3, S7, S9, S15–S18 |
| Z3 `echo-planner` | 25-turn history-resending loop, two instrumentors on one client | OpenAI Agents SDK / OpenInference ×2 | [SigorMatt/echo-planner](https://github.com/SigorMatt/echo-planner) `71bc477` | 1.2 | `captures/z3/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 4 bodies, the root in the last), `-recorded` (1 body) — `9b0268f` | series 2 (B8; audit code `4b57f18`), `audit/z3-*.md`; first audited by B7-Z3, again by B7r. PROBES L1, L3, S3, S6–S10, S15, S21 |
| Z4 `streaming-concierge` | streamed tool call, one manual root span | bare `openai` / OTel GenAI | [SigorMatt/streaming-concierge](https://github.com/SigorMatt/streaming-concierge) `553279a` | 1.0 (built; its manifest predates `contract_version`), 1.1 (reviewed) | `captures/z4/2026-10-12-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`), `-recorded` — `47cb06c` | series 2 (B8; audit code `4b57f18`), `audit/z4-*.md`; first audited in series 1 (A5), again by B7r. PROBES L1, L2, S1–S5 |
| Z5 `flaky-fetcher` | retries, `os._exit(0)` with no shutdown | LangGraph / OpenInference | [SigorMatt/flaky-fetcher](https://github.com/SigorMatt/flaky-fetcher) `2a3e778` | 1.2 | `captures/z5/2026-10-13-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`), `-recorded` — one body each, four spans, no root — `f081997` | series 2 (B8; audit code `4b57f18`), `audit/z5-*.md`; first audited by B7-Z5, again by B7r. PROBES L1, L4, S3, S7, S11–S13, S15 |
| Z6 `crew-of-three` | agents nested under a crew, one client seen twice (two instrumentors; one client seen once — S6) | CrewAI / OpenInference ×2 | [SigorMatt/crew-of-three](https://github.com/SigorMatt/crew-of-three) `78adcaf` | 1.3 | `captures/z6/2026-10-14-real` (Nebius, `Qwen/Qwen3-235B-A22B-Instruct-2507`; 11 bodies, the root in the last; the run departed from its script), `-recorded` (1 body) — `88dbcfd` | series 2 (B8; audit code `4b57f18`), `audit/z6-*.md`; first audited by B7-Z6. PROBES L1, L3, S3, S6, S7, S9, S15, S18–S22 |

Repository: the remote and the `HEAD` of the local checkout at the close
(`git -C ~/git/<project> remote get-url origin`, `rev-parse HEAD`), each
pushed and older than the project's captures. Contract: the
`contract_version` of the project manifest copied into the captures. Audited:
every report under `audit/` was written by the zoo's audit as it stood at
`4b57f18` (B6c), at the `audit` extra's pins, in the series-2 close (B8);
`PROBES.md` says how.

All six are built, captured and audited. They were taken in the order Z4, Z3
and Z5 (each built to produce a shape Z4 could not), Z1, Z2, Z6. Projects are
built with the contract version current when they start; the version is in
their `MANIFEST.json`.

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
   (contract §3): pick another model. A project that has never run has no
   manifest: one throwaway recorded run to a dead port writes it (and
   captures nothing), before the first `zoo capture`.
4. **Audit** — a zoo series batch: `zoo audit` on both captures, the reports
   under `audit/`, `PROBES.md` extended with every new probe (owner, capture,
   command, observed, expected or "to establish"), CI green. One batch per
   project, or one run for several that arrive together.
5. **Registry** — the project's row above updated; the series' `TASKS.md`
   row closed.

## After the sixth

`PROBES.md` holds all six projects (series 2's close, B8). Next: the spanweave
series written from the S-probes (S1, the unclaimed attribute-less root, first
— it reshapes the rest), then the spanweave-live series from the L-probes (L2
and the §1.1/§4.3 tension). Each library's series pins the zoo at the sha whose
captures it reproduces.

## Threads for zoo series 3

Series 2 closed two of the four threads this section carried: the port
hand-off race (B1: the race was the test harness's, which now retries a start
lost to it) and the PR body wording (the closing PR says "merge commit"). The
other two are carried, with the rest of what series 3 inherits, in `TASKS.md`
("Series 2", "Threads for series 3"):

- **Contract 1.2 manifests**: the zoo checks the project manifest it copies;
  1.2 adds `base_url` and fixes `started_at` to UTC `Z`. Confirm `verify`
  accepts 1.1 and 1.2 manifests and records which. (The committed captures
  carry 1.2 and 1.3 project manifests and verify; nothing under
  `spanweave_zoo/` reads `contract_version`.)
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
- A real run may depart from its project's script: Z6's real crew made two
  delegations, one `Ask question to coworker` and four lint passes where its
  brief scripts one send-back. The contract allows randomness in the real
  run, and the recorded capture is the script; the departure is the capture's
  own fact, not a defect (series 2's decisions log, 2026-10-14, "captures";
  PROBES S22).
- A project that has never run has no `MANIFEST.json`. Z6 had none before
  its first run; the operator's throwaway recorded run against a dead port
  wrote one and captured nothing — the method for any project that has never
  run (the checklist, step 3; series 2's decisions log, 2026-10-14,
  "captures").
