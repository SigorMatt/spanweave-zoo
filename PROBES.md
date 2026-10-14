# PROBES.md — what the next series of each library starts from

The zoo's audit (`zoo audit`, `SPEC.md` §7) over all six pet projects' twelve
captures, consolidated into the probe list each owning repository's next series
starts from. Series 1 audited Z4; series 2 audited Z3, Z5, Z1, Z2 and Z6 as
their captures landed (B7-Z3, B7-Z5, B7-Z1, B7-Z2, B7-Z6) and re-audited Z4,
Z3 and Z5 once (B7r). At the series' close (B8) **all twelve reports were
written again by one audit** — the zoo's at B6c (`4b57f18`) — and replaced in
place under `audit/`, so every probe below cites one method: the twelve
`audit/<project>-<run-id>.md`. An observation the report does not carry, but
which was read beside the audit with a command given in the probe, is marked
*beside the audit*.

A probe is a reproduction, never a fix (`CLAUDE.md`, standing rule 7): its
captures, a command, what was observed, what the audit expected or what is
still to establish, and the repository that owns it. Nothing below is fixed or
worked around here, and nothing below says how it should be fixed; that
belongs to the owner's series. The owner is named by `SPEC.md` §7.4's table. A
probe marked *to establish* is an observation the audit made and could not
explain from its report; it asserts nothing.

