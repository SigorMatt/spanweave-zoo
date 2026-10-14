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
marked *(B7r)*. B7-Z1 adds Z1's, written by the audit as B6b left it
(`390eb24`: step 4's node table also names each node's span, its parent id,
its unmapped keys and its payload state): `audit/z1-2026-10-13-real.md` and
`audit/z1-2026-10-13-recorded.md`; observations from them are marked
*(B7-Z1)*. B7-Z2 adds Z2's, written by the audit as B6c left it (`4b57f18`:
the node table also names the body and the record each node came from):
`audit/z2-2026-10-14-real.md` and `audit/z2-2026-10-14-recorded.md`;
observations from them are marked *(B7-Z2)*. B7-Z6 adds Z6's, written by the
same audit (`4b57f18`): `audit/z6-2026-10-14-real.md` and
`audit/z6-2026-10-14-recorded.md`; observations from them are marked
*(B7-Z6)*. This file consolidates them into the probe list each owning
repository's next series starts from.

A probe is a reproduction, never a fix (`CLAUDE.md`, standing rule 7): a
capture, a command, what was observed, what the audit expected, and the
repository that owns it. Nothing below is fixed or worked around here, and
nothing below says how it should be fixed; that belongs to the owner's series.
The owner is named by `SPEC.md` §7.4's table.

**Pins.** Every observation below was made at `spanweave@fec7da27af517ad8b58ae3ec57827916aae60674`
(0.9.1), `spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` (0.0.1) and
`agentgolden@aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0), the `audit`
extra's pins, with the stock Collector 0.162.0 — Z4's, Z3's, Z5's, Z1's, Z2's
and Z6's alike (each report's header records the three shas, pinned and installed).
The six Z4, Z3 and Z5 reports were all written by one audit, the zoo's at B6a
(`07285bd`), re-run by B7r with the pins unchanged; Z1's two by the zoo's at
B6b (`390eb24`), the pins unchanged, so their node table has B6b's columns
and the other six keep B6a's (`SPEC.md` §7.5) until B8 audits them again;
Z2's and Z6's four by the zoo's at B6c (`4b57f18`), the pins unchanged, so
theirs also has B6c's Body and Record columns; the step-2 policy runs' `--quiet 0` and
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
uv run zoo verify captures/z1/2026-10-13-real
uv run zoo verify captures/z1/2026-10-13-recorded
uv run zoo audit captures/z1/2026-10-13-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z1/2026-10-13-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo verify captures/z2/2026-10-14-real
uv run zoo verify captures/z2/2026-10-14-recorded
uv run zoo audit captures/z2/2026-10-14-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z2/2026-10-14-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo verify captures/z6/2026-10-14-real
uv run zoo verify captures/z6/2026-10-14-recorded
uv run zoo audit captures/z6/2026-10-14-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z6/2026-10-14-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
```

