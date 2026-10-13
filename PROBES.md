# PROBES.md — what the next series of each library starts from

Series 1 of the zoo (`TASKS.md`) closed with one audit, `zoo audit`
(`SPEC.md` §7), over Z4's two captures. Its reports are `audit/z4-2026-10-12-real.md`
and `audit/z4-2026-10-12-recorded.md`. Series 2 adds Z3's (B7-Z3):
`audit/z3-2026-10-13-real.md` and `audit/z3-2026-10-13-recorded.md`; and Z5's
(B7-Z5): `audit/z5-2026-10-13-real.md` and `audit/z5-2026-10-13-recorded.md`. B7r
re-audited all six captures with the one audit as B6a left it (`07285bd`:
step 2 under each completion policy, step 4 a row per node) and **replaced**
the six reports in place, same filenames; every probe below cites the
re-audit's reports, and an observation the earlier reports could not make is
marked *(B7r)*. This file consolidates them into the probe list each owning
repository's next series starts from.

A probe is a reproduction, never a fix (`CLAUDE.md`, standing rule 7): a
capture, a command, what was observed, what the audit expected, and the
repository that owns it. Nothing below is fixed or worked around here, and
nothing below says how it should be fixed; that belongs to the owner's series.
The owner is named by `SPEC.md` §7.4's table.

**Pins.** Every observation below was made at `spanweave@fec7da27af517ad8b58ae3ec57827916aae60674`
(0.9.1), `spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` (0.0.1) and
`agentgolden@aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0), the `audit`
extra's pins, with the stock Collector 0.162.0 — Z4's, Z3's and Z5's alike (each
report's header records the three shas, pinned and installed). The six reports
were all written by one audit, the zoo's at B6a (`07285bd`), re-run by B7r
with the pins unchanged; the step-2 policy runs' `--quiet 0` and
`--root-grace 0` are the audit's values, not the receiver's (each report's
"Method", `SPEC.md` §7.3).

**Reproducing everything at once**, from a checkout of this repository:

```bash
uv sync --extra dev --extra audit
uv run zoo verify captures/z4/2026-10-12-real
uv run zoo verify captures/z4/2026-10-12-recorded
uv run zoo audit captures/z4/2026-10-12-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z4/2026-10-12-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo verify captures/z3/2026-10-13-real
uv run zoo verify captures/z3/2026-10-13-recorded
uv run zoo audit captures/z3/2026-10-13-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z3/2026-10-13-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo verify captures/z5/2026-10-13-real
uv run zoo verify captures/z5/2026-10-13-recorded
uv run zoo audit captures/z5/2026-10-13-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z5/2026-10-13-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
```

The reports it writes differ from the committed ones only in the `listening`
port and the clock readings in a `completed` or `late_arrival` event (each
report's "Method"). B7r checked it: a second run of all six audits, normalised
for those two things alone, was identical to the committed reports line for
line, so no difference in the audit's method was found. Z3's `real` audit takes
about 23 s (its two timed replays sleep the captured gaps); the others about a
second.
Each probe also gives the step's own commands, as the reports print them.

**Count.** spanweave-live: 4 (L1–L2 from Z4, L1 seen again in Z3 and Z5; L3
from Z3; L4 from Z5). spanweave: 13 (S1–S5 from Z4, S3 seen again in Z3 and
Z5; S6–S10 from Z3, S7 seen again in Z5; S11–S13 from Z5). agentgolden: 0
(step 5's `signature` ran clean on every written graph of all six captures).
B7r's re-audit added no probe and no finding: each report's findings are the
ones it had (Z4 3, Z3 1, Z5 1, per report), and its new observations are
written into the probes they answer. A probe marked *to establish* is an
observation the audit made and could not explain from its own report; it
asserts nothing.

---

## spanweave-live

### L1. The exporter's own bytes are answered 415

- **From:** finding F1 in both reports (step 1).
- **Captures:** `captures/z4/2026-10-12-real` (`raw/0001.body`, `raw/0002.body`);
  `captures/z4/2026-10-12-recorded` (`raw/0001.body`).
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 2
  uv run zoo replay captures/z4/2026-10-12-real --to http://127.0.0.1:<port> --raw
  ```

  (`--requests 1` and `…-recorded` for the recorded capture.)
- **Observed:** every body answered 415, event `unsupported_media_type`:
  `'application/x-protobuf' is not 'application/json'; this endpoint reads
  OTLP/HTTP JSON and not protobuf`. 3 of 3 bodies across the two captures.
