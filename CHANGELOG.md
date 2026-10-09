# Changelog

Pre-release. Nothing here is frozen: the CLI, the capture layout and
`MANIFEST.json` all still move. Entries are by batch id (`WORKPLAN.md` §1).

## A3a — a capture exists only once it is ready

- **Readiness is two things, and the run directory comes after both**
  (`SPEC.md` §4.6). `zoo capture` now binds both sinks, starts the Collector
  and waits for it, and only **then** creates `captures/<project>/<run-id>/`,
  labels the manifest, sets the sinks serving and prints the single readiness
  line `zoo capture: the raw bytes are the record. Ctrl-C to stop.` A refusal
  for any reason -- a port held, the Collector exiting, a config it cannot
  load, a binary that is not the pin -- happens before that line and leaves
  **no run directory at all**, exiting 2 and naming the port or the cause. A
  capture directory now means a capture was made.
- **The Collector's readiness is its own ready line, not a port that accepts**
  (`SPEC.md` §4.6, §4.2). The wait requires `Everything is ready. Begin
  running and processing data.` in the Collector's own log **and** a connection
  its receiver accepts. The old check only connected, so a stranger already
  holding 4320 passed it: the probe reached the stranger, the Collector that
  could not have the port exited, and the capture was recorded as if fine with
  a `json/` that could only ever be empty. The child's output is piped and
  drained by a thread instead of inherited, so a refusal quotes the
  Collector's last lines -- `bind: address already in use` among them -- and
  the operator still sees its log as it happens.
- **`collector/config.yaml` leaves `service.telemetry.logs.level` at the stock
  `info`** (`SPEC.md` §4.2), where it asked for `warn` before: the ready line
  is logged at `info`, and at `warn` a healthy Collector says nothing at all
  on startup. The metrics level stays `none` -- the Collector's own telemetry
  is still not part of a capture.
- **A Collector that exits during a run is recorded, not absorbed**
  (`SPEC.md` §4.6, §4.5). The caller's wait notices it on its next hop and
  writes `problems: ["collector exited: <code>"]` into `MANIFEST.json` there
  and then, prints it, and `zoo capture` exits non-zero. Recorded once however
  often it is looked at; the key is absent from a capture that had none. The
  raw sink keeps recording, because the raw bytes are the record.
- **`zoo sink`'s banner and the capture's readiness line are distinct**, each
  naming its own command, neither a prefix of the other (`cli.SINK_BANNER`,
  `capture.READY_LINE`).
- Internals: `_Listener` binds at construction and serves later, so a port is
  held before any directory exists and an unserved listener is closed without
  waiting for a loop that never started. `sink.Recorder` takes
  `create_directory` -- `zoo sink` still creates `--out` when it starts
  (`SPEC.md` §3.1), `zoo capture` does not. The `launch` seam's handle can be
  asked whether the child is still there (`SPEC.md` §4.8).
- Tested against a **stand-in child process** rather than the 100 MB download
  (`SPEC.md` §4.9): it binds the receiver endpoint it is handed through
  `ZOO_COLLECTOR_OTLP_HTTP` and logs the way the Collector does, which is
  enough to drive a held port, a Collector that holds a port and never reports
  ready, and a config it cannot load. It claims no re-encoding, which stays
  `test_collector_real.py`'s one job.

## A3 — the capture is a manifest, immutable

- **`zoo capture` ends by writing the whole `MANIFEST.json`** (`SPEC.md` §5):
  the pet project's own `MANIFEST.json` copied **verbatim** from a path the
  operator passes (`--project-manifest`), the zoo's `sink_version`, the pinned
  `collector_version`, `kind`, `started_at` / `ended_at` from the injected
  clock, and `bodies` entries carrying `content_type` / `content_encoding`
  beside A1's `file`, `sha256` and `bytes` -- for `raw/`, for `json/` and for
  rejected bodies alike. Nothing else: no span counts, no durations, no
  judgement of a capture (`SPEC.md` §1.4).
- **`--kind` is required, and is never inferred** (`SPEC.md` §5.2).
  `recorded` | `real`, no default, nothing derived from the project's own
  `mode`, the endpoint or the environment: a recorded capture and a real one
  differ by that declaration alone and the audit reads it as the truth.
  `zoo capture` refuses the command, and `manifest.label` refuses to write a
  manifest it cannot label.
- **The project's manifest is copied, not merged and not validated**
  (`SPEC.md` §5.3). No field of it is read -- including `mode` -- and if it
  disagrees with `kind`, both declarations sit in the record. The one thing
  checked is that the path holds a readable JSON **document**, and a path that
  is missing, unreadable or not JSON is a refusal **at the start** of the
  capture, before any bytes are on disk: the alternative is a capture that can
  only be completed by editing it.