The reports it writes differ from the committed ones only in the `listening`
port and the clock readings in a `completed` or `late_arrival` event (each
report's "Method"). B7r checked it: a second run of all six audits, normalised
for those two things alone, was identical to the committed reports line for
line, so no difference in the audit's method was found. Z3's `real` audit took
about 23 s at B6a (its two timed replays slept the captured gaps); the others
about a second. Run at a later audit, the six differ in what that audit
changed as well: from B6b on, step 4's node table has B6b's columns and no
replay is `--timing`. B7-Z1 checked Z1's two the same way: a second run,
normalised for the `listening` ports and the `completed` and `late_arrival`
events, was identical to the committed reports; each takes about a second.
B7-Z2 checked Z2's two the same way, with the same result; from B6c on, step
4's node table also has the Body and Record columns. B7-Z6 checked Z6's two
the same way, with the same result.
Each probe also gives the step's own commands, as the reports print them.

**Count.** spanweave-live: 4 (L1–L2 from Z4, L1 seen again in Z3, Z5, Z1, Z2
and Z6; L3 from Z3, seen again in Z1, Z2 and Z6; L4 from Z5). spanweave: 22
(S1–S5 from Z4, S3 seen again in Z3, Z5, Z1, Z2 and Z6; S6–S10 from Z3, S6
seen again in Z6, S7 seen again in Z5, Z1, Z2 and Z6, S9 seen again in Z1, Z2
and Z6; S11–S13 from Z5; S14–S15 from Z1; S16–S18 from Z2, S18 seen again in
Z6; S19–S22 from Z6). agentgolden: 0 (step 5's `signature` ran clean on every
written graph of all twelve captures). B7-Z1 added two probes (S14, S15) and
one finding per Z1 report (L1's); B7-Z2 added three (S16–S18) and one finding
per Z2 report (L1's); B7-Z6 added four (S19–S22) and one finding per Z6 report
(L1's).
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
- **Seen again in Z1** (B7-Z1, finding F1 in both Z1 reports):
  `captures/z1/2026-10-13-real` (`raw/0001.body`, `raw/0002.body`,
  `--requests 2`) and `captures/z1/2026-10-13-recorded` (`raw/0001.body`,
  `--requests 1`), the same commands with `z1/2026-10-13-*`. Every body
  answered 415, the same event and detail: 3 of 3 bodies across the two
  captures.
- **Seen again in Z2** (B7-Z2, finding F1 in both Z2 reports):
  `captures/z2/2026-10-14-real` (`raw/0001.body`–`raw/0003.body`,
  `--requests 3`) and `captures/z2/2026-10-14-recorded` (`raw/0001.body`,
  `--requests 1`), the same commands with `z2/2026-10-14-*`. Every body
  answered 415, the same event and detail: 4 of 4 bodies across the two
  captures.
- **Seen again in Z6** (B7-Z6, finding F1 in both Z6 reports):
  `captures/z6/2026-10-14-real` (`raw/0001.body`–`raw/0011.body`,
  `--requests 11`) and `captures/z6/2026-10-14-recorded` (`raw/0001.body`,
  `--requests 1`), the same commands with `z6/2026-10-14-*`. Every body
  answered 415, the same event and detail: 12 of 12 bodies across the two
  captures.

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
- **Seen again in Z1** (B7-Z1, step 2 of both Z1 reports): the root's
  record in the last of **two** bodies (S15 says how that was read). Real,
  2 bodies (22 and 9 records), all answered 200: the end-of-input run
  completes once, at `index` 31, by `Cap(records=0)`; `--quiet 0` completes
  twice — at `index` 22 (generation 1, 22 records, before the body carrying
  the root arrived) and, after a `late_arrival` at `index` 23, at `index` 31
  (generation 2, 9 records), writing
  `graphs/40e8f3f6ace0600a1255ec9030397af7.json` and `.2.json`; `--root-grace
  0` completes once, at `index` 31, by `RootEnded(grace_seconds=0.0)`.
  `finished` reports `routed: 31` in each run. Recorded, 1 body of 31 records:
  one completion at `index` 31 under each of the three. Live, batch and
  incremental equal on both (266,641 bytes real, 249,322 recorded).
  - **Not in the report, observed beside it (B7-Z1):** the two generation
    graphs `--quiet 0` writes, which step 3 compares with nothing. Replayed
    by hand into `serve --port 0 --out graphs --quiet 0 --requests 2`, then
    `spanweave inspect` on each: generation 1 (22 nodes) carries
    `orphan_parent` × 6 and 16 explicit `parent` edges — the six nodes whose
    parent is in the second body (`73e3edd2fc491888` `model`,
    `9833521556552bed` `load_ledger`, `b920656c39cb92a4`
    `RunnableAssign<categories>`, `c8f9b88d62e9a54b` `RunnableAssign<rates>`,
    `898632359c6f7de1` `reconcile`, `e0e1f2785bd03602`
    `ChatPromptTemplate`); generation 2 (9 nodes) carries no `orphan_parent`
    and 8 explicit `parent` edges, its one parentless node the root
    `bd08a2148df084bc` `LangGraph`. Neither generation's graph is the
    end-of-input graph (31 nodes, 30 `parent` edges, no `orphan_parent`).
- **Seen again in Z2** (B7-Z2, step 2 of both Z2 reports): the root's record
  (`FunctionAgent.run`) is the last record of the last of **three** bodies —
  `json/0003.json` record 5, the node table's Body and Record columns (B6c).
  Real, 3 bodies (3, 15 and 5 records), all answered 200: the end-of-input
  run completes once, at `index` 23, by `Cap(records=0)`; `--quiet 0`
  completes three times — at `index` 3 (generation 1, 3 records), after a
  `late_arrival` at `index` 4 at `index` 18 (generation 2, 15 records), and
  after a `late_arrival` at `index` 19 at `index` 23 (generation 3, 5
  records) — writing `graphs/666cfbfe677c2822ddc8ee532d0903e6.json`,
  `.2.json` and `.3.json`; `--root-grace 0` completes once, at `index` 23, by
  `RootEnded(grace_seconds=0.0)`. `finished` reports `routed: 23` in each
  run. Recorded, 1 body of 23 records (the root its record 23): one
  completion at `index` 23 under each of the three — `Cap(records=0)`,
  `Quiet(seconds=0.0)`, `RootEnded(grace_seconds=0.0)`. Live, batch and
  incremental equal on both (186,168 bytes real, 172,483 recorded).
  - **Not in the report, observed beside it (B7-Z2):** the three generation
    graphs `--quiet 0` writes, replayed by hand into `serve --port 0 --out
    graphs --quiet 0 --requests 3` (`zoo replay ... --json`), then `spanweave
    inspect` on each: generation 1 (3 nodes) carries `orphan_parent` × 3 and
    no `parent` edge; generation 2 (15 nodes) `orphan_parent` × 10 and 5
    `parent` edges, and the three `unpaired_call` of S9; generation 3 (5
    nodes, the root among them) no `orphan_parent` and 4 `parent` edges.
    Every generation carries derived `temporal` edges (2, 9 and 1); S18 says
    which. None is the end-of-input graph (23 nodes, 22 `parent` edges, 14
    `temporal`, no `orphan_parent`).
- **Seen again in Z6** (B7-Z6, step 2 of both Z6 reports): the root's record
  (`release-notes.kickoff`) is the last record of the last of **eleven**
  bodies — `json/0011.json` record 3, the node table's Body and Record
  columns. Real, 11 bodies (2, 2, 4, 1, 2, 2, 3, 3, 2, 2 and 3 records), all
  answered 200: the end-of-input run completes once, at `index` 26, by
  `Cap(records=0)`; `--quiet 0` completes **eleven** times, once per body —
  at `index` 2, 4, 8, 9, 11, 13, 16, 19, 21, 23 and 26, generations 1 to 11,
  each after the first opened by a `late_arrival` at the body's first record
  (`index` 3, 5, 9, 10, 12, 14, 17, 20, 22, 24; generation 4's one-record
  body has its `late_arrival` and its `completed` at the same `index`, 9) —
  writing `graphs/a5e74188438ca56d4f12f94d2651b49b.json` and `.2.json` to
  `.11.json`; `--root-grace 0` completes once, at `index` 26, by
  `RootEnded(grace_seconds=0.0)`. `finished` reports `routed: 26` in each
  run. Recorded, 1 body of 16 records (the root its record 16): one
  completion at `index` 16 under each of the three — `Cap(records=0)`,
  `Quiet(seconds=0.0)`, `RootEnded(grace_seconds=0.0)`. Live, batch and
  incremental equal on both (1,304,658 bytes real, 305,886 recorded).
  - **Not in the report, observed beside it (B7-Z6):** the eleven generation
    graphs `--quiet 0` writes, replayed by hand into `serve --port 0 --out
    graphs --quiet 0 --requests 11` (`zoo replay ... --json`) and read as
    JSON (S18's command): generations 1–10 hold 2, 2, 4, 1, 2, 2, 3, 3, 2
    and 2 nodes and carry `orphan_parent` × 2, 1, 3, 1, 1, 2, 2, 3, 1 and 2
    with 0, 1, 1, 0, 1, 0, 1, 0, 1 and 0 `parent` edges; generation 11 (3
    nodes: the root, `Release Notes Reviewer._execute_core` and its last
    `ChatCompletion`) no `orphan_parent` and 2 `parent` edges. The
    `unpaired_call` of S9 are spread over generations 1, 3, 4, 6, 7, 8 (2)
    and 10. Derived `temporal` edges: 1, 0, 2, 0, 0, 1, 1, 2, 0, 1, 0; S18
    says which one joins orphans whose stated parents differ. None is the
    end-of-input graph (26 nodes, 25 `parent` edges, 18 `temporal`, no
    `orphan_parent`).

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
- **Seen again in Z1** (B7-Z1, step 4 of both Z1 reports):
  `timestamp_unit_suspect` × 31 — once per node, every row — on
  `graphs/40e8f3f6ace0600a1255ec9030397af7.json` (real) and
  `graphs/a97e57e66afeaad79303a015a945515c.json` (recorded), through
  `openinference`. Not in the report but in the graph `serve` writes (read
  beside the audit, B7-Z1), the diagnostic's own message says what raised
  it: `started_at (1791915997281317120), ended_at (1791915997282008832)
  exceeds 100000000000, which unix seconds cannot reach; the field may be in
  milliseconds or nanoseconds. Every value is kept exactly as reported and
  nothing is rescaled`. Whether it is warranted on this input stays *to
  establish*.
- **Seen again in Z2** (B7-Z2, step 4 of both Z2 reports):
  `timestamp_unit_suspect` × 23 — once per node, every row — on
  `graphs/666cfbfe677c2822ddc8ee532d0903e6.json` (real) and
  `graphs/4af82ff37ed7031332c5112ccdfcdf39.json` (recorded), through
  `openinference`.
- **Seen again in Z6** (B7-Z6, step 4 of both Z6 reports):
  `timestamp_unit_suspect` × 26 (real) and × 16 (recorded) — once per node,
  every row — on `graphs/a5e74188438ca56d4f12f94d2651b49b.json` and
  `graphs/8766332238a4971b8dc6ffef5b6fb97c.json`, through `openinference`,
  on the records of both instrumentation scopes (S6).

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
- **Seen again in Z6, in another shape** (B7-Z6, steps 4 and 5 of both Z6
  reports, and the records' scopes read beside the audit — S19's command,
  printing `Node.raw.source["scope_spans"]["scope"]`): Z6 also runs two
  instrumentors (`openinference-instrumentation-crewai==1.1.21` and
  `openinference-instrumentation-openai==0.1.65`, the capture's project
  manifest), and Z6's brief and the B7-Z6 row expect the same model client
  "seen through two instrumentors". **The captures do not show a client seen
  twice.** Every `llm` node — 14 real, 8 recorded, all named
  `ChatCompletion` — comes from the `openinference.instrumentation.openai`
  scope (0.1.65); every `chain`, `agent` and `tool` node — 12 real, 8
  recorded — from `openinference.instrumentation.crewai` (1.1.21), which
  contributes no `llm` node. No two `llm` nodes' intervals overlap, in
  either capture; the only adjacent `llm` steps in step 5's signature are a
  delegation tool's `ChatCompletion` child followed by the delegating
  agent's next call (S20), and those two have different parents. Every record is claimed by `openinference`, `unknown` 0. Whether
  the CrewAI instrumentor would emit an `llm` span of its own under another
  configuration is not shown: the record carries what was exported.

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
- **Seen again in Z1** (B7-Z1, step 4 of both Z1 reports): 31
  `unmapped_attributes` diagnostics on each graph — one per node — taking
  15,462 bytes as compact sorted JSON on both captures. Keys: Z4's four
  `<record>.*` keys and `metadata` (31 each), `llm.input_messages.0.message.role`
  (7), `llm.input_messages.0.message.content` (6), `tool.description` (6),
  `llm.finish_reason`, `llm.input_messages.1.message.{content,role}`,
  `llm.invocation_parameters`, `llm.output_messages.0.message.role`,
  `llm.provider`, `llm.system` (4 each), `llm.output_messages.0.message.content`
  (3), `llm.prompt_template.template`, `llm.prompt_template.variables`,
  `llm.tools.0.tool.json_schema` (2 each), and one each of
  `llm.input_messages.2.message.{role,tool_calls.0.tool_call.{id,function.name,function.arguments}}`,
  `llm.input_messages.3.message.{content,name}` and
  `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`.
  Named in no earlier report: `llm.provider`, `llm.prompt_template.template`,
  `llm.prompt_template.variables` and `llm.input_messages.3.message.name`. The
  node table (B6b's columns) puts the two `llm.prompt_template.*` keys on
  the two `unknown` `ChatPromptTemplate` nodes (S14), and `metadata` on every
  node. The two captures' tables are the same, key for key and count for
  count.
- **Seen again in Z2** (B7-Z2, step 4 of both Z2 reports): 23
  `unmapped_attributes` diagnostics on each graph — one per node — taking
  12,509 bytes as compact sorted JSON on both captures. Keys: Z4's four
  `<record>.*` keys (23 each); `llm.invocation_parameters`, `llm.provider`,
  `llm.system` (6 each, every `llm` node); `llm.tools.0.tool.json_schema` (4,
  the four `astream_chat` nodes); `tool.description`, `tool.parameters` (3
  each, the three `FunctionTool.acall` nodes); `<record>.events` (2, S17);
  `llm.finish_reason`, `llm.input_messages.{0,1}.message.{content,role}`,
  `llm.output_messages.0.message.role` (2 each, the two inner
  `astream_chat` nodes); and one each of
  `llm.input_messages.2.message.{role,contents.0.message_content.{text,type},tool_calls.{0,1,2}.tool_call.{id,function.name,function.arguments}}`,
  `llm.input_messages.{3,4,5}.message.content`,
  `llm.output_messages.0.message.content`,
  `llm.output_messages.0.message.contents.0.message_content.{text,type}` and
  `llm.output_messages.0.message.tool_calls.{0,1,2}.tool_call.function.arguments`.
  Named in no earlier report: the four `…contents.0.message_content.{text,type}`
  keys, and `llm.output_messages.0.message.tool_calls.{1,2}.tool_call.function.arguments`
  (one `llm` node's output naming three calls, S16). `metadata`, on every
  node of Z5 and Z1, is on none here. The two captures' tables are the same,
  key for key and count for count.
- **Seen again in Z6** (B7-Z6, step 4 of both Z6 reports): 26 (real) and 16
  (recorded) `unmapped_attributes` diagnostics — one per node — taking 39,622
  and 17,128 bytes as compact sorted JSON; 74 distinct keys real, 50
  recorded, the recorded set a subset of the real one. Keys: Z4's four
  `<record>.*` keys (every node); `llm.finish_reason`,
  `llm.input_messages.{0,1}.message.{content,role}`,
  `llm.invocation_parameters`, `llm.output_messages.0.message.role`,
  `llm.system` (every `llm` node: 14 real, 8 recorded); the history keys
  `llm.input_messages.<n>.message.{role,tool_calls.0.tool_call.{id,function.name,function.arguments}}`
  and `llm.input_messages.<n>.message.{content,name}`, growing with each turn
  of a task as Z3's do, up to `<n>` = 15 real and 7 recorded;
  `llm.tools.{0,1,2}.tool.json_schema`; `tool.description` and
  `tool.parameters` with `tool.cache_function`, `tool.current_usage_count`,
  `tool.description_updated` and `tool.result_as_answer` (every `tool` node:
  8 real, 4 recorded); `crew_id`, `crew_key` (the root and the three
  `_execute_core` nodes), `crew_agents`, `crew_inputs`, `crew_tasks` (the
  root), `task_id`, `task_key`, `graph.node.id` (the three `_execute_core`
  nodes) and `graph.node.parent_id` (two of them; S19). Named in no earlier
  report: `crew_agents`, `crew_id`, `crew_inputs`, `crew_key`, `crew_tasks`,
  `task_id`, `task_key`, `graph.node.parent_id`, the four `tool.*` keys
  `cache_function`, `current_usage_count`, `description_updated`,
  `result_as_answer`, `llm.tools.2.tool.json_schema`, and
  `llm.input_messages.<n>.message.name` for `<n>` = 5, 7, 9, 11, 13, 15.
  `metadata` is on no node, nor `<record>.events` (no record carries span
  events: the node table's Span events column is *absent* on every row of
  both).

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
- **Seen again in Z1** (B7-Z1, step 4 of both Z1 reports), with one
  instrumentor: `unpaired_call` × 1 on each graph, on the first `ChatOpenAI`
  `llm` node in graph order — `bc88f958b4e7b638` (real),
  `d65c8a757c33a1ea` (recorded), parent the `model` chain under the root —
  whose unmapped keys include
  `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`.
  Not in the report but in the graph `serve` writes (read beside the audit),
  the diagnostic's message: `call 'chatcmpl-tool-b84a56ef4e875c2d' was
  requested and no span in this input fulfils it; no edge is invented`, its
  source `{"call_id": ..., "operation": "categorize"}` (recorded:
  `call_stub_categorize_1`). The graph holds a `tool` node named
  `categorize` (`bf207c306c0f583c` real, `4b292064ede9bc73` recorded), the
  root's grandchild through the `tools` chain; its unmapped keys are the
  `<record>.*` four, `metadata` and `tool.description`. The five `fx_rate`
  tool nodes are called by a chain, not by an `llm` node, and no diagnostic
  names them. **To establish:** what the `categorize` tool span would have to
  carry for spanweave to pair it, and whether its record carries it.
- **Seen again in Z2** (B7-Z2, step 4 of both Z2 reports): `unpaired_call` ×
  3 on each graph, all three on one node — the inner `astream_chat` of the
  first step (`55d6988ab7075459` real, `da618221c331ae9b` recorded; S17) —
  whose unmapped keys include
  `llm.output_messages.0.message.tool_calls.{0,1,2}.tool_call.function.arguments`.
  Not in the report but in the graph (read beside the audit through the
  public API, `Graph.diagnostics`): the three messages are `call
  '<id>' was requested and no span in this input fulfils it; no edge is
  invented`, sources `{"call_id": ..., "operation": "fetch_policy"}` with ids
  `chatcmpl-tool-98de6bb2557bb32a`, `chatcmpl-tool-bf153eeb0a4ae1db`,
  `chatcmpl-tool-bfa245421393e6da` (real) and `call_fetch_policy_0`, `_1`,
  `_2` (recorded). The graph holds three `tool` nodes whose `operation` is
  `fetch_policy` (S16); the attribute keys their records carry are
  `input.mime_type`, `input.value`, `openinference.span.kind`,
  `output.mime_type`, `output.value`, `tool.description`, `tool.name` and
  `tool.parameters` — names only; none is a call-id key. No `call_result`
  edge is in either graph. This is what spanweave's own `SPEC.md` §4.4 states
  for an unmatched call ("never a fallback to guessing by name or
  proximity"). The second step's inner `astream_chat` carries the three ids
  again only as `llm.input_messages.2.message.tool_calls.{0,1,2}.tool_call.id`
  (unmapped, history) and no `unpaired_call`. **To establish:** whether
  LlamaIndex's OpenInference instrumentation records the call id anywhere on
  a `FunctionTool.acall` span — these records do not, by key name.
- **Seen again in Z6** (B7-Z6, step 4 of both Z6 reports): `unpaired_call` ×
  8 (real) and × 4 (recorded), one on each `ChatCompletion` whose unmapped
  keys include `llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments`
  — every `llm` node whose model requested a tool, and no other. The graph
  holds as many `tool` nodes (8 real, 4 recorded) and no `call_result` edge.
  Not in the report but in the graph (`Graph.diagnostics`, read beside the
  audit): the sources name the operations `list_commits`, `lint_markdown`
  (4 real, 2 recorded), `delegate_work_to_coworker` (2 real, 1 recorded) and
  `ask_question_to_coworker` (1, real) with ids `chatcmpl-tool-…` (real) and
  `call_<n>_<operation>` (recorded); the `tool` nodes' `tool.name` values
  are `list_commits`, `lint_markdown`, `Delegate work to coworker` and `Ask
  question to coworker` — for the two delegation tools not the operation's
  spelling — and their records carry no key containing `id` (names only).
  As in Z2, spanweave's §4.4 ("never a fallback to guessing by name or
  proximity") describes what was observed. **To establish:** whether
  CrewAI's OpenInference instrumentation records a call id on a tool span.

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

### S14. `openinference.span.kind = PROMPT` becomes an `unknown` node

- **From:** step 4's table in both Z1 reports (B7-Z1).
- **Captures:** `captures/z1/2026-10-13-real`, `captures/z1/2026-10-13-recorded`.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 2
  uv run zoo replay captures/z1/2026-10-13-real --to http://127.0.0.1:<port> --json
  uv run spanweave inspect graphs/40e8f3f6ace0600a1255ec9030397af7.json
  ```

  (`--requests 1`, `…-recorded` and `graphs/a97e57e66afeaad79303a015a945515c.json`
  for the recorded capture.)
- **Observed:** `unknown: 2` in `inspect`'s node counts and
  `unknown_span_kind` × 2 on each graph; the report's `unknown` nodes:
  `ChatPromptTemplate` × 2. The node table: `df4e7bd70f4edf20` (child of the
  `RunnableSequence` under `RunnableParallel<categories>`) and
  `e0e1f2785bd03602` (child of the `summarize` chain) real,
  `03003a0f0472b46a` and `ce2ca6162ca67c60` recorded; status `ok`, model
  absent, inputs and outputs `present`, unmapped keys including
  `llm.prompt_template.template` and `llm.prompt_template.variables`. Not in
  the report but in the graph `serve` writes (read beside the audit): the
  diagnostic's message is `openinference.span.kind='PROMPT' does not map to a
  NodeKind; kept as unknown, with the reported kind preserved in attributes`.
  Nothing was dropped; it is spanweave saying what it did not map, and not a
  finding (`SPEC.md` §7.4).
- **To establish:** whether `PROMPT` is a kind the `openinference` adapter
  is meant to map.

### S15. Z1's nesting: depth 8, and every child's record before its parent's, within and across bodies

- **From:** steps 3 and 4 of both Z1 reports, and the records step 3 feeds,
  read beside the audit. B7-Z1's points of interest (Z1's brief: "nesting
  depth and parent-before-child ordering in a real exporter's batches"),
  reported as observed; not a finding.
- **Captures:** `captures/z1/2026-10-13-real` (2 bodies, 22 + 9 records),
  `captures/z1/2026-10-13-recorded` (1 body, 31 records).
- **Command:** both `zoo audit` commands above; and for the order of the
  records, the audit's own re-read (step 3) with a `spanweave.Builder` fed
  one record at a time, noting the node each record adds:

  ```bash
  uv run python -c '
  import sys; from pathlib import Path; import spanweave; from spanweave_zoo import audit
  run = Path(sys.argv[1]); files = sorted(f"json/{p.name}" for p in (run / "json").glob("[0-9][0-9][0-9][0-9].json"))
  for part in audit.reread(run, files).partitions:
      b, seen = spanweave.Builder(), set()
      for rec, origin in zip(part.feed, part.origins):
          b.feed(rec); g = b.graph()
          for n in g.nodes():
              if n.id not in seen: seen.add(n.id); print(origin, n.id, n.kind.value, n.name, g.parents(n.id, spanweave.EdgeKind.PARENT))
  ' captures/z1/2026-10-13-real
  ```

  (A parent shown empty at the time its child is added is a parent not yet
  fed; the final graph's `parent` edges are the report's node table.)
- **Observed — depth:** 31 nodes, 30 explicit `parent` edges, one node with
  no parent (`bd08a2148df084bc` `LangGraph` real, `19b58c36ccca6627`
  recorded), no `orphan_parent`; live, batch and incremental equal. The
  longest root-to-leaf path is 8 `parent` edges (9 levels), to each of the
  five `fx_rate` `tool` nodes: `LangGraph` → `tools` (chain) → `categorize`
  (tool) → `categorize` (chain) → `RunnableAssign<rates>` →
  `RunnableParallel<rates>` → `lookup_rate` → `_fetch_rates` → `fx_rate`. The
  deepest `tool` nodes are those five (`6c17e931ae4a5989`,
  `de9709a4a4be62f2`, `64171e698a5f787d`, `c27097b50658e7c6`,
  `e7cde30149b4895b` real), all children of `_fetch_rates`, status `ok`,
  inputs and outputs `present`, no span events; the deepest `llm` node
  is the `ChatOpenAI` under `RunnableSequence` at depth 7. The recorded
  graph's node table is the real one's row for row but for node ids and the
  model (`ledger-clerk-stub`).
- **Observed — the `summarize` node:** it is a **`chain`** node, not an
  `llm` node — `fb5a00c15fff11d1` (real), `f0106dfcaca83836` (recorded),
  model absent, at depth 4, a child of the `categorize` chain and so a
  sibling of `RunnableAssign<rates>`, not beneath `lookup_rate` or
  `fx_rate`. Its children are `ChatPromptTemplate` (`unknown`, S14),
  `ChatOpenAI` (`llm`, depth 5, `04704daf4e5e5376` real /
  `eddf6a6b5613c8b0` recorded, model `Qwen/Qwen3-235B-A22B-Instruct-2507` /
  `ledger-clerk-stub`) and `StrOutputParser`. The B7-Z1 row's phrase "the
  `summarize` LLM node on the way back up" does not match the capture: the
  LLM node under `summarize` is named `ChatOpenAI`, and it is not on the path
  from `fx_rate` back to the root.
- **Observed — ordering:** in both captures every child's record is fed
  before its parent's: 30 of 30 `parent` edges, none the other way, so
  parent-before-child holds for none. Within a body: real body 1, 16 of 16
  edges with both ends in it; real body 2, 8 of 8; recorded's one body, 30
  of 30. Across bodies (real): the 6 edges whose child is in body 1 and
  parent in body 2 (L3's six `orphan_parent` under `--quiet 0`); none the
  other way. Body 1 ends inside the `summarize` subtree: its
  `ChatPromptTemplate` is the last record of body 1, and `ChatOpenAI`,
  `StrOutputParser` and `summarize` itself the first three of body 2. The
  root `LangGraph` is the last record of the last body in both captures.
- **To establish:** nothing for spanweave: at end of input it rebuilt every
  `parent` edge from child-first records, and its incremental graph equals
  its batch graph. What a consumer that completes early sees of this order is
  L3's.

### S16. Z2's fan-out: three `FunctionTool.acall` nodes start in one order and end in another; spanweave orders their parents by start

- **From:** step 4 of both Z2 reports, and the nodes' timestamps and edges
  read beside the audit. B7-Z2's first and second points of interest,
  reported as observed; not a finding.
- **Captures:** `captures/z2/2026-10-14-real` (3 bodies, 3 + 15 + 5
  records), `captures/z2/2026-10-14-recorded` (1 body, 23 records).
- **Command:** both `zoo audit` commands above; and for the timestamps and
  the derived edges, a `spanweave.Builder` fed the records step 3 feeds:

  ```bash
  uv run python -c '
  import sys; from pathlib import Path; import spanweave; from spanweave_zoo import audit
  run = Path(sys.argv[1]); files = sorted(f"json/{p.name}" for p in (run / "json").glob("[0-9][0-9][0-9][0-9].json"))
  for part in audit.reread(run, files).partitions:
      b = spanweave.Builder()
      for rec in part.feed: b.feed(rec)
      g = b.graph(); t0 = min(n.started_at for n in g.nodes())
      for n in sorted(g.nodes(), key=lambda n: n.started_at):
          print(n.id, part.origins[n.raw.line_number - 1], n.name, n.kind.value, n.started_at - t0, n.ended_at - t0, g.parents(n.id, spanweave.EdgeKind.PARENT))
      for e in g.edges():
          if e.kind != spanweave.EdgeKind.PARENT: print(e.kind.value, e.warrant.value, e.basis, e.src, "->", e.dst)
  ' captures/z2/2026-10-14-real
  ```

  (Times in ns from the root's start; the audit's report carries none.)
- **Observed — the row's premise:** the three `FunctionTool.acall` nodes are
  **not siblings** in either graph. Each is the only child of its own
  `BaseWorkflowAgent.call_tool` `chain` node; the three `call_tool` nodes are
  the siblings, children of the root `FunctionAgent.run`, beside the
  `run_agent_step`, `parse_agent_output`, `aggregate_tool_results` and
  `setup_agent` chains. The three `tool` nodes' `operation` is
  `fetch_policy`; step 5 names three `tool:fetch_policy` steps.
- **Observed — start and end order (real):** by start, `2f42891bc379dbb4`
  (15.057 s), `1d1e1964ed3f7c4e` (15.060 s), `20788a74b1c43ece` (15.062 s);
  by end, `1d1e1964ed3f7c4e` (15.162 s), `20788a74b1c43ece` (15.264 s),
  `2f42891bc379dbb4` (15.360 s) — the first started is the last to end
  (about 0.10, 0.20 and 0.30 s long). Their records are `json/0002.json`
  records 11, 5 and 8, in start order: the exporter sent them in end order.
  Recorded: by start `dbe920d1658b385c`, `253264b8d31b6e8d`,
  `4a08209acab845ee`; by end `253264b8d31b6e8d`, `4a08209acab845ee`,
  `dbe920d1658b385c`; records 14, 8 and 11 of `json/0001.json` — the same
  shape. In both captures the order of the records fed is the order of the
  spans' ends, all 23 of them, and every child's record precedes its
  parent's (22 of 22 `parent` edges).
- **Observed — how spanweave orders them:** 14 derived `temporal` edges per
  graph, every one `sibling start_time ordering`, each between two children
  of one parent (spanweave's `SPEC.md` §4.3). None touches a
  `FunctionTool.acall` node (each has no sibling). Among the root's
  children the chain runs `parse_agent_output` → `call_tool`
  (`0b76f56ee6e637fb`, parent of the first-started `acall`) →
  `call_tool` (`6610971780590a14`) → `call_tool` (`00889eb3593de58c`) →
  `aggregate_tool_results` × 3 → `setup_agent` → `run_agent_step` →
  `parse_agent_output` (real; the recorded chain is the same by name): start
  order, not end order and not record order. The edge `00889eb3593de58c` →
  `a6dd7bd6e5d950e6` (`aggregate_tool_results`) joins a `call_tool` still
  running when the `aggregate_tool_results` started (15.264 s end, 15.163 s
  start) — an order, not a precedence, as §4.3 says. `unpaired_call` × 3:
  the three calls the first step's model requested name no span (S9).
- **Observed — the parent that ends after them:** each `call_tool` ends after
  its own `acall`, by 0.385, 0.289 and 0.281 ms (real; 0.323, 0.335 and
  0.501 ms recorded), and its record follows that `acall`'s directly (records
  5→6, 8→9, 11→12 real; 8→9, 11→12, 14→15 recorded). Their common parent, the
  root `FunctionAgent.run`, ends last of all 23 spans (20.941 s real, 1.140 s
  recorded) and its record is the last record fed (`json/0003.json` record 5
  real, `json/0001.json` record 23 recorded; L3). The first step's
  `run_agent_step` ends (15.053 s real) before any `acall` starts; it is not
  their parent.
- **To establish:** nothing for spanweave from the order alone: child-first
  records in end order rebuilt every `parent` edge, and incremental equals
  batch. Whether the three tool nodes could be paired with their calls is
  S9's.

### S17. Two `astream_chat` `llm` nodes per agent step, one nested in the other, and a third `llm` node beside them

- **From:** steps 4 and 5 of both Z2 reports, and timestamps read beside the
  audit (S16's command). B7-Z2's third point of interest, reported as
  observed; not a finding.
- **Captures and command:** as S16.
- **Observed:** 6 `llm` nodes per graph, 3 under each of the two
  `BaseWorkflowAgent.run_agent_step` chains: `OpenAILike._prepare_chat_with_tools`
  and `OpenAILike.astream_chat` (the **outer**), siblings, joined by one
  `temporal` edge; and a second `OpenAILike.astream_chat` (the **inner**),
  the outer's only child. The two streams are nested, not side by side. All
  six carry the model (`Qwen/Qwen3-235B-A22B-Instruct-2507` real,
  `stub-model` recorded), status `ok`; step 5 names three consecutive `llm`
  steps per agent step. The inner's record precedes the outer's in the feed
  (e.g. real `json/0002.json` records 1 and 2).
  - Outer (`da6c5422d132ace1`, `659be38850f33552` real): outputs `absent`,
    no span events, unmapped keys the three `llm.*` of every `llm` node and
    `llm.tools.0.tool.json_schema`.
  - Inner (`55d6988ab7075459`, `db1c06636eb889b0` real; `da618221c331ae9b`,
    `72dca99b6ea6d9b6` recorded): outputs `present`, the input and output
    message keys (S7), `<record>.events` — one span event each, `First Token
    Stream Event` — and, on the first step's, the three `unpaired_call` (S9).
  - The streams' spans are short beside their step: real, the first step's
    inner spans 0.214–0.266 s and its `run_agent_step` 0.209–15.053 s; the
    second's 15.369–15.370 s within 15.366–20.936 s. Each inner node's
    `First Token Stream Event` `timeUnixNano` falls **after** that span's
    own end: 6.887 s (real, step 1; ended 0.266 s) and 15.855 s (step 2;
    ended 15.370 s); recorded 0.805 s (ended 0.254 s) and 1.130 s (ended
    1.124 s). spanweave keeps the event as the record carries it (an
    unmapped `<record>.events`, the node table's Span events block).
- **To establish:** whether the span intervals the instrumentation reports
  for a stream cover the stream at all — the timestamps are the exporter's,
  and spanweave neither checks nor rescales them; and whether an `llm` node
  wrapping another `llm` node of the same call is a shape the `openinference`
  adapter is meant to say anything about.

### S18. A partial graph orders orphans whose stated parents differ

- **From:** the generation graphs `serve --quiet 0` writes for the real Z2
  capture, read beside the audit (B7-Z2; L3's "seen again in Z2"). Step 3
  compares the end-of-input graph only, so the report does not show it.
- **Capture:** `captures/z2/2026-10-14-real`.
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --quiet 0 --requests 3
  uv run zoo replay captures/z2/2026-10-14-real --to http://127.0.0.1:<port> --json
  uv run python -c '
  import json, sys
  d = json.load(open(sys.argv[1])); name = {n["id"]: n["name"] for n in d["nodes"]}
  stated = {x["node_id"]: x["source"] for x in d["diagnostics"] if x["code"] == "orphan_parent"}
  for e in d["edges"]:
      if e["kind"] == "temporal": print(e["src"], name[e["src"]], stated.get(e["src"]), "->", e["dst"], name[e["dst"]], stated.get(e["dst"]), e["basis"])
  ' graphs/666cfbfe677c2822ddc8ee532d0903e6.json
  ```

  (`.2.json` for generation 2.)
- **Observed:** generation 1 (3 nodes, no `parent` edge, `orphan_parent` ×
  3) has two `temporal` edges, basis `sibling start_time ordering`:
  `c53d458dde4e4a12` `init_run` → `315ed06c6c80d472` `setup_agent` (both
  stating parent `86a464c4b18af821`, the root), and `315ed06c6c80d472`
  `setup_agent` → `013c6a9b437679a2` `_prepare_chat_with_tools`, whose
  record states parent `539a254a824d5e2a` (`run_agent_step`, not in that
  input). Generation 2 (15 nodes, `orphan_parent` × 10) has 9; one of them,
  `c617d3f115e8801c` `setup_agent` (stating the root) →
  `716ca47344fbdff2` `_prepare_chat_with_tools` (stating
  `727933145969a7fe`, the second `run_agent_step`), again joins nodes whose
  stated parents differ; the other 8 join nodes that both state the root. Neither cross-parent edge is in the end-of-input
  graph, where the two `_prepare_chat_with_tools` nodes are ordered only
  against their own siblings.
- **Expected (the owner's spec, at `fec7da2`):** spanweave's `SPEC.md` §4.3
  — "nodes with no parent are siblings of each other at trace root". The
  observation agrees with it if a node whose stated parent is absent counts
  as having no parent.
- **To establish:** whether it does — whether `orphan_parent` nodes with
  different stated parents are meant to form one sibling group — and what
  a consumer of an early completion (L3) is to make of an order the
  complete graph does not assert. Not looked for in earlier captures'
  generation graphs.
- **Seen again in Z6** (B7-Z6, the generation graphs of L3's "seen again in
  Z6", S18's command on each): one of the 8 `temporal` edges across the
  eleven generations joins orphans whose stated parents differ — generation
  3's `0cc839c55998fd72` `Release Notes Writer._execute_core` (stating
  `34c04caf3b53b381`, the root `release-notes.kickoff`) →
  `89e56db8cdd3d86d` `ChatCompletion` (stating `961eb676dd44c052`, the
  Reviewer's `_execute_core`), basis `sibling start_time ordering`. The
  other 7 join nodes that state the same parent. The end-of-input graph has
  no such edge: there the Writer's node is ordered only against the other
  two `_execute_core` nodes.

### S19. Z6's nesting: one `agent` node per task, under the crew's `chain`; the records' `graph.node.parent_id` names the previous agent

- **From:** step 4 of both Z6 reports, and the records read beside the audit.
  B7-Z6's first point of interest, reported as observed; not a finding.
- **Captures:** `captures/z6/2026-10-14-real` (11 bodies, 26 records),
  `captures/z6/2026-10-14-recorded` (1 body, 16 records).
- **Command:** both `zoo audit` commands above; and for times, scopes and the
  records' attributes, a `spanweave.Builder` fed the records step 3 feeds:

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
  ' captures/z6/2026-10-14-real
  ```

  (Times in ns from the root's start; the audit's report carries none.)
- **Observed — the row's premise:** "tasks nested under agents nested under
  the crew" is **not** three levels in either capture. The root is
  `release-notes.kickoff`, a `chain` node (`34c04caf3b53b381` real,
  `4f7e2c35179f73b8` recorded). Its only children are three `agent` nodes
  named `<agent role>._execute_core` — `Commit Collector`, `Release Notes
  Writer`, `Release Notes Reviewer` — siblings ordered by two `temporal`
  edges in that order. Each is **one** span per task: its record's
  `openinference.span.kind` is `AGENT` and it carries `task_id`, `task_key`,
  `crew_id`, `crew_key` and `graph.node.id` (the agent's role); no separate
  task span or agent span is in either capture. Under each, the `llm` and
  `tool` nodes of that task. The deepest path is 3 `parent` edges: root →
  Reviewer's `_execute_core` → a delegation `tool` node → its
  `ChatCompletion` (S20). `_execute_core` under `release-notes.kickoff`, as
  the row says, holds.
- **Observed — two statements of structure:** the Writer's and the
  Reviewer's records carry `graph.node.parent_id` naming the **previous
  agent** (`Commit Collector` and `Release Notes Writer` respectively) — the
  crew's sequential order — while their span parent is the crew's kickoff.
  The Commit Collector's carries none. spanweave builds the `parent` edges
  from the spans' parent ids and leaves `graph.node.id` and
  `graph.node.parent_id` unmapped (S7); the sequence they state appears in
  the graph only as the `temporal` edges between the three siblings, which
  are derived from start times, not from those attributes.
- **Observed — intervals (real):** the three tasks run 0.052–2.806 s,
  2.814–7.309 s and 7.331–48.277 s inside the root's 0–48.300 s (recorded
  0.052–0.543, 0.552–0.574, 0.594–0.812 inside 0–0.825 s). The kickoff's
  inputs are *absent* (its record has no `input.value`), its outputs
  `present`.
- **To establish:** whether the `openinference` adapter is meant to map
  OpenInference's `graph.node.id` / `graph.node.parent_id`, and what it would
  do where they state a relation other than the span parent.

### S20. Delegation is a `tool` node with the coworker's `ChatCompletion` as its only child; no `agent` node for the coworker

- **From:** steps 4 and 5 of both Z6 reports, and the records read beside the
  audit (S19's command). B7-Z6's second point of interest, reported as
  observed; not a finding.
- **Captures and command:** as S19; for the persona, each `ChatCompletion`
  record's `llm.input_messages.0.message.content` (its system message), of
  which only the opening words were read.
- **Observed:** the delegation spans are `tool` nodes (`openinference.span.kind`
  `TOOL`, scope `crewai`), children of the Reviewer's `_execute_core`:
  real, `Delegate work to coworker.run` × 2 (`853c794192f0bb63`,
  `a20b4dfd274d45e2`) and `Ask question to coworker.run` × 1
  (`ca55b967aa976a9b`); recorded, `Delegate work to coworker.run` × 1
  (`449398542054a6e1`). Each has exactly one child, a `ChatCompletion` `llm`
  node (`05fee439adbecf19`, `344735450e29f7e9`, `b9bffcf46a373332` real;
  `d713a1c08b316e89` recorded) whose system message opens "You are Release
  Notes Writer." — the coworker's persona — while every other
  `ChatCompletion` under the Reviewer's task opens "You are Release Notes
  Reviewer." No `_execute_core` or other `agent` node stands for the
  coworker's work: the coworker is visible only as that `llm` node, under
  a `tool` node, under the delegating agent's task. Its interval lies
  inside the tool's (real: 16.327–19.482 s in 16.313–19.494 s; 27.367–29.720
  in 27.354–29.732; 34.956–39.868 in 34.945–39.879). None of the three
  carries an `unpaired_call`; the delegating `ChatCompletion` before each
  tool does (S9). Step 5 names the steps `tool:Delegate work to coworker`
  and `tool:Ask question to coworker`, each followed by the coworker's
  `llm` step.
- **To establish:** whether a consumer can tell the coworker's model call
  from the delegator's other than by its parent being a delegation tool —
  the graph carries no agent identity on an `llm` node (its normalized
  attributes are `model` alone).

### S21. Records in a Z6 body are grouped by instrumentation scope, not in end order

- **From:** step 3's list of records fed and step 4's Body and Record
  columns, both Z6 reports, with end times read beside the audit (S19's
  command). Observed; not a finding.
- **Captures and command:** as S19.
- **Observed:** in every real body that holds records of both scopes, the
  `openai` scope's records come first and the `crewai` scope's after them,
  each scope's in the order its spans ended — so where a `crewai` span ended
  before an `openai` span of the same body, its record still comes later:
  `json/0003.json` records 1–4 are `ChatCompletion` (the Writer's, ended
  7.296 s), `ChatCompletion` (the Reviewer's, 11.463 s), `Release Notes
  Writer._execute_core` (7.309 s), `lint_markdown.run` (11.466 s);
  `json/0008.json` records 1–3 are `ChatCompletion` (32.794 s),
  `ChatCompletion` (34.943 s), `lint_markdown.run` (32.797 s) — each span's
  end, from the root's start. The recorded capture's
  one body: records 1–8 are the eight `ChatCompletion`s, records 9–16 the
  eight `crewai` spans, the root last. In both captures every child's
  record precedes its parent's (25 of 25 `parent` edges real, 15 of 15
  recorded), as in Z1 (S15) and Z2 (S16).
- **To establish:** nothing for spanweave: it rebuilt every `parent` edge and
  incremental equals batch. Records reach a receiver in the exporter's order,
  not the spans' (L3).

### S22. Real and recorded: two shapes of one crew

- **From:** both Z6 reports, side by side. B7-Z6's fourth point of interest,
  reported as observed. That the real run did not follow its script is the
  capture's own fact (`WORKPLAN.md` §3, 2026-10-14, "captures"; the contract
  allows randomness in the real run), not a defect of anything audited.
- **Captures and command:** both `zoo audit` commands above.
- **Observed — the same:** the root `release-notes.kickoff` and its three
  `_execute_core` children in the same order; the Commit Collector's task
  as `ChatCompletion`, `list_commits.run`, `ChatCompletion`; the Writer's
  as one `ChatCompletion`; every node status `ok`; every record claimed by
  `openinference`; the same diagnostic codes (S3, S7, S9), no `unknown`
  node, no `orphan_parent` at end of input; the `list_commits.run` node's
  inputs `empty` (its `input.value` is `{}`) on both — the first `empty`
  payload state in any zoo report — and the root's inputs *absent*.
- **Observed — the departure (the Reviewer's task):** recorded, 7 children in
  start order — `ChatCompletion`, `lint_markdown.run`, `ChatCompletion`,
  `Delegate work to coworker.run` (with the Writer's `ChatCompletion`),
  `ChatCompletion`, `lint_markdown.run`, `ChatCompletion` — two lint passes
  and one send-back, as Z6's brief scripts ("the reviewer sends the draft
  back exactly once, then approves"). Real, 15 children — `ChatCompletion`,
  `lint_markdown.run`, `ChatCompletion`, `Delegate work to coworker.run`,
  `ChatCompletion`, `lint_markdown.run`, `ChatCompletion`, `Delegate work to
  coworker.run`, `ChatCompletion`, `lint_markdown.run`, `ChatCompletion`,
  `Ask question to coworker.run`, `ChatCompletion`, `lint_markdown.run`,
  `ChatCompletion` — four lint passes, two delegations and one question.
  Totals: 26 nodes (`agent` 3, `chain` 1, `llm` 14, `tool` 8), 25 `parent`
  and 18 `temporal` edges, 60 diagnostics, 26 signature steps real; 16 nodes
  (3, 1, 8, 4), 15 and 10, 36, 16 steps recorded. Real ran 48.3 s in 11
  bodies; recorded 0.825 s in 1. By span name, the recorded Reviewer's seven
  children are the real one's first seven; where the recorded run approves
  after its first send-back, the real one goes on.
- **To establish:** nothing for any of the three libraries: both shapes were
  read without a finding beyond L1, and each is what its run exported.

---

## agentgolden

None. Step 5 (`agentgolden.signature.signature(graph)`, no rules) returned
four `llm` steps on each written graph of Z4's, 102 steps on each of Z3's,
4 steps on each of Z5's, 31 on each of Z1's, 23 on each of Z2's, and 26
(real) and 16 (recorded) on Z6's, and raised on none — again in all six
re-audited reports (B7r), in both Z1 reports (B7-Z1), in both Z2 reports
(B7-Z2) and in both Z6 reports (B7-Z6). S10's `llm:-` steps were *to establish* as possibly
agentgolden's; the re-audit's node table shows the graph itself carries no
model on those nine nodes, so the signature reads it as it is.
