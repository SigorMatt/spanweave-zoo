# PROBES.md — what the next series of each library starts from

Series 1 of the zoo (`TASKS.md`) closed with one audit, `zoo audit`
(`SPEC.md` §7), over Z4's two captures. Its reports are `audit/z4-2026-10-12-real.md`
and `audit/z4-2026-10-12-recorded.md`; this file consolidates them into the
probe list each owning repository's next series starts from.

A probe is a reproduction, never a fix (`CLAUDE.md`, standing rule 7): a
capture, a command, what was observed, what the audit expected, and the
repository that owns it. Nothing below is fixed or worked around here, and
nothing below says how it should be fixed; that belongs to the owner's series.
The owner is named by `SPEC.md` §7.4's table.

**Pins.** Every observation below was made at `spanweave@fec7da27af517ad8b58ae3ec57827916aae60674`
(0.9.1), `spanweave-live@cddc694b8b2a365434c0d97889f6e303e08a0b6d` (0.0.1) and
`agentgolden@aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0), the `audit`
extra's pins, with the stock Collector 0.162.0.

**Reproducing everything at once**, from a checkout of this repository:

```bash
uv sync --extra dev --extra audit
uv run zoo verify captures/z4/2026-10-12-real
uv run zoo verify captures/z4/2026-10-12-recorded
uv run zoo audit captures/z4/2026-10-12-real --out "${TMPDIR:-/tmp}"/zoo-audit
uv run zoo audit captures/z4/2026-10-12-recorded --out "${TMPDIR:-/tmp}"/zoo-audit
```

The reports it writes differ from the committed ones only in the `listening`
port and the clock readings in a `completed` event (each report's "Method").
Each probe also gives the step's own commands, as the reports print them.

**Count.** spanweave-live: 2. spanweave: 5. agentgolden: 0 (step 5's
`signature` ran clean on every written graph of both captures).

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

### L2. A record `serve` routed reaches no graph, and no event says where it went

- **From:** finding F3 in both reports (step 3). Same record as S1.
- **Captures:** `captures/z4/2026-10-12-real` (`json/0002.json` record 2);
  `captures/z4/2026-10-12-recorded` (`json/0001.json` record 5).
- **Command:**

  ```bash
  uv run spanweave-live serve --port <port> --out graphs --requests 2
  uv run zoo replay captures/z4/2026-10-12-real --to http://127.0.0.1:<port> --json
  ```

  (`--requests 1` and `…-recorded` for the recorded capture.)
- **Observed:** `finished` reports `routed: 5`; the one graph `serve` wrote holds
  4 of them. The fifth — Z4's root span, which no adapter claims (S1) — went to
  the no-trace builder, which is never completed and never written, and no
  event names it.
- **Expected (the audit's):** each record of a trace reaches that trace's
  graph, or an event says where it went. At the pinned sha, spanweave-live's
  `SPEC.md` §4.3, §5.4 and §8.5 describe the route the record took.

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
  otel_genai 0.00), batch and incremental alike.
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
- **To establish:** whether these four follow from S1 alone.

### S3. `timestamp_unit_suspect` on every span

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** `timestamp_unit_suspect` × 4 on each graph, from the stock
  Collector's OTLP/JSON re-encoding of a stock exporter's export.
- **To establish:** what in the record raises the suspicion, and whether it is
  warranted on this input.

### S4. `unmapped_attributes` on every span

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** 4 diagnostics on each graph (2,044 bytes real, 2,152 bytes
  recorded, as compact sorted JSON), each naming `<record>.flags`,
  `<record>.kind`, `<record>.resource_spans`, `<record>.scope_spans`,
  `gen_ai.provider.name`, `gen_ai.response.id`, `gen_ai.response.model` and
  `server.address`; the recorded capture adds `server.port`.
- **To establish:** which of these the `otel_genai` adapter is meant to map.

### S5. `unpaired_call` once per graph

- **From:** step 4's table in both reports.
- **Captures and command:** as S2.
- **Observed:** `unpaired_call` × 1 on each graph.
- **To establish:** which call is unpaired, and whether it follows from S1.

---

## agentgolden

None. Step 5 (`agentgolden.signature.signature(graph)`, no rules) returned
four `llm` steps on each written graph and raised on none.