- **The content headers are carried across, not inspected** (`SPEC.md` §5.4,
  and §1.1 is amended to say so in place). A1 deliberately left
  `content_type` / `content_encoding` out because the sink does not look at a
  content type except to echo it; the values were already verbatim in each
  body's `NNNN.headers.json`, so the manifest writer copies them from the
  record at the end of the run. No byte of a body is read to do it, the sink
  is unchanged, and a header that legally repeats is carried once with
  `headers.json` still the record of the repeat.
- **`zoo verify` checks both directions** (`SPEC.md` §5.6): every body the
  manifest lists is on disk with the digest and the length it recorded, **and
  every file on disk is one the manifest accounts for**. A body present on
  disk but absent from the manifest now fails -- A1 left that deliberately
  unimplemented -- as does a headers file with no listed body beside it. The
  check walks the **directory** as well as the list, because a check that
  iterated the manifest can only confirm what the manifest already says.
- `zoo verify [path]` now accepts **one run directory** as well as a capture
  root, which is what an operator types after a run. It used to glob two
  levels down from it, find nothing, say so and exit **zero** -- a reassuring
  pass over a capture nobody checked. Each run's line also prints the `kind`
  the capture declares, and `none declared` for a `zoo sink` run that declares
  nothing.
- `README.md` gains **"Running a pet project's real run"**: the five commands
  an operator types, exercised end to end against the real Collector with a
  real OTLP protobuf export and stopped with `SIGINT` the way the section says
  to stop it.
- **A defect the real run surfaced, fixed here** (`SPEC.md` §3.1): the sink's
  refusal to start in a directory that already holds a capture globbed `*` +
  its body suffix, and the json sink's bodies are `*.json` -- so it counted
  `NNNN.headers.json` as a body and refused a re-used run id with "2 body
  file(s), starting 0001.headers.json". Bodies and headers files are now
  counted apart and named accurately, and a directory holding only a headers
  file is still refused: half a capture is a capture to refuse.

## A2 — the Collector re-encodes beside the raw

- `collector/`: the **stock** OpenTelemetry Collector (contrib), pinned at
  **0.162.0** in `collector/VERSION`, with the release's own sha256 for each
  platform in `collector/SHA256SUMS` and its config checked in at
  `collector/config.yaml` (`SPEC.md` §4.1, §4.2). `make collector` downloads
  exactly that release, **refuses to unpack anything whose digest is not the
  pinned one** -- or a platform with no line at all -- and extracts the
  binary, which is **gitignored**: the pin is the record, the bytes are a
  download. Nothing in `make check` fetches it.
- The config is one `otlp` receiver, `batch` at its defaults, one `otlp_http`
  exporter with `encoding: json`, one traces pipeline, and no components
  beyond those. Its endpoints are `${env:NAME:-default}`, the stock confmap
  form, so **the file checked in is the file that runs** and the ports are
  supplied rather than edited. Two settings are not defaults and say why in
  place: `compression: none` (the sink never decompresses, so a gzipped
  re-encoding would make `json/NNNN.json` a gzip member rather than JSON) and
  `service.telemetry.metrics.level: none` (a recorder should not open a fourth
  listening port it never reads). The A2 row's `otlphttp` is a deprecated
  alias at this version; `otlp_http` is the same component's current name.
- `zoo capture --project z4 --run-id <id>` (`SPEC.md` §4.6): **two recorders
  in one process on one run directory** -- the raw sink on **4318**, the port
  every brief gave the pet projects, and the json sink on **4319** where the
  Collector exports -- with the Collector itself behind the raw sink on a
  third port. Start order is json sink, Collector, raw sink; stop order is the
  reverse, so the Collector's last batch has somewhere to flush.
- **The tee** (`SPEC.md` §4.3): the raw sink writes the body, its headers and
  its digest to disk and **then** forwards the same bytes to the Collector.
  Byte-identical -- still gzipped if it arrived gzipped, still protobuf if it
  arrived as protobuf -- and header-identical, in order and with repeats,
  minus only `Host` and the hop-by-hop headers of RFC 9110 §7.6.1, which name
  the connection rather than the payload. A **rejected** POST (`SPEC.md` §3.4)
  is recorded and *not* forwarded: forwarding it would invent traffic the
  exporter never aimed at the Collector. The answer to the exporter is still
  `200`, empty, its own content type echoed -- it does not depend on the bytes
  and it does not depend on the forward.