**Pins.** Every observation below was made at
`spanweave@fec7da27af517ad8b58ae3ec57827916aae60674` (0.9.1),
`spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` (0.0.1) and
`agentgolden@aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0), the `audit`
extra's pins, with the stock Collector 0.162.0. Each report's header records
the three shas, pinned and installed. The step-2 policy runs' `--quiet 0` and
`--root-grace 0` are the audit's values, not the receiver's, which documents
no default for either (each report's "Method"; `SPEC.md` §7.3;
`OPEN_QUESTIONS.md` §8). No `--cap`, and no non-zero value of either policy, is
ever run.

**Count.** spanweave-live: 4 (L1–L4). spanweave: 22 (S1–S22). agentgolden: 0.
Findings, per report: Z4 3 (F1 = L1, F2 = S1, F3 = L2), every other project 1
(F1 = L1); 16 across the twelve reports. Every other probe is an observation
and not a finding under §7.4.

## The captures

| Project | Capture | Bodies (records) | Trace | Report |
|---|---|---|---|---|
| Z1 `ledger-clerk` | `captures/z1/2026-10-13-real` | 2 (22, 9) | `40e8f3f6ace0600a1255ec9030397af7` | `audit/z1-2026-10-13-real.md` |
| | `captures/z1/2026-10-13-recorded` | 1 (31) | `a97e57e66afeaad79303a015a945515c` | `audit/z1-2026-10-13-recorded.md` |
| Z2 `fan-out-researcher` | `captures/z2/2026-10-14-real` | 3 (3, 15, 5) | `666cfbfe677c2822ddc8ee532d0903e6` | `audit/z2-2026-10-14-real.md` |
| | `captures/z2/2026-10-14-recorded` | 1 (23) | `4af82ff37ed7031332c5112ccdfcdf39` | `audit/z2-2026-10-14-recorded.md` |
| Z3 `echo-planner` | `captures/z3/2026-10-13-real` | 4 (24, 32, 32, 14) | `7a93d1ee6fc28e193585910fc2ce5906` | `audit/z3-2026-10-13-real.md` |
| | `captures/z3/2026-10-13-recorded` | 1 (102) | `87d538e303fcbd1860df2b8c2fbb58f4` | `audit/z3-2026-10-13-recorded.md` |
| Z4 `streaming-concierge` | `captures/z4/2026-10-12-real` | 2 (3, 2) | `612628c796e094bd26041bf735576133` | `audit/z4-2026-10-12-real.md` |
| | `captures/z4/2026-10-12-recorded` | 1 (5) | `9264505bc6b829dd4330b31460bef36f` | `audit/z4-2026-10-12-recorded.md` |
| Z5 `flaky-fetcher` | `captures/z5/2026-10-13-real` | 1 (4) | `3072629a56dca029bd8c19818bbebbc4` | `audit/z5-2026-10-13-real.md` |
| | `captures/z5/2026-10-13-recorded` | 1 (4) | `88167a239e683f6a5db73ac739bce4fe` | `audit/z5-2026-10-13-recorded.md` |
| Z6 `crew-of-three` | `captures/z6/2026-10-14-real` | 11 (2, 2, 4, 1, 2, 2, 3, 3, 2, 2, 3) | `a5e74188438ca56d4f12f94d2651b49b` | `audit/z6-2026-10-14-real.md` |
| | `captures/z6/2026-10-14-recorded` | 1 (16) | `8766332238a4971b8dc6ffef5b6fb97c` | `audit/z6-2026-10-14-recorded.md` |

One trace per capture. `<N>` below is the capture's body count, `<trace>` its
trace id, as this table gives them.

## Reproducing

From a checkout of this repository:

```bash
uv sync --extra dev --extra audit
for run in captures/z*/*; do
  uv run zoo verify "$run"
  uv run zoo audit "$run" --out "${TMPDIR:-/tmp}"/zoo-audit
done
```

Each audit takes about a second. The reports it writes differ from the
committed ones only in the `listening` port and the clock readings of a
`completed` or `late_arrival` event (`seconds`, and the two in its `detail`;
each report's "Method"). B8 checked it: two runs of all twelve, normalised for
those two things alone, were identical to each other line for line, and the
Z2 and Z6 runs identical to the reports B7-Z2 and B7-Z6 had committed with the
same audit. The re-run found no difference in the audit's method. Against the
reports B7r and B7-Z1 had committed with earlier audits, the twelve differ only
in what the audit changed since: step 4's node table gained B6b's columns (span
name, parent id, unmapped keys, payloads; Z3, Z4, Z5) and B6c's Body and Record
(all four of Z1, Z3, Z4, Z5), and step 2's two policy runs are no longer
replayed `--timing` (B6b). Every `serve` event in step 2 — each `completed`'s
`index` and reason, each `late_arrival`, `written`, `released` and `finished`
— is the same with and without the timed replay.

Each step's own commands, as the reports print them:

```bash
# step 1
uv run spanweave-live serve --port <port> --out graphs --requests <N>
uv run zoo replay <capture> --to http://127.0.0.1:<port> --raw
# step 2: the end-of-input run; then the same with --quiet 0, then with --root-grace 0
uv run spanweave-live serve --port <port> --out graphs --requests <N>
uv run zoo replay <capture> --to http://127.0.0.1:<port> --json
# step 4, on the end-of-input run's graph
uv run spanweave inspect graphs/<trace>.json
```

Step 3 (the in-process re-read and the live / batch / incremental comparison)
and step 5 (`agentgolden.signature.signature(graph)`, no rules) run inside
`zoo audit`. Two commands read the graph beside the audit; the probes name
them as *R* and *G*.

*R* — a `spanweave.Builder` fed the records step 3 feeds, printing per node
its body and record, name, kind, start and end (ns from the root's start),
parent, scope and a few attributes:

```bash
uv run python -c '
import sys; from pathlib import Path; import spanweave; from spanweave_zoo import audit
run = Path(sys.argv[1]); files = sorted(f"json/{p.name}" for p in (run / "json").glob("[0-9][0-9][0-9][0-9].json"))
for part in audit.reread(run, files).partitions:
    b = spanweave.Builder()
    for rec in part.feed: b.feed(rec)
    g = b.graph(); t0 = min(n.started_at for n in g.nodes())
    for n in sorted(g.nodes(), key=lambda n: n.started_at):
        src = n.raw.source; a = src.get("attributes") or {}
        print(n.id, part.origins[n.raw.line_number - 1], n.name, n.kind.value, n.started_at - t0, n.ended_at - t0,
              g.parents(n.id, spanweave.EdgeKind.PARENT), src["scope_spans"]["scope"], a.get("openinference.span.kind"),
              {k: a[k] for k in ("graph.node.id", "graph.node.parent_id", "tool.name") if k in a})
    for e in g.edges():
        if e.kind != spanweave.EdgeKind.PARENT: print(e.kind.value, e.warrant.value, e.basis, e.src, "->", e.dst)
    for d in g.diagnostics: print(d)
' <capture>
```

*G* — the generation graphs `serve --quiet 0` writes, which step 3 compares
with nothing: the `--quiet 0` command of step 2 by hand, then each
`graphs/<trace>.json`, `.2.json`, … read as JSON:

```bash
uv run spanweave-live serve --port <port> --out graphs --quiet 0 --requests <N>
uv run zoo replay <capture> --to http://127.0.0.1:<port> --json
uv run python -c '
import json, sys
d = json.load(open(sys.argv[1])); name = {n["id"]: n["name"] for n in d["nodes"]}
stated = {x["node_id"]: x["source"] for x in d["diagnostics"] if x["code"] == "orphan_parent"}
print(len(d["nodes"]), "nodes;", sum(e["kind"] == "parent" for e in d["edges"]), "parent edges;", len(stated), "orphan_parent")
for e in d["edges"]:
    if e["kind"] == "temporal": print(e["src"], name[e["src"]], stated.get(e["src"]), "->", e["dst"], name[e["dst"]], stated.get(e["dst"]), e["basis"])
' graphs/<trace>.json
```

---

## spanweave-live

### L1. The exporter's own bytes are answered 415

- **From:** finding F1 in every report (step 1).
- **Captures:** all twelve — every `raw/NNNN.body`.
- **Command:** step 1.
- **Observed:** every body answered 415, event `unsupported_media_type`:
  `'application/x-protobuf' is not 'application/json'; this endpoint reads
  OTLP/HTTP JSON and not protobuf`. 29 of 29 bodies: Z4 3 (2 real, 1
  recorded), Z3 5 (4, 1), Z5 2 (1, 1), Z1 3 (2, 1), Z2 4 (3, 1), Z6 12 (11,
  1). The same `json/` bodies, re-encoded by the stock Collector, are all
  answered 200 (step 2).
- **Expected (the audit's):** 2xx — each body is the export as the stock Python
  OTLP/HTTP exporter sent it, unmodified (`zoo verify` passes on every
  capture).

### L2. A record `serve` routed reaches no graph, and no event says where it went

- **From:** finding F3 in both Z4 reports (step 3). Same record as S1.
- **Captures:** `captures/z4/2026-10-12-real` (`json/0002.json` record 2);
  `captures/z4/2026-10-12-recorded` (`json/0001.json` record 5) — Z4's root
  span `concierge.conversation`. The node table has no row for it: its rows
  are the four `llm` nodes, real `json/0001.json` records 1–3 and
  `json/0002.json` record 1, recorded `json/0001.json` records 1–4.
- **Command:** step 2's end-of-input run, without `--deltas`, as the audit runs
  it.
- **Observed:** `finished` reports `routed: 5`; the one graph `serve` wrote
  holds 4 of them. The fifth went to the no-trace builder, which is never
  completed and never written, and no event names it. Under each completion
  policy (step 2 of both reports; observations, no finding by §7.3) no event
  names it either, and each `finished` reports `routed: 5`. Real: `--quiet 0`
  completes the trace twice — generation 1 at `index` 3, written
  `graphs/612628c796e094bd26041bf735576133.json`, then a `late_arrival` at
  `index` 4 and generation 2 at `index` 5, written `….2.json`, released "at
  version 1" — `completed: 2`, `late_arrival: 1`, `written: 2`;
  `--root-grace 0` completes it once, at `index` 5, `the cap policy fired on
  Cap(records=0)` — the end-of-input `Cap(0)`, not `RootEnded`. Recorded (one
  body): `--quiet 0` completes it once at `index` 5 by the quiet policy;
  `--root-grace 0` once at `index` 5 by the end-of-input `Cap(0)`.
- **Beside the audit:** `stderr` is not `serve`'s only output. With `--deltas`
  added to the end-of-input command, `serve` writes 5 delta lines to stdout on
  the real capture, and the fifth (empty `trace_id_after`) carries
  `concierge.conversation`, `unclaimed_record` and `missing_trace_id`
  (spanweave-live's `SPEC.md` §6.3, §8.4). The record is reported there as a
  delta; no event on stderr, and no count in `finished`, names it.
- **Expected (the audit's):** each record of a trace reaches that trace's
  graph, or an event says where it went. At `cddc694`, spanweave-live's
  `SPEC.md` §4.3, §5.4 and §8.5 describe the route the record took; its §1.1
  promises "'no trace id' and a counted event" for a record whose trace id
  cannot be had through the adapter surface, and its §1.5 says every decision
  is "an event with a code", while its §4.3 says the receiver "invents no
  event code" for that record's diagnostics. The tension between §1.1/§1.5
  and §4.3, inside the owner's own spec, is the strongest form of this probe.

### L3. A trace whose root arrives in the last body: one completion at the end of input, one per body under `--quiet 0`, one under `--root-grace 0`

- **From:** steps 2–4 of the Z3, Z1, Z2 and Z6 reports; not a finding under
  §7.4.
- **Captures:** the four real captures with more than one body —
  `captures/z3/2026-10-13-real` (4), `captures/z1/2026-10-13-real` (2),
  `captures/z2/2026-10-14-real` (3), `captures/z6/2026-10-14-real` (11) — and
  their recorded captures (one body each) beside them.
- **Command:** step 2, all three runs; *G* for the generation graphs.
- **Observed — where the root is:** the node table's one row whose parent is
  *no* is, in every capture, the **last record of the last body**: Z3 `Agent
  workflow` (`agent`, `json/0004.json` record 14 real, `json/0001.json` record
  102 recorded); Z1 `LangGraph` (`chain`, `json/0002.json` record 9 / record
  31); Z2 `FunctionAgent.run` (`chain`, `json/0003.json` record 5 / record
  23); Z6 `release-notes.kickoff` (`chain`, `json/0011.json` record 3 /
  record 16). Every other node's parent is present (*yes*), and no
  `orphan_parent` is on the end-of-input graph of any of them.
- **Observed — the end-of-input run:** every body answered 200; one
  `completed`, at the last `index`, `the cap policy fired on Cap(records=0)` —
  the end-of-input `Cap(0)` of `serve --requests N` (the report's Method) —
  then one `written` and one `released`. `routed` equals the records: 102
  (Z3), 31 (Z1), 23 (Z2), 26 (Z6 real) and 16 (Z6 recorded). Live, batch and
  incremental are equal: 1,433,357 bytes (Z3 real), 266,641 / 249,322 (Z1),
  186,168 / 172,483 (Z2), 1,304,658 / 305,886 (Z6).
- **Observed — `--quiet 0`:** one completion **per body**, each `the quiet
  policy fired on Quiet(seconds=0.0)`, each after the first opened by a
  `late_arrival` at the body's first record:
  - Z3 real: at `index` 24, 56, 88 and 102 (generations 1–4: 24, 32, 32, 14
    records), `late_arrival` at 25, 57, 89; four graphs written
    (`graphs/7a93d1ee6fc28e193585910fc2ce5906.json`, `.2.json`, `.3.json`,
    `.4.json`); `finished`: `completed: 4`, `late_arrival: 3`, `written: 4`,
    `released: 4`, `routed: 102`.
  - Z1 real: at `index` 22 and 31, `late_arrival` at 23; `.json` and `.2.json`.
  - Z2 real: at `index` 3, 18 and 23, `late_arrival` at 4 and 19; `.json` to
    `.3.json`.
  - Z6 real: at `index` 2, 4, 8, 9, 11, 13, 16, 19, 21, 23 and 26 (generations
    1–11), `late_arrival` at 3, 5, 9, 10, 12, 14, 17, 20, 22, 24 (generation
    4's one-record body has its `late_arrival` and its `completed` at the same
    `index`, 9); `.json` to `.11.json`.
  - Every generation but the last was completed and written before the body
    carrying the root arrived. Each recorded capture (one body): one
    completion, at its last `index`.
- **Observed — `--root-grace 0`:** one `completed`, at the last `index`, `the
  root_ended policy fired on RootEnded(grace_seconds=0.0)`, generation 1, one
  graph — in all eight captures.
- **Observed beside the audit (*G*) — the generation graphs:** none is the
  end-of-input graph.
  - Z1 real: generation 1 (22 nodes) carries `orphan_parent` × 6 and 16
    `parent` edges — the six nodes whose parent is in the second body:
    `73e3edd2fc491888` `model`, `9833521556552bed` `load_ledger`,
    `b920656c39cb92a4` `RunnableAssign<categories>`, `c8f9b88d62e9a54b`
    `RunnableAssign<rates>`, `898632359c6f7de1` `reconcile`,
    `e0e1f2785bd03602` `ChatPromptTemplate` (the report's node table gives the
    same six: child in `json/0001.json`, parent in `json/0002.json`);
    generation 2 (9 nodes) no `orphan_parent`, 8 `parent` edges, its one
    parentless node the root.
  - Z2 real: generation 1 (3 nodes) `orphan_parent` × 3, no `parent` edge;
    generation 2 (15 nodes) × 10, 5 `parent` edges, and S9's three
    `unpaired_call`; generation 3 (5 nodes, the root among them) none, 4
    `parent` edges. Derived `temporal` edges 2, 9 and 1 (S18).
  - Z6 real: generations 1–10 hold 2, 2, 4, 1, 2, 2, 3, 3, 2 and 2 nodes and
    carry `orphan_parent` × 2, 1, 3, 1, 1, 2, 2, 3, 1 and 2 with 0, 1, 1, 0, 1,
    0, 1, 0, 1 and 0 `parent` edges; generation 11 (the root, `Release Notes
    Reviewer._execute_core` and its last `ChatCompletion`) none and 2.
    `unpaired_call` (S9) spread over generations 1, 3, 4, 6, 7, 8 (2) and 10;
    `temporal` edges 1, 0, 2, 0, 0, 1, 1, 2, 0, 1, 0 (S18).
  - Z3's four generation graphs were not read.
- **To establish:** what a consumer of an early completion is to make of
  generations that hold children without their parents, and what `--quiet S`
  or `--root-grace S` do at values other than `0` — the audit runs neither.

### L4. A trace with no root: completed by `Quiet(0)` under `--quiet 0`; under `--root-grace 0`, by the end-of-input `Cap(0)`, never by `RootEnded`

- **From:** steps 2–4 of both Z5 reports; not a finding under §7.4. Z5 exits
  via `os._exit(0)` with no shutdown (`ZOO-BRIEFS.md`, Z5).
- **Captures:** `captures/z5/2026-10-13-real`, `captures/z5/2026-10-13-recorded`.
- **Command:** step 2, all three runs.
- **Observed:** the one body answered 200 in every run. End of input: one
  `completed`, at `index` 4, `the cap policy fired on Cap(records=0): this
  trace had absorbed 4 records`; one graph per capture holding all 4 records
  (S12: none of them is a root); live, batch and incremental equal (17,691
  bytes each). `--quiet 0`: one `completed`, at `index` 4, `the quiet policy
  fired on Quiet(seconds=0.0)`. `--root-grace 0`: one `completed`, at `index`
  4, `the cap policy fired on Cap(records=0)` — the end-of-input `Cap(0)`; no
  event names `RootEnded`. `finished`: `completed: 1`, `written: 1`, `routed:
  4`, in every run, on each capture. No `llm` node is in either graph, and step
  5 names two `tool:http_get` steps; Z5's brief scripts three `http_get` calls
  and one LLM summary.
- **To establish:** what `serve --cap N` does with this trace, and what
  `--quiet S` and `--root-grace S` do at values other than `0`. Whether
  `RootEnded` ever completes a trace with no root on a receiver whose input
  does not end is not shown: here the input ended at the one request.

---

## spanweave

### S1. Z4's root span is claimed by no adapter

- **From:** finding F2 in both Z4 reports (step 3).
- **Captures:** `captures/z4/2026-10-12-real` (`json/0002.json` record 2);
  `captures/z4/2026-10-12-recorded` (`json/0001.json` record 5) — the root span
  `concierge.conversation`.
- **Command:** step 2's end-of-input run, then
  `spanweave.adapters.classify(record)` on each record
  `spanweave_live.Endpoint` reads from the body (step 3 does exactly this).
- **Observed:** `classify` returned `()` for that record. Building it alone
  raised `AdapterSelectionError` (`adapter_unconfident`: openinference 0.00,
  otel_genai 0.00), batch and incremental alike.
- **Expected (the audit's):** an adapter claims each record of an OTLP export
  `read_records` unpacked, so its trace id can be had through the adapter
  surface.

### S2. `orphan_parent` on every Z4 chat span

- **From:** step 4 of both Z4 reports.
- **Captures:** both Z4 captures.
- **Command:** step 4.
- **Observed:** `orphan_parent` × 4 — each of the four `llm` nodes, named `chat
  Qwen/Qwen3-235B-A22B-Instruct-2507` (real) and `chat stub-concierge-1`
  (recorded): `a700993010700621`, `317657789bb0f148`, `a90c8b9b28c8e710`,
  `17eb31438da683f1` (real); `1c22728149a3ec83`, `afa87e72e4b4c576`,
  `30498d48d228299f`, `08800207f04dcccd` (recorded). Each has parent *absent
  from graph* and parent id `—`; status `unset`; inputs and outputs
  `present`; no span events. The one record of each capture that is not a
  node is S1's root.
- **To establish:** whether these four follow from S1 alone — the node table
  gives no id for a parent absent from the graph, so it does not show the four
  absent parents are S1's root span.

### S3. `timestamp_unit_suspect` on every node

- **From:** step 4 of every report.
- **Captures:** all twelve.
- **Command:** step 4.
- **Observed:** on every graph, once per node and on every row of the node
  table: × 4 (Z4, through `otel_genai`), × 102 (Z3), × 4 (Z5), × 31 (Z1), × 23
  (Z2), × 26 and × 16 (Z6 real and recorded), through `openinference` — from
  the stock Collector's OTLP/JSON re-encoding of a stock exporter's export.
  *Beside the audit* (the graph `serve` writes, Z1), the diagnostic's own
  message says what raised it: `started_at (1791915997281317120), ended_at
  (1791915997282008832) exceeds 100000000000, which unix seconds cannot reach;
  the field may be in milliseconds or nanoseconds. Every value is kept exactly
  as reported and nothing is rescaled`.
- **To establish:** whether the suspicion is warranted on this input.

### S4. `unmapped_attributes` on every Z4 span

- **From:** step 4 of both Z4 reports.
- **Captures:** both Z4 captures.
- **Command:** step 4.
- **Observed:** 4 diagnostics on each graph (2,044 bytes real, 2,152 bytes
  recorded, as compact sorted JSON), one per node, each naming
  `<record>.flags`, `<record>.kind`, `<record>.resource_spans`,
  `<record>.scope_spans`, `gen_ai.provider.name`, `gen_ai.response.id`,
  `gen_ai.response.model` and `server.address`; the recorded capture adds
  `server.port`. The node table's Unmapped keys column is the same on all four
  rows of each.
- **To establish:** which of these the `otel_genai` adapter is meant to map.

### S5. `unpaired_call` once per Z4 graph

- **From:** step 4 of both Z4 reports.
- **Captures:** both Z4 captures.
- **Command:** step 4.
- **Observed:** `unpaired_call` × 1 on each graph, on the second `llm` node —
  `317657789bb0f148` (real, `json/0001.json` record 2), `afa87e72e4b4c576`
  (recorded, record 2).
- **To establish:** whether it follows from S1.

### S6. Two instrumentors on one client: Z3 sees each model call twice, nested; Z6 once

- **From:** steps 3–5 of both Z3 and both Z6 reports; not a finding. Both
  projects run two OpenInference instrumentors (their project manifests: Z3
  `openinference-instrumentation-openai-agents==2.5.3` and
  `openinference-instrumentation-openai==0.1.65`; Z6
  `openinference-instrumentation-crewai==1.1.21` and
  `openinference-instrumentation-openai==0.1.65`).
- **Captures:** both Z3 and both Z6 captures.
- **Command:** step 4; *R* for the instrumentation scopes (Z6).
- **Observed — Z3:** 102 nodes on each capture, all from `openinference
  0.1.0`: `agent` 2, `chain` 26, `llm` 50, `tool` 24; `unknown` 0; no record
  unclaimed (`routed` 102 equals the records in the graph). The 50 `llm`
  nodes are **25 `generation` nodes and 25 `ChatCompletion` nodes**, and
  every `ChatCompletion` is the only child of a `generation` (its parent id):
  each model call is seen twice, once per instrumentor, and spanweave relates
  the two by the `parent` edge the records state. Each `generation` is a child
  of a `turn` chain under the `echo-planner` agent; 24 of the 25 turns also
  hold one `tool` node. Step 5 names the 50 as 25 adjacent pairs, all but the
  last followed by one `tool` step. In every body the `ChatCompletion` records
  come first, then the rest (S21).
- **Observed — Z6:** the captures do **not** show a client seen twice. Every
  `llm` node — 14 real, 8 recorded, all named `ChatCompletion` — is from the
  `openinference.instrumentation.openai` scope (0.1.65, *R*); every `chain`,
  `agent` and `tool` node — 12 real, 8 recorded — from
  `openinference.instrumentation.crewai` (1.1.21), which contributes no `llm`
  node. No two `llm` nodes' intervals overlap; the only adjacent `llm` steps in
  step 5's signature are a delegation tool's `ChatCompletion` child followed by
  the delegating agent's next call (S20), with different parents. Every record
  claimed by `openinference`, `unknown` 0.
- **To establish:** whether the `openinference` adapter is meant to say
  anything about two `llm` nodes for one call (Z3), and whether CrewAI's
  instrumentor would emit an `llm` span of its own under another configuration
  (Z6) — the record carries what was exported.

### S7. `unmapped_attributes` on every OpenInference node

- **From:** step 4 of the Z3, Z5, Z1, Z2 and Z6 reports.
- **Captures:** those ten.
- **Command:** step 4.
- **Observed:** one `unmapped_attributes` diagnostic per node on every graph,
  Z4's four `<record>.*` keys (S4) on every node. As compact sorted JSON:
  362,893 and 363,830 bytes (Z3 real, recorded; of a 1,433,357-byte real
  graph), 1,620 each (Z5), 15,462 each (Z1), 12,509 each (Z2), 39,622 and
  17,128 (Z6). The node table's Unmapped keys column puts each key on its
  node. By project:
  - **Z3:** `llm.output_messages.0.message.role` (50),
    `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`
    (48), the indexed `llm.input_messages.<n>.message.{role,content,tool_calls.<m>.tool_call.{id,function.name,function.arguments},tool_call_id}`
    keys up to `<n>` = 49 (at most 35 diagnostics for any one, 36 recorded),
    `llm.invocation_parameters` (34), `llm.system` (32), `llm.finish_reason`
    (25), `tool.description` and `tool.parameters` (24 each),
    `llm.tools.<n>.tool.json_schema` (16 real, 16 and 17 recorded),
    `llm.output_messages.0.message.content` (2), `agent.name` and
    `graph.node.id` (1 each), `<record>.droppedAttributesCount` (18, S8). The
    history-resending loop (Z3's brief) makes each turn's `llm` nodes carry
    every earlier message again, so the indexed keys grow with the turn. The
    two captures' key sets are the same; nine counts differ by one.
  - **Z5:** `metadata` (4), `<record>.events` (2, on the two `tool` nodes,
    S11), `tool.description` (2).
  - **Z1:** `metadata` (31, every node), `llm.input_messages.0.message.role`
    (7), `llm.input_messages.0.message.content` (6), `tool.description` (6),
    `llm.finish_reason`, `llm.input_messages.1.message.{content,role}`,
    `llm.invocation_parameters`, `llm.output_messages.0.message.role`,
    `llm.provider`, `llm.system` (4 each),
    `llm.output_messages.0.message.content` (3),
    `llm.prompt_template.template`, `llm.prompt_template.variables` (2 each,
    the two `unknown` nodes, S14), `llm.tools.0.tool.json_schema` (2), and one
    each of `llm.input_messages.2.message.{role,tool_calls.0.tool_call.{id,function.name,function.arguments}}`,
    `llm.input_messages.3.message.{content,name}` and
    `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`.
    The two captures' tables are the same.
  - **Z2:** `llm.invocation_parameters`, `llm.provider`, `llm.system` (6 each,
    every `llm` node); `llm.tools.0.tool.json_schema` (4, the four
    `astream_chat` nodes); `tool.description`, `tool.parameters` (3 each, the
    three `FunctionTool.acall` nodes); `<record>.events` (2, S17);
    `llm.finish_reason`, `llm.input_messages.{0,1}.message.{content,role}`,
    `llm.output_messages.0.message.role` (2 each, the two inner
    `astream_chat` nodes); and one each of
    `llm.input_messages.2.message.{role,contents.0.message_content.{text,type},tool_calls.{0,1,2}.tool_call.{id,function.name,function.arguments}}`,
    `llm.input_messages.{3,4,5}.message.content`,
    `llm.output_messages.0.message.content`,
    `llm.output_messages.0.message.contents.0.message_content.{text,type}` and
    `llm.output_messages.0.message.tool_calls.{0,1,2}.tool_call.function.arguments`
    (one `llm` node's output naming three calls, S16). No `metadata`. The two
    captures' tables are the same.
  - **Z6:** 74 distinct keys real, 50 recorded, the recorded set a subset of
    the real. `llm.finish_reason`, `llm.input_messages.{0,1}.message.{content,role}`,
    `llm.invocation_parameters`, `llm.output_messages.0.message.role`,
    `llm.system` (every `llm` node); the history keys
    `llm.input_messages.<n>.message.{role,content,name,tool_calls.0.tool_call.{id,function.name,function.arguments}}`,
    growing with each turn of a task as Z3's do, up to `<n>` = 15 real and 7
    recorded; `llm.tools.{0,1,2}.tool.json_schema`; `tool.description`,
    `tool.parameters`, `tool.cache_function`, `tool.current_usage_count`,
    `tool.description_updated`, `tool.result_as_answer` (every `tool` node);
    `crew_id`, `crew_key` (the root and the three `_execute_core` nodes),
    `crew_agents`, `crew_inputs`, `crew_tasks` (the root), `task_id`,
    `task_key`, `graph.node.id` (the three `_execute_core` nodes) and
    `graph.node.parent_id` (two of them, S19). No `metadata`, no
    `<record>.events` (the Span events column is *absent* on every row).
- **To establish:** which of these the `openinference` adapter is meant to map.

### S8. `<record>.droppedAttributesCount` on 18 Z3 nodes: the last nine model calls, both their nodes

- **From:** step 4 of both Z3 reports.
- **Captures:** both Z3 captures.
- **Command:** step 4.
- **Observed:** `<record>.droppedAttributesCount` is an unmapped key on 18
  nodes of each graph, and the node table's Unmapped keys column names them:
  the `generation` node and its `ChatCompletion` child of each of the **last
  nine** pairs (S6) — real, the `generation` nodes `json/0003.json` records
  15, 18, 21, 24, 27, 30 and `json/0004.json` records 4, 7, 10, their
  `ChatCompletion` children `json/0003.json` records 3–8 and `json/0004.json`
  records 1–3; recorded, the same nine pairs (`generation` records 74, 77, …,
  98; `ChatCompletion` records 17–25 of `json/0001.json`). On the same nine
  `ChatCompletion` nodes, and on no other, the outputs are *absent*; on the
  same nine `generation` nodes the model is *absent* (S10). The record carries
  a count of what the SDK dropped; what was dropped is not in the export as
  received. The 599 `Attributes dict is full` lines the operator saw are the
  SDK's stderr and no file under `captures/z3/` holds them.
- **To establish:** whether spanweave should surface a span's dropped-attribute
  count as more than an unmapped key. The exporter's attribute limit is the
  instrumentation's, not any of the three libraries'.

### S9. `unpaired_call`: a requested call and the tool span that served it are never paired

- **From:** step 4 of the Z3, Z1, Z2 and Z6 reports.
- **Captures:** those eight.
- **Command:** step 4; *R* for the diagnostics' messages and sources.
- **Observed:** `unpaired_call` on the `llm` nodes whose output requested a
  tool (their unmapped keys include
  `llm.output_messages.0.message.tool_calls.<n>.tool_call.function.arguments`),
  and no `call_result` edge in any graph:
  - **Z3:** × 48 on each graph, one on each of 48 `llm` nodes — the
    `generation` and the `ChatCompletion` of every pair but the last (24 + 24;
    the last pair, `9ba382d983e377cc` / `abc456bd1503ec60` real,
    `4feb2fa9b583d910` / `181957d46e2096c9` recorded, carries none) — beside 24
    `tool` nodes. Each call is requested by two nodes (S6).
  - **Z1:** × 1, on the first `ChatOpenAI` node (`bc88f958b4e7b638` real,
    `d65c8a757c33a1ea` recorded), parent the `model` chain under the root.
    *Beside the audit:* `call 'chatcmpl-tool-b84a56ef4e875c2d' was requested
    and no span in this input fulfils it; no edge is invented`, source
    `{"call_id": ..., "operation": "categorize"}` (recorded:
    `call_stub_categorize_1`). The graph holds a `tool` node named
    `categorize` (`bf207c306c0f583c` real, `4b292064ede9bc73` recorded), the
    root's grandchild through the `tools` chain, whose unmapped keys are the
    `<record>.*` four, `metadata` and `tool.description`. The five `fx_rate`
    tool nodes are called by a chain, not by an `llm` node, and no diagnostic
    names them.
  - **Z2:** × 3, all on the inner `astream_chat` of the first step
    (`55d6988ab7075459` real, `da618221c331ae9b` recorded; S17). *Beside the
    audit:* sources `{"call_id": ..., "operation": "fetch_policy"}`, ids
    `chatcmpl-tool-98de6bb2557bb32a`, `chatcmpl-tool-bf153eeb0a4ae1db`,
    `chatcmpl-tool-bfa245421393e6da` (real) and `call_fetch_policy_0`, `_1`,
    `_2` (recorded). The three `tool` nodes whose `operation` is
    `fetch_policy` (S16) carry the attribute keys `input.mime_type`,
    `input.value`, `openinference.span.kind`, `output.mime_type`,
    `output.value`, `tool.description`, `tool.name` and `tool.parameters` —
    none a call-id key. The second step's inner `astream_chat` carries the
    three ids again only as history
    (`llm.input_messages.2.message.tool_calls.{0,1,2}.tool_call.id`) and no
    `unpaired_call`.
  - **Z6:** × 8 (real) and × 4 (recorded), one on each `ChatCompletion` that
    requested a tool, beside as many `tool` nodes. *Beside the audit:* the
    sources name `list_commits`, `lint_markdown` (4 real, 2 recorded),
    `delegate_work_to_coworker` (2, 1) and `ask_question_to_coworker` (1,
    real), ids `chatcmpl-tool-…` (real) and `call_<n>_<operation>` (recorded);
    the `tool` nodes' `tool.name` values are `list_commits`, `lint_markdown`,
    `Delegate work to coworker` and `Ask question to coworker` — for the two
    delegation tools not the operation's spelling — and their records carry
    no key containing `id`.
- **Expected (the owner's spec, at `fec7da2`):** spanweave's `SPEC.md` §4.4
  pairs by call id and is "never a fallback to guessing by name or
  proximity"; what was observed is what it states for an unmatched call.
- **To establish:** whether any of the three instrumentations (LangChain,
  LlamaIndex, CrewAI's OpenInference) records a call id on a tool span — these
  records do not, by key name; and for Z3, whether the 48 follow from two
  `llm` nodes per call (S6).

### S10. Nine Z3 `llm` steps carry no model

- **From:** steps 4 and 5 of both Z3 reports.
- **Captures:** both Z3 captures.
- **Command:** step 4; step 5 inside `zoo audit`.
- **Observed:** of the 50 `llm` steps, 41 carry the model
  (`llm:Qwen/Qwen3-235B-A22B-Instruct-2507` real, `llm:echo-planner-stub`
  recorded) and 9 carry `llm:-`. The node table shows the `model` key absent
  from the graph on exactly 9 `llm` nodes, position for position the `llm:-`
  steps: the `generation` node of each of the last nine pairs (e.g.
  `c6bc024ad4607d9a`, real, `json/0003.json` record 15); their
  `ChatCompletion` children carry the model. The nine carry
  `<record>.droppedAttributesCount` (S8), and among their unmapped keys none
  names a model; `llm.system`, on 32 of the 41 `llm` nodes with a model, is on
  none of the nine, `llm.invocation_parameters` on one. The signature reads the
  graph as it is and raised on neither.
- **To establish:** whether the model is among the attributes the SDK dropped
  on those nine spans — the record carries the count, not the names.

### S11. Two failed `http_get` tool calls: status `error`, outputs absent, their `exception` events an unmapped key

- **From:** steps 4 and 5 of both Z5 reports; not a finding. Z5's brief
  scripts the first two `http_get` calls to raise a `ConnectionError`.
- **Captures:** both Z5 captures.
- **Command:** step 4.
- **Observed:** both `tool` nodes, `http_get` — `225a4ec7cea5d25f`
  (`json/0001.json` record 1) and `b72cc2b1cb801793` (record 4) real,
  `fb78514dc6557db1` and `cd8b2a400dc4e7bb` recorded — have status `error`,
  inputs `present` and outputs **absent**: the two absent outputs `inspect`
  counts are theirs. Both `chain` nodes (`fetch`, `retry_or_summarize`) are
  `ok`, with outputs present; no node carries a model. Each `tool` node's
  record carries one span event, `name` `exception`, with `exception.type`
  `ConnectionError`, `exception.message` "connection to
  https://example.com/status reset by peer (attempt 1)" and "(attempt 2)",
  `exception.stacktrace`, `exception.escaped` `False` and a `timeUnixNano`;
  the two `<record>.events` unmapped keys are on those two nodes. No
  diagnostic code names an error, a status or an exception; the codes are
  `orphan_parent` 2, `timestamp_unit_suspect` 4, `unmapped_attributes` 4.
  Step 5 names both `tool:http_get`.
- **To establish:** how spanweave renders a span's `exception` events —
  whether they are meant to map to anything other than an unmapped
  `<record>.events` (S17 has the same key for a non-error event).

### S12. `orphan_parent` × 2 on Z5's rootless trace

- **From:** step 4 of both Z5 reports.
- **Captures:** both Z5 captures.
- **Command:** step 4.
- **Observed:** 4 nodes, 2 explicit `parent` edges, `orphan_parent` × 2 on
  each graph. The two nodes whose parent is *absent from graph* (parent id
  `—`) are the last two records of the one body: `fetch` (`chain`, `ok`,
  record 3; `ffc7f15f81138f70` real, `0e13631e1bbd0b71` recorded) and the
  second `http_get` (`tool`, `error`, the "attempt 2" exception, record 4;
  `b72cc2b1cb801793`, `cd8b2a400dc4e7bb`). The first `http_get` and
  `retry_or_summarize` are children of `fetch` (records 1 and 2). No node's
  parent is *no*: no root is in either graph (L4).
- **To establish:** whether the two absent parents are the root the process
  exited before exporting, or another unexported span — the node table gives no
  id for a parent absent from the graph. The same shape as S2, with a
  different cause recorded for it: here the root is not in the export at all.

### S13. Z5's real and recorded: bodies not byte-identical; graphs of equal size, not byte-identical

- **From:** both Z5 reports, and the captures' bytes beside them.
- **Captures:** both Z5 captures.
- **Command:** both audits, then

  ```bash
  cmp -l captures/z5/2026-10-13-real/raw/0001.body captures/z5/2026-10-13-recorded/raw/0001.body | wc -l
  diff audit/z5-2026-10-13-real.md audit/z5-2026-10-13-recorded.md
  ```

- **Observed:** `raw/0001.body` is 5,934 bytes in each capture and the two
  differ in 380 bytes; `json/0001.json` is 8,070 bytes in each and differs too;
  their sha256s differ. The two graphs are 17,691 bytes each (live, batch and
  incremental) and differ at least in the trace id. The diff of the two
  reports is the capture path, kind and seal, the `listening` ports, the clock
  readings, the trace id, the node table's node and parent ids (the span ids)
  and each `exception` event's `timeUnixNano`; bodies, records, span names, kinds,
  statuses, payloads, diagnostics, unmapped keys, the unmapped-key table (1,620
  bytes each) and the signature (`chain:-`, `tool:http_get`, `chain:-`,
  `tool:http_get`) are the same, row for row.
- **To establish:** whether the two graphs differ in anything but the ids and
  timestamps the exporter generated — the audit does not keep the graphs it
  compares, and its report gives their sizes, not their bytes.

### S14. `openinference.span.kind = PROMPT` becomes an `unknown` node

- **From:** step 4 of both Z1 reports.
- **Captures:** both Z1 captures.
- **Command:** step 4.
- **Observed:** `unknown: 2` in `inspect`'s node counts and
  `unknown_span_kind` × 2 on each graph; the report's `unknown` nodes:
  `ChatPromptTemplate` × 2 — `df4e7bd70f4edf20` (`json/0001.json` record 5,
  child of the `RunnableSequence` under `RunnableParallel<categories>`) and
  `e0e1f2785bd03602` (`json/0001.json` record 22, the last record of the first
  body, child of the `summarize` chain) real; `03003a0f0472b46a` (record 5) and
  `ce2ca6162ca67c60` (record 22) recorded. Status `ok`, model absent, inputs
  and outputs `present`, unmapped keys including
  `llm.prompt_template.template` and `llm.prompt_template.variables`. *Beside
  the audit:* the diagnostic's message is `openinference.span.kind='PROMPT'
  does not map to a NodeKind; kept as unknown, with the reported kind
  preserved in attributes`. Nothing was dropped.
- **To establish:** whether `PROMPT` is a kind the `openinference` adapter is
  meant to map.

### S15. Every child's record before its parent's, in every capture

- **From:** step 4's Body and Record columns, all twelve reports; Z1's brief
  ("nesting depth and parent-before-child ordering in a real exporter's
  batches"). Not a finding.
- **Captures:** all twelve.
- **Command:** step 4.
- **Observed — ordering:** for every `parent` edge in every graph, the child's
  record precedes its parent's (body first, then record): Z1 30 of 30, Z2 22
  of 22, Z3 101 of 101, Z5 2 of 2, Z6 25 of 25 and 15 of 15; Z4's graphs have
  no `parent` edge (S2). Parent-before-child holds for none. Within one body
  and across bodies alike: of the real captures' edges, Z1 24 within a body
  and 6 from body 1 to body 2; Z2 9 within and 13 across (1 from body 1 to 2,
  2 from 1 to 3, 10 from 2 to 3); Z3 79 within and 22 into body 4; Z6 7
  within and 18 across, 16 of them into body 11. The root is the last record
  of the last body (L3). Z1's first body ends inside the `summarize` subtree:
  `ChatPromptTemplate` is `json/0001.json` record 22, and `ChatOpenAI`,
  `StrOutputParser` and `summarize` are `json/0002.json` records 1–3.
- **Observed — Z1's depth:** 31 nodes, 30 `parent` edges, no
  `orphan_parent`. The longest root-to-leaf path is 8 `parent` edges (9
  levels), to each of the five `fx_rate` `tool` nodes: `LangGraph` → `tools`
  (chain) → `categorize` (tool) → `categorize` (chain) →
  `RunnableAssign<rates>` → `RunnableParallel<rates>` → `lookup_rate` →
  `_fetch_rates` → `fx_rate` (`6c17e931ae4a5989`, `de9709a4a4be62f2`,
  `64171e698a5f787d`, `c27097b50658e7c6`, `e7cde30149b4895b` real,
  `json/0001.json` records 12–16), status `ok`, inputs and outputs `present`.
  The deepest `llm` node is the `ChatOpenAI` under `RunnableSequence`, depth 7.
  `summarize` is a **`chain`** node (`fb5a00c15fff11d1` real,
  `f0106dfcaca83836` recorded), depth 4, child of the `categorize` chain and
  sibling of `RunnableAssign<rates>`; its children are `ChatPromptTemplate`
  (S14), `ChatOpenAI` (`llm`, `04704daf4e5e5376` real / `eddf6a6b5613c8b0`
  recorded) and `StrOutputParser` — not on the path from `fx_rate` back to the
  root. The recorded node table is the real one's row for row but for node
  ids, bodies and records, and the model (`ledger-clerk-stub`).
- **To establish:** nothing for spanweave: at end of input it rebuilt every
  `parent` edge from child-first records, and incremental equals batch. What a
  consumer that completes early sees of this order is L3's.

### S16. Z2's fan-out: three `FunctionTool.acall` nodes start in one order and end in another; spanweave orders their parents by start

- **From:** step 4 of both Z2 reports, and the nodes' times and edges read
  beside the audit (*R*). Not a finding.
- **Captures:** both Z2 captures.
- **Command:** step 4; *R* for times and the derived edges.
- **Observed — shape:** the three `FunctionTool.acall` nodes are **not
  siblings**. Each is the only child of its own `BaseWorkflowAgent.call_tool`
  `chain` node; the three `call_tool` nodes are the siblings, children of the
  root `FunctionAgent.run`, beside the `run_agent_step`, `parse_agent_output`,
  `aggregate_tool_results` and `setup_agent` chains. The three `tool` nodes'
  `operation` is `fetch_policy`; step 5 names three `tool:fetch_policy` steps.
- **Observed — record order (the report):** real, the `acall` nodes are
  `json/0002.json` records 11 (`2f42891bc379dbb4`), 5 (`1d1e1964ed3f7c4e`) and
  8 (`20788a74b1c43ece`), each followed directly by its `call_tool`'s record
  (12, 6, 9); recorded, records 14, 8 and 11 of `json/0001.json`, likewise.
- **Observed — start and end order (*R*):** real, by start `2f42891bc379dbb4`
  (15.057 s), `1d1e1964ed3f7c4e` (15.060 s), `20788a74b1c43ece` (15.062 s); by
  end `1d1e1964ed3f7c4e` (15.162 s), `20788a74b1c43ece` (15.264 s),
  `2f42891bc379dbb4` (15.360 s) — the first started is the last to end. The
  records are in end order, all 23 of them, in both captures. Each
  `call_tool` ends after its own `acall`, by 0.385, 0.289 and 0.281 ms (real;
  0.323, 0.335 and 0.501 ms recorded). The root ends last of all 23 spans
  (20.941 s real, 1.140 s recorded). The first step's `run_agent_step` ends
  (15.053 s real) before any `acall` starts; it is not their parent.
- **Observed — how spanweave orders them:** 14 derived `temporal` edges per
  graph, every one `sibling start_time ordering`, each between two children of
  one parent (spanweave's `SPEC.md` §4.3). None touches an `acall` node (each
  has no sibling). Among the root's children the chain runs
  `parse_agent_output` → `call_tool` (`0b76f56ee6e637fb`, parent of the
  first-started `acall`) → `call_tool` (`6610971780590a14`) → `call_tool`
  (`00889eb3593de58c`) → `aggregate_tool_results` × 3 → `setup_agent` →
  `run_agent_step` → `parse_agent_output` (real; recorded the same by name):
  start order, not end order and not record order. The edge
  `00889eb3593de58c` → `a6dd7bd6e5d950e6` (`aggregate_tool_results`) joins a
  `call_tool` still running when the `aggregate_tool_results` started — an
  order, not a precedence, as §4.3 says.
- **To establish:** nothing for spanweave from the order alone. Whether the
  three tool nodes could be paired with their calls is S9's.

### S17. Two `astream_chat` `llm` nodes per Z2 agent step, one nested in the other, and a third `llm` node beside them

- **From:** steps 4 and 5 of both Z2 reports, and times read beside the audit
  (*R*). Not a finding.
- **Captures:** both Z2 captures.
- **Command:** step 4; *R*.
- **Observed:** 6 `llm` nodes per graph, 3 under each of the two
  `BaseWorkflowAgent.run_agent_step` chains:
  `OpenAILike._prepare_chat_with_tools` and `OpenAILike.astream_chat` (the
  **outer**), siblings joined by one `temporal` edge; and a second
  `OpenAILike.astream_chat` (the **inner**), the outer's only child. All six
  carry the model (`Qwen/Qwen3-235B-A22B-Instruct-2507` real, `stub-model`
  recorded), status `ok`; step 5 names three consecutive `llm` steps per agent
  step. The inner's record precedes the outer's (real `json/0002.json` records
  1 and 2).
  - Outer (`da6c5422d132ace1`, `659be38850f33552` real): outputs `absent`, no
    span events, unmapped keys the three `llm.*` of every `llm` node and
    `llm.tools.0.tool.json_schema`.
  - Inner (`55d6988ab7075459`, `db1c06636eb889b0` real; `da618221c331ae9b`,
    `72dca99b6ea6d9b6` recorded): outputs `present`, the input and output
    message keys (S7), `<record>.events` — one span event each, `First Token
    Stream Event` — and, on the first step's, the three `unpaired_call` (S9).
  - *R:* real, the first step's inner spans 0.214–0.266 s and its
    `run_agent_step` 0.209–15.053 s; the second's 15.369–15.370 s within
    15.366–20.936 s. Each inner node's `First Token Stream Event`
    `timeUnixNano` falls **after** that span's own end: 6.887 s (real, step 1;
    ended 0.266 s) and 15.855 s (step 2; ended 15.370 s); recorded 0.805 s
    (ended 0.254 s) and 1.130 s (ended 1.124 s). spanweave keeps the event as
    the record carries it.
- **To establish:** whether the span intervals the instrumentation reports for
  a stream cover the stream at all — the timestamps are the exporter's, and
  spanweave neither checks nor rescales them; and whether an `llm` node
  wrapping another `llm` node of the same call is a shape the `openinference`
  adapter is meant to say anything about (Z3's pairs, S6, are another).

### S18. A partial graph orders orphans whose stated parents differ

- **From:** the generation graphs `serve --quiet 0` writes for the real Z2 and
  Z6 captures, read beside the audit (*G*; L3). Step 3 compares the
  end-of-input graph only, so no report shows it.
- **Captures:** `captures/z2/2026-10-14-real`, `captures/z6/2026-10-14-real`.
- **Command:** *G*.
- **Observed — Z2:** generation 1 (3 nodes, no `parent` edge, `orphan_parent`
  × 3) has two `temporal` edges, basis `sibling start_time ordering`:
  `c53d458dde4e4a12` `init_run` → `315ed06c6c80d472` `setup_agent` (both
  stating parent `86a464c4b18af821`, the root), and `315ed06c6c80d472`
  `setup_agent` → `013c6a9b437679a2` `_prepare_chat_with_tools`, whose record
  states parent `539a254a824d5e2a` (`run_agent_step`, not in that input).
  Generation 2 (15 nodes, `orphan_parent` × 10) has 9; one of them,
  `c617d3f115e8801c` `setup_agent` (stating the root) → `716ca47344fbdff2`
  `_prepare_chat_with_tools` (stating `727933145969a7fe`, the second
  `run_agent_step`), again joins nodes whose stated parents differ; the other 8
  join nodes that both state the root.
- **Observed — Z6:** one of the 8 `temporal` edges across the eleven
  generations joins orphans whose stated parents differ — generation 3's
  `0cc839c55998fd72` `Release Notes Writer._execute_core` (stating
  `34c04caf3b53b381`, the root) → `89e56db8cdd3d86d` `ChatCompletion` (stating
  `961eb676dd44c052`, the Reviewer's `_execute_core`). The other 7 join nodes
  that state the same parent.
- **Observed — end of input:** no such edge in either end-of-input graph: there
  each node is ordered only against its own siblings.
- **Expected (the owner's spec, at `fec7da2`):** spanweave's `SPEC.md` §4.3 —
  "nodes with no parent are siblings of each other at trace root". The
  observation agrees with it if a node whose stated parent is absent counts as
  having no parent.
- **To establish:** whether it does — whether `orphan_parent` nodes with
  different stated parents are meant to form one sibling group — and what a
  consumer of an early completion (L3) is to make of an order the complete
  graph does not assert. Z1's and Z3's generation graphs were not read for it.

### S19. Z6's nesting: one `agent` node per task, under the crew's `chain`; the records' `graph.node.parent_id` names the previous agent

- **From:** step 4 of both Z6 reports, and the records read beside the audit
  (*R*). Not a finding.
- **Captures:** both Z6 captures.
- **Command:** step 4; *R*.
- **Observed — shape:** the root is `release-notes.kickoff`, a `chain` node
  (`34c04caf3b53b381` real, `4f7e2c35179f73b8` recorded). Its only children
  are three `agent` nodes named `<agent role>._execute_core` — `Commit
  Collector`, `Release Notes Writer`, `Release Notes Reviewer` — siblings
  ordered by two `temporal` edges in that order. Each is **one** span per task
  (*R*: `openinference.span.kind` `AGENT`, with `task_id`, `task_key`,
  `crew_id`, `crew_key` and `graph.node.id`, the agent's role); no separate
  task span or agent span is in either capture — two levels, not three. Under
  each, the `llm` and `tool` nodes of that task. The deepest path is 3 `parent`
  edges: root → the Reviewer's `_execute_core` → a delegation `tool` node →
  its `ChatCompletion` (S20). The kickoff's inputs are *absent* (its record has
  no `input.value`), its outputs `present`.
- **Observed — two statements of structure (*R*):** the Writer's and the
  Reviewer's records carry `graph.node.parent_id` naming the **previous agent**
  (`Commit Collector`, `Release Notes Writer`) — the crew's sequential order —
  while their span parent is the kickoff. The Commit Collector's carries none.
  spanweave builds the `parent` edges from the spans' parent ids and leaves
  `graph.node.id` and `graph.node.parent_id` unmapped (S7); the sequence they
  state appears in the graph only as the `temporal` edges between the three
  siblings, derived from start times.
- **Observed — intervals (*R*):** real, the three tasks run 0.052–2.806 s,
  2.814–7.309 s and 7.331–48.277 s inside the root's 0–48.300 s (recorded
  0.052–0.543, 0.552–0.574, 0.594–0.812 inside 0–0.825 s).
- **To establish:** whether the `openinference` adapter is meant to map
  OpenInference's `graph.node.id` / `graph.node.parent_id`, and what it would
  do where they state a relation other than the span parent.

### S20. Z6's delegation is a `tool` node with the coworker's `ChatCompletion` as its only child; no `agent` node for the coworker

- **From:** steps 4 and 5 of both Z6 reports, and the records read beside the
  audit (*R*; for the persona, each `ChatCompletion` record's
  `llm.input_messages.0.message.content`, of which only the opening words were
  read). Not a finding.
- **Captures:** both Z6 captures.
- **Command:** step 4; *R*.
- **Observed:** the delegation spans are `tool` nodes, children of the
  Reviewer's `_execute_core`: real, `Delegate work to coworker.run` × 2
  (`853c794192f0bb63`, `a20b4dfd274d45e2`) and `Ask question to coworker.run`
  × 1 (`ca55b967aa976a9b`); recorded, `Delegate work to coworker.run` × 1
  (`449398542054a6e1`). Each has exactly one child, a `ChatCompletion` `llm`
  node (`05fee439adbecf19`, `344735450e29f7e9`, `b9bffcf46a373332` real;
  `d713a1c08b316e89` recorded) whose system message opens "You are Release
  Notes Writer." — the coworker's persona — while every other
  `ChatCompletion` under the Reviewer's task opens "You are Release Notes
  Reviewer." No `agent` node stands for the coworker's work. Its interval lies
  inside the tool's (real: 16.327–19.482 s in 16.313–19.494 s; 27.367–29.720 in
  27.354–29.732; 34.956–39.868 in 34.945–39.879). None of the three carries an
  `unpaired_call`; the delegating `ChatCompletion` before each tool does (S9).
  Step 5 names `tool:Delegate work to coworker` and `tool:Ask question to
  coworker`, each followed by the coworker's `llm` step.
- **To establish:** whether a consumer can tell the coworker's model call from
  the delegator's other than by its parent being a delegation tool — the graph
  carries no agent identity on an `llm` node (its normalized attributes are
  `model` alone).

### S21. Records in a body are grouped by instrumentation scope, not in end order

- **From:** step 4's Body and Record columns, the Z3 and Z6 reports — the two
  projects with two instrumentors (S6); end times and scopes read beside the
  audit (*R*, Z6). Not a finding.
- **Captures:** both Z3 and both Z6 captures.
- **Command:** step 4; *R*.
- **Observed:** in every body that holds records of both scopes, the OpenAI
  instrumentor's `ChatCompletion` records come first and the other
  instrumentor's after them. Z3: in each of the four real bodies the first 6,
  8, 8 and 3 records are the body's `ChatCompletion`s, the rest after them; in
  the recorded body records 1–25 are the 25 `ChatCompletion`s and records
  26–102 the rest, the root last. Z6: recorded, records 1–8 are the eight
  `ChatCompletion`s, records 9–16 the eight `crewai` spans, the root last.
  *R* (Z6 real): within a scope the records are in the order the spans ended,
  so a `crewai` span that ended before an `openai` span of the same body still
  comes later — `json/0003.json` records 1–4 are `ChatCompletion` (the
  Writer's, ended 7.296 s), `ChatCompletion` (the Reviewer's, 11.463 s),
  `Release Notes Writer._execute_core` (7.309 s), `lint_markdown.run` (11.466
  s); `json/0008.json` records 1–3 are `ChatCompletion` (32.794 s),
  `ChatCompletion` (34.943 s), `lint_markdown.run` (32.797 s).
- **To establish:** nothing for spanweave: it rebuilt every `parent` edge and
  incremental equals batch (S15). Records reach a receiver in the exporter's
  order, not the spans' (L3).

### S22. Z6's real and recorded: two shapes of one crew

- **From:** both Z6 reports, side by side. That the real run did not follow its
  script is the capture's own fact (`TASKS.md`, series 2's decisions log,
  2026-10-14, "captures"; the contract allows randomness in the real run), not
  a defect of anything audited.
- **Captures:** both Z6 captures.
- **Command:** both audits.
- **Observed — the same:** the root and its three `_execute_core` children in
  the same order; the Commit Collector's task as `ChatCompletion`,
  `list_commits.run`, `ChatCompletion`; the Writer's as one `ChatCompletion`;
  every node status `ok`; every record claimed by `openinference`; the same
  diagnostic codes (S3, S7, S9), no `unknown` node, no `orphan_parent` at end
  of input; the `list_commits.run` node's inputs `empty` (its `input.value` is
  `{}`) — the only `empty` payload state in any zoo report — and the root's
  inputs *absent*.
- **Observed — the departure (the Reviewer's task):** recorded, 7 children in
  start order — `ChatCompletion`, `lint_markdown.run`, `ChatCompletion`,
  `Delegate work to coworker.run` (with the Writer's `ChatCompletion`),
  `ChatCompletion`, `lint_markdown.run`, `ChatCompletion` — two lint passes and
  one send-back, as Z6's brief scripts. Real, 15 children — four lint passes,
  two delegations and one question (`Ask question to coworker.run`). Totals:
  26 nodes (`agent` 3, `chain` 1, `llm` 14, `tool` 8), 25 `parent` and 18
  `temporal` edges, 60 diagnostics, 26 signature steps real; 16 nodes (3, 1, 8,
  4), 15 and 10, 36, 16 steps recorded. Real ran 48.3 s in 11 bodies; recorded
  0.825 s in 1. By span name the recorded Reviewer's seven children are the
  real one's first seven; where the recorded run approves after its first
  send-back, the real one goes on.
- **To establish:** nothing for any of the three libraries: both shapes were
  read without a finding beyond L1, and each is what its run exported.

---

## agentgolden

None. Step 5 (`agentgolden.signature.signature(graph)`, no rules) ran on every
written graph of the twelve captures and raised on none: 4 steps on each of
Z4's, 102 on each of Z3's, 4 on each of Z5's, 31 on each of Z1's, 23 on each of
Z2's, and 26 (real) and 16 (recorded) on Z6's. S10's `llm:-` steps were once
*to establish* as possibly agentgolden's; the node table shows the graph itself
carries no model on those nine nodes, so the signature reads it as it is.