- **Expected (the audit's):** 2xx — each body is the export as the stock Python
  OTLP/HTTP exporter sent it, unmodified (`zoo verify` passes on both).
- **Seen again in Z3** (B7-Z3, finding F1 in both Z3 reports):
  `captures/z3/2026-10-13-real` (`raw/0001.body`–`raw/0004.body`, `--requests 4`)
  and `captures/z3/2026-10-13-recorded` (`raw/0001.body`, `--requests 1`), the
  same commands with `z3/2026-10-13-*` for `z4/2026-10-12-*`. Every body answered
  415, the same event and detail: 5 of 5 bodies across the two captures.
- **Seen again in Z5** (B7-Z5, finding F1 in both Z5 reports):
  `captures/z5/2026-10-13-real` and `captures/z5/2026-10-13-recorded`
  (`raw/0001.body` each, `--requests 1`), the same commands with
  `z5/2026-10-13-*`. Both bodies answered 415, the same event and detail: 2 of
  2 bodies across the two captures.
- **Re-audit (B7r):** F1 again in all six re-audited reports, the same bodies,
  status and detail.

### L2. A record `serve` routed reaches no graph, and no event says where it went

- **From:** finding F3 in both reports (step 3). Same record as S1.
- **Captures:** `captures/z4/2026-10-12-real` (`json/0002.json` record 2);
  `captures/z4/2026-10-12-recorded` (`json/0001.json` record 5).
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 2
  uv run zoo replay captures/z4/2026-10-12-real --to http://127.0.0.1:<port> --json
  ```

  (`--requests 1` and `…-recorded` for the recorded capture.) The command runs
  without `--deltas`, as the audit's step 2 does.
- **Observed:** `finished` reports `routed: 5`; the one graph `serve` wrote holds
  4 of them. The fifth — Z4's root span, which no adapter claims (S1) — went to
  the no-trace builder, which is never completed and never written, and no
  event names it.
- **Expected (the audit's):** each record of a trace reaches that trace's
  graph, or an event says where it went. At the pinned sha, spanweave-live's
  `SPEC.md` §4.3, §5.4 and §8.5 describe the route the record took.
- **The owner's spec, at `cddc694`:** beside §4.3, §5.4 and §8.5, its §1.1
  promises "'no trace id' and a counted event" for a record whose trace id
  cannot be had through the adapter surface, and its §1.5 says every decision
  is "an event with a code"; its §4.3 says the receiver "invents no event code"
  for that record's diagnostics. The tension between §1.1/§1.5 and §4.3, inside
  the owner's own spec, is the strongest form of this probe.
- **Note:** `stderr` is not `serve`'s only output. With `--deltas` added to the
  same command, `serve` writes 5 delta lines to stdout on the real capture, and
  the fifth (empty `trace_id_after`) carries `concierge.conversation`,
  `unclaimed_record` and `missing_trace_id` (spanweave-live's `SPEC.md` §6.3,
  §8.4). The record is reported there as a delta; no event on stderr, and no
  count in `finished`, names it.
- **Under each completion policy (B7r)**, step 2 of both re-audited Z4
  reports: F3 is the end-of-input run's and stands; the two policy runs
  (`serve ... --quiet 0 --requests N` and `... --root-grace 0 --requests N`,
  replayed `--timing`) yield no finding by the audit's rule (`SPEC.md` §7.3)
  and are observations. In neither does any event name the fifth record, and
  each `finished` reports `routed: 5`. Real (gap before `json/0002.json`
  0.202147 s): `--quiet 0` completes the trace twice — generation 1 at
  `index` 3, written `graphs/612628c796e094bd26041bf735576133.json`, then a
  `late_arrival` at `index` 4 and generation 2 at `index` 5, written
  `graphs/612628c796e094bd26041bf735576133.2.json`, released "at version 1"
  — `completed: 2`, `late_arrival: 1`, `written: 2`; `--root-grace 0`
  completes it once, at `index` 5, `the cap policy fired on Cap(records=0)`
  — the end-of-input `Cap(0)`, not `RootEnded`. Recorded (one body): `--quiet
  0` completes it once at `index` 5 by the quiet policy; `--root-grace 0`
  once at `index` 5 by the end-of-input `Cap(0)`.

### L3. A trace whose root arrives in the last of four bodies: one completion at the end of input; four under `--quiet 0`, one under `--root-grace 0`

- **From:** step 2 and step 3 of `audit/z3-2026-10-13-real.md`; not a finding
  under `SPEC.md` §7.4. B7-Z3's first point of interest, reported as observed.
- **Captures:** `captures/z3/2026-10-13-real` (4 bodies; the operator's capture
  commit and `ROADMAP.md` record the root span in the fourth);
  `captures/z3/2026-10-13-recorded` (1 body) beside it.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 4
  uv run zoo replay captures/z3/2026-10-13-real --to http://127.0.0.1:<port> --json
  ```

- **Observed:** all 4 bodies answered 200. `serve` wrote one `completed` event,
  at `index` 102, `the cap policy fired on Cap(records=0)` — the end-of-input
  `Cap(0)` of `serve --requests N` (the report's Method) — then one `written`
  and one `released`; `finished` reports `routed: 102`, `completed: 1`,
  `written: 1`. No event names a completion before the end of input. The one
  graph, `graphs/7a93d1ee6fc28e193585910fc2ce5906.json`, holds all 102 records
  (json/0001 records 1–24, 0002 1–32, 0003 1–32, 0004 1–14); `spanweave
  inspect` reports 102 nodes and 101 explicit `parent` edges, and no
  `orphan_parent` diagnostic. Live, batch and incremental are equal (1,433,357
  bytes). The recorded capture (one body, 102 records) gives the same node,
  edge and diagnostic counts.
- **Observed under each completion policy (B7r)**, step 2 of the re-audited
  `audit/z3-2026-10-13-real.md` — the line that was *to establish* here ("a
  completion policy firing on the first three bodies, before the root
  arrived, was not exercised"):

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --quiet 0 --requests 4
  uv run zoo replay captures/z3/2026-10-13-real --to http://127.0.0.1:<port> --json --timing
  ```

  (The second run: `--root-grace 0` in place of `--quiet 0`.) The replay slept the
  captured gaps — none, 5.00924 s, 5.01494 s, 0.797305 s — and all 4 bodies
  answered 200 in both runs.
  - `--quiet 0`: four `completed` events, each `the quiet policy fired on
    Quiet(seconds=0.0)`, at `index` 24, 56, 88 and 102 — generations 1 to 4,
    one per body (24, 32, 32 and 14 records absorbed) — with a `late_arrival`
    opening generations 2, 3 and 4 at `index` 25, 57 and 89. Four graphs
    written: `graphs/7a93d1ee6fc28e193585910fc2ce5906.json`, `.2.json`,
    `.3.json`, `.4.json`; `finished`: `completed: 4`, `late_arrival: 3`,
    `written: 4`, `released: 4`, `routed: 102`. The first three were
    completed and written before the body carrying the root arrived.
  - `--root-grace 0`: one `completed`, at `index` 102, `the root_ended policy
    fired on RootEnded(grace_seconds=0.0)`, generation 1; one graph written,
    `graphs/7a93d1ee6fc28e193585910fc2ce5906.json`, released at version 102;
    `finished`: `completed: 1`, `written: 1`, `routed: 102`.
  - The recorded capture (one body, `audit/z3-2026-10-13-recorded.md`):
    one `completed` at `index` 102 under each policy — `Quiet(seconds=0.0)`
    and `RootEnded(grace_seconds=0.0)` respectively — and one graph.

  The values are the audit's, `0` for each (`SPEC.md` §7.3); no other value of
  `--quiet` or `--root-grace`, and no `--cap`, was exercised. Step 3 compares
  only the end-of-input run's graph, so the four generation graphs under
  `--quiet 0` were not compared with anything.
- **Node table (B7r):** step 4 of both re-audited Z3 reports gives one node
  whose parent is *no* (its record states none): `448817e27ad9f3b1` (real),
  `e5cd88a577106085` (recorded), kind `agent`, status `ok`. Every other node's
  parent is present (*yes*, 101 of 102). The table does not say which body a
  node's record came from.

### L4. A trace with no root: completed by `Quiet(0)` under `--quiet 0`; under `--root-grace 0`, by the end-of-input `Cap(0)`, never by `RootEnded`

- **From:** step 2 and step 3 of both Z5 reports; not a finding under
  `SPEC.md` §7.4. B7-Z5's first point of interest, reported as observed: Z5
  exits via `os._exit(0)` with no shutdown (`ZOO-BRIEFS.md`, Z5), and
  `WORKPLAN.md`'s B7-Z5 row records one body each, four spans and no root.
- **Captures:** `captures/z5/2026-10-13-real`, `captures/z5/2026-10-13-recorded`.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 1
  uv run zoo replay captures/z5/2026-10-13-real --to http://127.0.0.1:<port> --json
  ```

  (`…-recorded` for the recorded capture.)
- **Observed:** the one body answered 200. `serve` wrote one `completed`
  event, at `index` 4, `the cap policy fired on Cap(records=0): this trace had
  absorbed 4 records` — the end-of-input `Cap(0)` of `serve --requests N` (the
  report's Method) — then one `written` and one `released`; `finished` reports
  `routed: 4`, `completed: 1`, `written: 1`, on each capture. The one graph
  per capture (`graphs/3072629a56dca029bd8c19818bbebbc4.json` real,
  `graphs/88167a239e683f6a5db73ac739bce4fe.json` recorded) holds all 4
  records; live, batch and incremental are equal (17,691 bytes each).
  `spanweave inspect` reports 4 nodes (`chain` 2, `tool` 2), 2 explicit
  `parent` edges and `orphan_parent` × 2 (S12). No `llm` node is in either
  graph, and step 5's signature names two `tool:http_get` steps; Z5's brief
  scripts three `http_get` calls and one LLM summary.
- **Observed under each completion policy (B7r)** — the line that was *not
  observable from the audit* here (what `Quiet` and `RootEnded` did with this
  trace). Step 2 of both re-audited Z5 reports:

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --quiet 0 --requests 1
  uv run zoo replay captures/z5/2026-10-13-real --to http://127.0.0.1:<port> --json --timing
  ```

  (The second run: `--root-grace 0` in place of `--quiet 0`; `…-recorded` for
  the recorded capture.) The one body answered 200, no gap slept, in every
  run.
  - `--quiet 0`: one `completed`, at `index` 4, `the quiet policy fired on
    Quiet(seconds=0.0)`, generation 1; one graph written; `finished`:
    `completed: 1`, `written: 1`, `routed: 4` — on each capture.
  - `--root-grace 0`: one `completed`, at `index` 4, `the cap policy fired on
    Cap(records=0)` — the end-of-input `Cap(0)` of `--requests N`; no event
    names `RootEnded`. One graph written; `finished` as above — on each
    capture.

  The pinned receiver has no default for either flag (`OPEN_QUESTIONS.md`
  §8); `0` is the audit's value (`SPEC.md` §7.3).
- **To establish:** what `serve --cap N` does with this trace, and what
  `--quiet S` and `--root-grace S` do at values other than `0` — none of
  these is exercised by the audit. Whether `RootEnded` ever completes a trace
  with no root on a receiver whose input does not end is not shown either:
  here the input ended at the one request, and under `--root-grace 0` no
  event before the end-of-input `Cap(0)` names a completion.

---

## spanweave

### S1. Z4's root span is claimed by no adapter

- **From:** finding F2 in both reports (step 3).
- **Captures:** `captures/z4/2026-10-12-real` (`json/0002.json` record 2);
  `captures/z4/2026-10-12-recorded` (`json/0001.json` record 5) — the root span
  `concierge.conversation` in each.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 2
  uv run zoo replay captures/z4/2026-10-12-real --to http://127.0.0.1:<port> --json
  ```

  then `spanweave.adapters.classify(record)` on each record
  `spanweave_live.Endpoint` reads from the body (the audit's step 3 does exactly
  this; `zoo audit` above runs it).
- **Observed:** `classify` returned `()` for that record. Building it alone
  raised `AdapterSelectionError` (`adapter_unconfident`: openinference 0.00,
  otel_genai 0.00), batch and incremental alike. F2 again in both re-audited Z4
  reports (B7r), the same record.
- **Expected (the audit's):** an adapter claims each record of an OTLP export
  `read_records` unpacked, so its trace id can be had through the adapter
  surface.

### S2. `orphan_parent` on every chat span

- **From:** step 4's table in both reports; not a finding under `SPEC.md` §7.4,
  which leaves step 4's tables to this file.
- **Captures:** both Z4 captures; trace `612628c796e094bd26041bf735576133`
  (real) and `9264505bc6b829dd4330b31460bef36f` (recorded).
- **Command:** after the step-2 commands of L2,

  ```bash
  uv run spanweave inspect graphs/612628c796e094bd26041bf735576133.json
  ```

- **Observed:** `orphan_parent` × 4 — each of the four `llm` nodes. Their
  parent is the root span of S1, which is not in the graph.
- **Node table (B7r)**, step 4 of both re-audited Z4 reports: each of the four
  `llm` nodes — `a700993010700621`, `317657789bb0f148`, `a90c8b9b28c8e710`,
  `17eb31438da683f1` (real); `1c22728149a3ec83`, `afa87e72e4b4c576`,
  `30498d48d228299f`, `08800207f04dcccd` (recorded) — has parent *absent from
  graph* and carries `orphan_parent`; status `unset`; model
  `Qwen/Qwen3-235B-A22B-Instruct-2507` (real), `stub-concierge-1` (recorded);
  span events *absent*. The table does not give the absent parent's id.
- **To establish:** whether these four follow from S1 alone — the report
  names no parent id, so it does not show the four absent parents are S1's
  root span.

### S3. `timestamp_unit_suspect` on every span

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** `timestamp_unit_suspect` × 4 on each graph, from the stock
  Collector's OTLP/JSON re-encoding of a stock exporter's export.
- **To establish:** what in the record raises the suspicion, and whether it is
  warranted on this input.
- **Seen again in Z3** (B7-Z3, step 4 of both Z3 reports): `timestamp_unit_suspect`
  × 102 — once per node — on `graphs/7a93d1ee6fc28e193585910fc2ce5906.json`
  (real) and `graphs/87d538e303fcbd1860df2b8c2fbb58f4.json` (recorded), through
  the `openinference` adapter this time rather than `otel_genai`.
- **Seen again in Z5** (B7-Z5, step 4 of both Z5 reports): `timestamp_unit_suspect`
  × 4 — once per node — on `graphs/3072629a56dca029bd8c19818bbebbc4.json`
  (real) and `graphs/88167a239e683f6a5db73ac739bce4fe.json` (recorded), through
  `openinference`.
- **Node table (B7r):** in all six re-audited reports every node's row carries
  `timestamp_unit_suspect`, once (4 + 4 Z4, 102 + 102 Z3, 4 + 4 Z5). The
  *to establish* above stands: the table names the code per node, not what
  raised it.

### S4. `unmapped_attributes` on every span

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** 4 diagnostics on each graph (2,044 bytes real, 2,152 bytes
  recorded, as compact sorted JSON), each naming `<record>.flags`,
  `<record>.kind`, `<record>.resource_spans`, `<record>.scope_spans`,
  `gen_ai.provider.name`, `gen_ai.response.id`, `gen_ai.response.model` and
  `server.address`; the recorded capture adds `server.port`. Unchanged in the
  re-audited reports (B7r); every node's row carries `unmapped_attributes`.
- **To establish:** which of these the `otel_genai` adapter is meant to map.

### S5. `unpaired_call` once per graph

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** `unpaired_call` × 1 on each graph.
- **Node table (B7r)**, step 4 of both re-audited Z4 reports: the one
  `unpaired_call` is on the second `llm` node in graph order —
  `317657789bb0f148` (real), `afa87e72e4b4c576` (recorded) — the line that was
  *to establish* as "which call is unpaired", observed as which node carries
  it.
- **To establish:** whether it follows from S1.

### S6. Two instrumentors on one client: 50 `llm` nodes, every record claimed

- **From:** steps 3–5 of both Z3 reports; not a finding under `SPEC.md` §7.4.
  B7-Z3's third point of interest, reported as observed: Z3 runs two
  instrumentors on one client (`ROADMAP.md`), expected to emit a `generation`
  and a `ChatCompletion` span for every turn.
- **Captures:** `captures/z3/2026-10-13-real`, `captures/z3/2026-10-13-recorded`.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 4
  uv run zoo replay captures/z3/2026-10-13-real --to http://127.0.0.1:<port> --json
  uv run spanweave inspect graphs/7a93d1ee6fc28e193585910fc2ce5906.json
  ```

  (`--requests 1`, `…-recorded` and `graphs/87d538e303fcbd1860df2b8c2fbb58f4.json`
  for the recorded capture.)
- **Observed:** on each capture, 102 nodes, all from `openinference 0.1.0`
  (`nodes by adapter`): `agent` 2, `chain` 26, `llm` 50, `tool` 24; `unknown`
  nodes 0. No record went unclaimed — step 3 has no `classify` finding, and
  `routed` (102) equals the records in the graph. Step 5's signature has 50
  `llm` steps, in 25 adjacent pairs, each pair after a `chain` step and all
  but the last followed by one `tool` step — on both captures.
- **Node table (B7r)**, step 4 of both re-audited Z3 reports: the report now
  names every node. In graph order the 50 `llm` nodes stand in 25 adjacent
  pairs, as the signature's steps do (the table's kinds and the signature's
  agree step for step); all 50 have their parent present (*yes*), status `ok`,
  and span events *absent*. In pairs 1–16 both nodes carry the model; in
  pairs 17–25 the first node's model is *absent* and the second's present
  (S10). All 102 nodes are status `ok`.
- **To establish:** which span each of the 50 `llm` nodes comes from — the
  node table gives id, kind, status, model, parent and diagnostics, not the
  span's name or its parent's id, so whether they are one `generation` and one
  `ChatCompletion` per turn, and whether spanweave relates the two of a pair,
  is still not shown by it.

### S7. `unmapped_attributes` on every node, 363 kB of OpenInference keys

- **From:** step 4's table in both Z3 reports.
- **Captures and command:** as S6.
- **Observed:** 102 `unmapped_attributes` diagnostics on each graph — one per
  node — taking 362,893 bytes (real) and 363,830 bytes (recorded) as compact
  sorted JSON, of a 1,433,357-byte (real) graph. Beyond Z4's four `<record>.*`
  keys (S4), on all 102: `llm.output_messages.0.message.role` (50),
  `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`
  (48), the indexed `llm.input_messages.<n>.message.{role,content,tool_calls.<m>.tool_call.{id,function.name,function.arguments},tool_call_id}`
  keys up to `<n>` = 49 (at most 35 diagnostics for any one, 36 recorded), `llm.invocation_parameters`
  (34), `llm.system` (32), `llm.finish_reason` (25), `tool.description` and
  `tool.parameters` (24 each), `llm.tools.<n>.tool.json_schema` (16 real, 16
  and 17 recorded), `llm.output_messages.0.message.content` (2), `agent.name`
  and `graph.node.id` (1 each). The two captures' key sets are the same; nine
  of their counts differ by one.
- **To establish:** which of these the `openinference` adapter is meant to map
  — the history-resending loop (Z3's brief) makes each turn's `llm` node carry
  every earlier message again, so the indexed keys grow with the turn.
- **Seen again in Z5** (B7-Z5, step 4 of both Z5 reports): 4
  `unmapped_attributes` diagnostics on each graph — one per node — taking
  1,620 bytes as compact sorted JSON, on both captures. Keys: Z4's four
  `<record>.*` keys (4 each), `metadata` (4), `<record>.events` (2),
  `tool.description` (2). `metadata` was named in neither Z3 report;
  `<record>.events` is S11's.

### S8. `<record>.droppedAttributesCount` on 18 nodes; what was dropped is absent

- **From:** step 4's table in both Z3 reports. B7-Z3's second point of
  interest, reported as observed.
- **Captures and command:** as S6.
- **Observed:** `<record>.droppedAttributesCount` is an unmapped key in 18 of
  the 102 `unmapped_attributes` diagnostics, on each capture. The 599
  `Attributes dict is full` lines B7-Z3's row names are not part of the zoo's
  record — no file under `captures/z3/` holds them — so the audit cannot relate
  a line to a span. What was dropped is not in the export as received: the
  record carries a count, and the report shows the attributes that arrived,
  never the ones that did not.
- **To establish:** whether spanweave should surface a span's dropped-attribute
  count as more than an unmapped key, and which 18 nodes carry it — the
  re-audit's node table (B7r) names the diagnostic codes on each node, not the
  unmapped keys a diagnostic names, so it still does not show the 18. The
  exporter's attribute limit is the instrumentation's, not any of the three
  libraries'.

### S9. `unpaired_call` × 48

- **From:** step 4's table in both Z3 reports.
- **Captures and command:** as S6.
- **Observed:** `unpaired_call` × 48 on each graph, beside 24 `tool` nodes, 50
  `llm` nodes, and 48 derived `temporal` edges;
  `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments` is
  unmapped on 48 nodes.
- **Node table (B7r)**, step 4 of both re-audited Z3 reports — the line that
  was *to establish* as "which calls are unpaired", observed as which nodes
  carry the diagnostic: one `unpaired_call` on each of 48 `llm` nodes, every
  `llm` node but the last pair in graph order (`9ba382d983e377cc` and
  `abc456bd1503ec60` real, `4feb2fa9b583d910` and `181957d46e2096c9` recorded,
  which carry none); no `tool`, `chain` or `agent` node carries one.
- **To establish:** whether the 48 follow from two `llm` nodes per tool call
  (S6).

### S10. Nine `llm` steps carry no model

- **From:** step 5 of both Z3 reports.
- **Captures and command:** as S6, then `agentgolden.signature.signature(graph)`
  on the `Builder`'s graph (the audit's step 5; `zoo audit` above runs it).
- **Observed:** of the 50 `llm` steps, 41 carry the model
  (`llm:Qwen/Qwen3-235B-A22B-Instruct-2507` real, `llm:echo-planner-stub`
  recorded) and 9 carry `llm:-`. The signature raised on neither graph.
- **Observed in the node table (B7r)** — the line that was *to establish*
  ("whether those 9 nodes carry no model in the graph or carry one the
  signature does not read"): step 4 of both re-audited Z3 reports shows the
  `model` key absent from `Node.attributes` (spanweave's normalized subset) on
  exactly 9 `llm` nodes, and they are the 9 `llm:-` steps, position for
  position: the first `llm` node of each of the last nine pairs (pairs
  17–25 in graph order; e.g. `c6bc024ad4607d9a`, the first, real). The graph
  carries no model on them; the signature reads the graph as it is.
- **To establish:** whether those nine records carry a model under a key the
  `openinference` adapter does not map, or carry none (S8's dropped
  attributes are on 18 nodes, not shown which) — the node table does not tie
  an unmapped key to a node.

### S11. Two `http_get` tool nodes, status `error`; their span events are an unmapped key

- **From:** steps 4 and 5 of both Z5 reports; not a finding under `SPEC.md`
  §7.4. B7-Z5's second point of interest, reported as observed: the B7-Z5 row
  records two `http_get` spans in ERROR with `exception` events, and Z5's
  brief scripts the first two `http_get` calls to raise a `ConnectionError`.
- **Captures and command:** as L4, then

  ```bash
  uv run spanweave inspect graphs/3072629a56dca029bd8c19818bbebbc4.json
  ```

  (`graphs/88167a239e683f6a5db73ac739bce4fe.json` for the recorded capture).
- **Observed:** on each capture, 2 `tool` nodes, and step 5's signature names
  both `tool:http_get`. `inspect` reports payloads `inputs present: 4`,
  `outputs present: 2`, `outputs absent: 2`. `<record>.events` is an unmapped
  key in 2 of the 4 `unmapped_attributes` diagnostics. No diagnostic code in
  step 4's table names an error, a status or an exception; the codes are
  `orphan_parent` 2, `timestamp_unit_suspect` 4, `unmapped_attributes` 4.
- **Observed in the node table (B7r)** — the line that was *not observable
  from the audit* (whether the two tool nodes carry an error status): step 4
  of both re-audited Z5 reports. Both `tool` nodes have status `error` —
  `225a4ec7cea5d25f` and `b72cc2b1cb801793` (real), `fb78514dc6557db1` and
  `cd8b2a400dc4e7bb` (recorded); both `chain` nodes `ok`; no node carries a
  model. Each `tool` node's record carries one span event, `name`
  `exception`, with attributes `exception.type` `ConnectionError`,
  `exception.message` "connection to https://example.com/status reset by
  peer (attempt 1)" and "(attempt 2)" respectively, `exception.stacktrace`
  and `exception.escaped` `False`, and a `timeUnixNano`; the two `chain`
  nodes' records carry no `events` key (*absent*). Neither `tool` row carries
  a diagnostic code naming an error, a status or an exception: their codes
  are `timestamp_unit_suspect` and `unmapped_attributes`, plus
  `orphan_parent` on the second (S12).
- **Still not observable from the audit:** which nodes the two absent outputs
  belong to, and which nodes the two `<record>.events` diagnostics are on — the
  node table names the diagnostic codes on a node, not the unmapped keys or
  the payloads. The two nodes whose records carry `events` are the two `tool`
  nodes.
- **To establish:** how spanweave renders a span's `exception` events —
  whether they are meant to map to anything other than an unmapped
  `<record>.events` — and whether the two absent outputs are the two failed
  calls. (Whether the status reaches the node is answered above: it does, as
  `error`.)

### S12. `orphan_parent` × 2 on a trace with no root

- **From:** step 4's table in both Z5 reports.
- **Captures and command:** as S11.
- **Observed:** `orphan_parent` × 2 on each graph, beside 4 nodes and 2
  explicit `parent` edges. No root is in either graph (L4).
- **Node table (B7r)** — the line that was *to establish* as "which two
  nodes are orphaned": step 4 of both re-audited Z5 reports. The two nodes
  whose parent is *absent from graph*, and which carry `orphan_parent`, are
  the first `chain` node and the second `tool` node in graph order —
  `ffc7f15f81138f70` (`chain`, `ok`) and `b72cc2b1cb801793` (`tool`, `error`,
  the "attempt 2" exception) real; `0e13631e1bbd0b71` and `cd8b2a400dc4e7bb`
  recorded. The other `tool` and `chain` nodes' parents are present (*yes*);
  no node's parent is *no*.
- **To establish:** whether the two absent parents are the root the process
  exited before exporting, or another unexported span — the node table does
  not give the absent parent's id. The same shape as S2 (Z4's chat spans, parented by a root no
  adapter claims), with a different cause recorded for it: here the root is
  not in the export at all.

### S13. Real and recorded: bodies not byte-identical; graphs of equal size, not byte-identical

- **From:** both Z5 reports, and the captures' bytes beside them. B7-Z5's
  third point of interest, reported as observed.
- **Captures:** `captures/z5/2026-10-13-real`, `captures/z5/2026-10-13-recorded`.
- **Command:** both `zoo audit` commands above, then

  ```bash
  cmp -l captures/z5/2026-10-13-real/raw/0001.body captures/z5/2026-10-13-recorded/raw/0001.body | wc -l
  diff audit/z5-2026-10-13-real.md audit/z5-2026-10-13-recorded.md
  ```

- **Observed:** the B7-Z5 row's premise of identical real and recorded bodies
  does not hold byte for byte: `raw/0001.body` is 5,934 bytes in each capture
  and the two differ in 380 bytes (`cmp -l`); `json/0001.json` is 8,070 bytes
  in each and differs too; their sha256s in the two manifests differ. The
  graphs are not byte-identical either: their trace ids differ
  (`3072629a56dca029bd8c19818bbebbc4` real, `88167a239e683f6a5db73ac739bce4fe`
  recorded, the `trace:` line of `inspect` and the file names). Everything
  else the two reports show is the same: 17,691 bytes per graph (live, batch
  and incremental), the same `inspect` output but for `trace:`, the same
  diagnostic counts and unmapped-key table (1,620 bytes each), and the same
  signature (`chain:-`, `tool:http_get`, `chain:-`, `tool:http_get`). The
  diff of the two reports is the capture path, kind and seal, the `listening`
  ports, the `completed` events' clock readings and the trace id.
- **Node table (B7r):** in the re-audited reports the two graphs' node
  tables differ in the node ids (every span id: `ffc7f15f81138f70`,
  `225a4ec7cea5d25f`, `d6a1ef700699850b`, `b72cc2b1cb801793` real;
  `0e13631e1bbd0b71`, `fb78514dc6557db1`, `4081011c8c1021f9`,
  `cd8b2a400dc4e7bb` recorded) and, in the span events, only in each
  `exception` event's `timeUnixNano`; kinds, statuses, models, parents,
  diagnostic codes and the events' attributes are the same, row for row. The
  diff of the two re-audited reports is otherwise what it was (above, now
  with three `serve` runs' ports and clock readings in step 2).
- **Not observable from the audit:** where else the two graphs differ — the
  audit does not keep the graphs it compares, and its report gives their
  sizes and the node table, not their bytes.
- **To establish:** whether the two graphs differ in anything but the ids
  and timestamps the exporter generated — equal sizes are consistent with
  that and do not show it.

---

## agentgolden

None. Step 5 (`agentgolden.signature.signature(graph)`, no rules) returned
four `llm` steps on each written graph of Z4's, 102 steps on each of Z3's and
4 steps on each of Z5's, and raised on none — again in all six re-audited
reports (B7r). S10's `llm:-` steps were *to establish* as possibly
agentgolden's; the re-audit's node table shows the graph itself carries no
model on those nine nodes, so the signature reads it as it is.