- **A forward that fails loses nothing and is never silent** (`SPEC.md` §4.4):
  the body is already recorded and is untouched, the failure is written into
  `MANIFEST.json` as a `forwards` entry, it is printed naming the body, and
  `zoo capture` exits non-zero -- so a run whose `json/` is incomplete cannot
  be mistaken for one that is complete.
- **One manifest, two sinks** (`SPEC.md` §4.5), which is what A3 inherits:
  one `MANIFEST.json` per run directory carrying `bodies` for raw *and* json,
  written under **one lock per run directory** so two recorders cannot
  interleave a read-modify-write. The two sinks get different `--out`
  directories and different rejected directories (`rejected/` and
  `rejected-json/`), because two recorders on one directory would share a
  counter and overwrite each other. A2 added exactly two manifest fields:
  `collector_version` (the pin, written before the first body) and `forwards`
  (delivery, not bytes -- so A1's three-key `bodies` entries are untouched).
- Refusals rather than reassurance (`SPEC.md` §4.6): no `VERSION` or no
  `config.yaml`; no binary, naming `make collector`; a binary whose
  `--version` is not the pin; a run directory that already holds a body, in
  either sink; a `--run-id` that is not one path segment; a Collector that
  does not accept a connection within the readiness budget. `make
  install-check` asserts the last of these on the **shipped** wheel, where
  `collector/` is absent by design.
- **`SIGINT` and `SIGTERM` end a run cleanly** (`SPEC.md` §4.6), through a
  handler that only asks it to stop, with the shutdown on the main thread.
  Found by running the real thing rather than by reasoning about it: a capture
  has three threads blocked in `select`, the kernel may deliver the signal to
  any of them, and a main thread parked in an *untimed* wait never runs the
  Python handler -- so Ctrl-C did nothing and the Collector stayed up holding
  its port. The caller now waits in short hops, as
  `socketserver.serve_forever` does and for the same reason.
- `raw/NNNN` and `json/NNNN` are documented as a **convenience, not a
  promise** (`SPEC.md` §4.7): the batch processor may coalesce or split, so
  `json/NNNN.json` is the NNNN-th POST the *Collector* made. Nothing is
  renumbered, merged or split to make the columns line up.
- Seams, injected and named in `SPEC.md` §4.8: `forward`, `launch`, `sleep`
  (the Collector's readiness wait -- a bounded number of connection attempts,
  never a clock read) and `after_forward`. `cli.py` is still the only module
  that reads the world, and now holds the one real `sleep` beside the one real
  `now`.
- Thirty-eight new tests. The tee's mechanics run everywhere, against the
  `forward` seam, including the degenerate cases: a Collector that refuses the
  connection, one that answers `503`, a rejected POST that is not forwarded,
  two rejected directories that must not collide. The **real Collector**
  integration test -- hand-built OTLP protobuf through the tee, asserted to
  come back as `json/0001.json` with **the same trace and span ids**, plus a
  gzipped second export -- runs when `collector/otelcol-contrib` is present
  and is **skipped when it is absent**, so `make check` is green both ways and
  CI never downloads 100 MB. It skips loudly rather than passing quietly.
  There is no protobuf library here and there is not going to be one:
  `tests/otlp.py` encodes the export by hand, field number by field number.
  Mutation shown caught: a tee that forwards a decompressed body fails
  `test_the_forwarded_body_is_the_bytes_that_arrived`, and one that forwards
  before writing fails `test_the_body_is_on_disk_before_the_forward_is_attempted`.

## A1 — the sink records bytes, and nothing else

- `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` (`SPEC.md` §3),
  on stdlib `http.server` and **no new dependency**: a `POST /v1/traces` with
  any `Content-Type` and any `Content-Encoding` becomes `raw/NNNN.body` -- the
  bytes exactly as received, still gzipped if they arrived gzipped -- beside
  `raw/NNNN.headers.json` (method, path, **every** header as a list of
  `[name, value]` pairs so a repeated header survives, body length, and a
  receipt time from the injected `now`). Answered `200`, empty body, the
  request's own content type echoed back.
- A POST to any other path is answered `404` and **still recorded**, under
  `rejected/` with its own counter (`SPEC.md` §3.4). An exporter aimed at the
  wrong endpoint is a fact to hold, and a 404 that dropped the bytes would
  lose it.
- The sink never decodes, decompresses, parses or validates a body, and never
  edits a capture: it **refuses to start** if `--out` already holds a body
  (`SPEC.md` §3.1). A body that is empty, truncated, mislabelled or lying
  about its encoding is recorded like any other; a POST with no
  `Content-Length` is recorded as a zero-byte body rather than having its
  framing guessed at (`SPEC.md` §3.7).
- `MANIFEST.json`'s `bodies` entries -- `file`, `sha256`, `bytes` -- written
  incrementally as the sink records (`SPEC.md` §3.5). This is the one part of
  the manifest `CLAUDE.md` §0.6 rule 2 already mandated, and `zoo verify` had
  nothing to re-hash against without it. The digest has exactly one home: it
  is **not** also copied into `NNNN.headers.json`. Everything else the
  manifest will carry is still A3's, added to this same file and these same
  entries (`SPEC.md` §5, which now also records what A1 did *not* do: fail on
  a body present on disk but absent from the manifest).
- `zoo verify` therefore stops refusing every capture and re-hashes: non-zero
  on a changed byte, a wrong length, a listed body that is missing, or a
  manifest it cannot read. A run with no readable manifest is still a refusal.
- Seams, all injected and all named in `SPEC.md` §3.6: `now` (the one real
  clock in the package lives in `cli.py`), the listener factory (tests bind
  `127.0.0.1` on port `0`, so the suite cannot collide with a port in use),
  and `before_record` / `after_record` -- which is how the receipt-order test
  holds two POSTs genuinely in flight **without sleeping**.
- Twenty new tests over a real socket, plus one in `tests/test_cli.py`
  asserting that no module but `cli.py` reads a clock: a protobuf, a JSON and
  a gzip body each round-tripping byte for byte; two POSTs in flight numbered
  in receipt order; `zoo verify` passing on a sink-written capture and failing
  after one bit of one byte changes. Mutation shown caught: a sink that
  decompresses before writing fails the gzip case.

## A0 — the repository skeleton

- `pyproject.toml`: package `spanweave_zoo`, console script `zoo`, Python
  3.11–3.14, **zero runtime dependencies**, the PEP 561 marker shipped. An
  `audit` extra — and only an extra — pins `spanweave` and `spanweave-live` by
  git sha for A5; a `dev` extra carries ruff, mypy and pytest. `uv.lock`
  committed.
- `Makefile` as the source of truth for the gates: `check` (ruff, ruff format,
  `mypy --strict`, pytest, the gate, `zoo verify`), `verify`, `install-check`.
  `zoo verify` is a prerequisite of `check` from the start, because "a capture
  is immutable" is only a claim if something re-checks it on every run
  (`CLAUDE.md` §0.6 rule 2).
- `.github/workflows/ci.yml`: `make check` and `make install-check` on Python
  3.11–3.14 on ubuntu-latest and 3.12 on macos-latest. CI installs
  `--extra dev` and never `--extra audit`: A0 through A4 must work without
  `spanweave` and `spanweave_live` present, and a CI that installed them would
  hide the day that stopped being true.
- `CLAUDE.md`: the operating contract, carrying `WORKPLAN.md` §0.6 as its own
  §0.6 — the eight standing rules, the architecture invariants, the halt
  points.
- `CONTRIBUTING.md`: the batch bar — spec first, a failing test confirmed red
  on the *derived* parent `<sha>^` in a worktree created by absolute path under
  the scratchpad, one named mutation shown caught, one concern per commit, a
  changelog entry, `make check` and `make verify` green, CI green on the tip.
- `SPEC.md` §1 (the zoo parses nothing, fixes nothing, improves nothing) and §2
  (the capture layout on disk). §§3–7 are headings naming what A1–A5 will
  specify, deliberately empty.
- `tests/gates.py` + `tests/test_gates.py`: one gate — no module under
  `spanweave_zoo/` imports `spanweave` or `spanweave_live` except `audit.py`.
  An AST walk, not a grep, so a nested, aliased or `TYPE_CHECKING` import is
  caught too; thirteen planted violations are each watched failing, and each is
  watched passing inside `audit.py`.
- `spanweave_zoo/`: `__init__.py`, `cli.py` and `py.typed`, minimal on purpose.
  `zoo --help`, `zoo --version`, and `zoo verify`, which exits 0 on a tree with
  no captures and **fails** on a capture it cannot yet re-hash rather than
  reporting an unchecked capture as verified — A3 implements the re-hash
  (`SPEC.md` §5).
- `README.md`: what the zoo is, the pre-release warning, the gates, and the
  provenance of the contract and the briefs.
- `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root, byte-identical to the
  documents handed to the pet projects, with their sha256s in `README.md`.
  Both root copies are contract version **1.1**; the pilot project Z4
  (`streaming-concierge`) was built against **1.0**, and the difference is the
  contract's own closing "Changes from 1.0" section. From now on every project
  is started from these bytes.
