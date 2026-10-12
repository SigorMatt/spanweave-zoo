## The operator flow, run as shipped (tasks 4 and 5)

Worktree: `/tmp/claude-1000/-home-msi-git-spanweave/db8f7f20-b229-460c-afff-06719260f7b2/scratchpad/wt-operator`
at `b913e2b` (detached). Nothing in `/home/msi/git/spanweave-zoo` was read-written, staged,
committed or checked out. Ports used: the stock defaults 4317/4318/4319/4320, plus 14317-14319
for the port-attribution experiments. Exporter: a throwaway `uv venv` under the scratchpad with
`opentelemetry-sdk==1.45.1` + `opentelemetry-exporter-otlp-proto-http==1.45.1`.

**Headline: a stranger following the README gets a capture.** The flow works end to end, the
bytes land, the Collector re-encodes them, the ids match, Ctrl-C shuts everything down cleanly
and `make verify` is green. Two of the five commands as *printed* do not run (§(A) R1, R2), and
the thing that worries me most is not a README error at all — it is that `zoo capture` will
tell you `collector 0.162.0 up, re-encoding to JSON` when its Collector is dead (§(A) R9).

---

### What I ran, and what happened

```
uv sync --extra dev                       -> 0.5s, 13 packages (README L113 step, not in the "five")
make collector                            -> OK in 5.9s; sha256 checked and matched (quoted below)
zoo capture --project probe --run-id 2026-10-10T12-00-00Z \
  --kind recorded --project-manifest <scratchpad>/pet-probe/MANIFEST.json   (background)
                                          -> up in ~0.45s; 4319, 4320, 4317, 4318 all accepting at T0+5.6s
                                             (first run: +5.6s cold; later runs +0.45s warm)
<second shell> one real OTLP/HTTP protobuf export, stock SDK
                                          -> force_flush -> True, 283-byte body recorded, 200
kill -INT <capture pid>                   -> exit 0, both sinks + Collector down, all ports released
make verify                               -> exit 0
```

`make collector`, quoted verbatim:

```
uv run python collector/fetch.py
collector: otelcol-contrib 0.162.0 for linux_amd64
  fetching https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.162.0/otelcol-contrib_0.162.0_linux_amd64.tar.gz
  sha256 fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3 matches collector/SHA256SUMS
collector: .../collector/otelcol-contrib ready (gitignored -- the pin is the record)

real	0m5.942s
```

The digest check ran and passed, against the line in `collector/SHA256SUMS`. `./collector/otelcol-contrib --version` → `otelcol-contrib version 0.162.0`.

**The manifest I had to author.** `EXPORT-CONTRACT.md` §1 (lines 27-34) gives the shape as a
literal JSON object, and that was enough — I typed it straight from the contract and `zoo capture`
accepted it. What I had to guess, all cosmetic because §5.3 reads no field of it: that the object
is flat with no wrapper key; that `endpoint` is the base URL (`http://localhost:4318`) and not the
`/v1/traces` path the exporter actually POSTs to; that `platform` is a `platform.platform()`
string; and that `instrumentation` is a list of `pkg==ver` strings even for one entry. **Not a
finding** — §5.3 says the zoo copies it verbatim and validates nothing, and that is exactly what
it did. The one thing neither document says is that the file must be a JSON **object** rather than
any JSON document (§5.3 says "document"); I did not test a top-level array.

**What the stock exporter actually sent** (first time a real stock exporter has hit this sink) —
`raw/0001.headers.json`, verbatim:

```json
{"method": "POST", "path": "/v1/traces", "bytes": 283,
 "headers": [["Host", "localhost:4318"],
             ["user-agent", "OTel-OTLP-Exporter-Python/1.45.1"],
             ["Accept-Encoding", "gzip, deflate, zstd"],
             ["Accept", "*/*"],
             ["Connection", "keep-alive"],
             ["content-type", "application/x-protobuf"],
             ["Content-Length", "283"]],
 "received_at": "2026-10-09T22:30:53.397560+00:00"}
```

- `content-type: application/x-protobuf`, **lower-cased by the exporter** (the sink records the
  case as sent — good).
- **No `Content-Encoding`. It did not gzip.** The stock Python exporter's default compression is
  `None`, so the README's "still gzipped if they arrived gzipped" (L46-47) is a real capability
  that this exporter never exercises. Worth knowing before the audit: `content_encoding` is `null`
  in the manifest, and a reviewer should not read that as a zoo bug.
- `Accept-Encoding: gzip, deflate, zstd` is response-side; the sink answers `200` with an empty
  body and the SDK is happy.
- Body is real protobuf: parsed with `ExportTraceServiceRequest.ParseFromString` → one span,
  `trace_id af5c77d1f83cd5b9cf5b625a813bbd03`, `span_id 55568e44c773902c`, name `one-span`.

**The capture directory, after Ctrl-C** (`find <capture dir> -type f | sort`):

```
captures/probe/2026-10-10T12-00-00Z/MANIFEST.json
captures/probe/2026-10-10T12-00-00Z/json/0001.headers.json
captures/probe/2026-10-10T12-00-00Z/json/0001.json
captures/probe/2026-10-10T12-00-00Z/raw/0001.body
captures/probe/2026-10-10T12-00-00Z/raw/0001.headers.json
```

`MANIFEST.json`, pretty-printed (project manifest elided to the two fields that matter for (B)):

```json
{
  "bodies": [
    {"bytes": 283, "content_encoding": null, "content_type": "application/x-protobuf",
     "file": "raw/0001.body",
     "sha256": "d5ff05d44a27436afcd08a7febb5ad7f274616746a073b57054355f6363c642d"},
    {"bytes": 657, "content_encoding": null, "content_type": "application/json",
     "file": "json/0001.json",
     "sha256": "920b52f20395862484a5ec4b0688e74c1304fe178da728fd47c1abb1221b7c2d"}
  ],
  "collector_version": "0.162.0",
  "ended_at": "2026-10-09T22:31:14.080666+00:00",
  "forwards": [{"file": "raw/0001.body", "status": 200}],
  "kind": "recorded",
  "project_manifest": {"...": "...", "model": "stub-model-1", "mode": "recorded"},
  "sink_version": "0.0.1",
  "started_at": "2026-10-09T22:26:01.673544+00:00"
}
```

`json/0001.json` is valid OTLP JSON (`{"resourceSpans": [...]}`), and the ids match the raw
protobuf **exactly**: `traceId af5c77d1f83cd5b9cf5b625a813bbd03`, `spanId 55568e44c773902c`,
`name one-span`, `service.name: probe`. The raw body's 32-byte trace id and 16-byte span id are
present as raw bytes inside `raw/0001.body` (checked by substring, independently of the parse).
`json/0001.headers.json` records the Collector's own POST: `User-Agent: OpenTelemetry Collector
Contrib/0.162.0 (linux/amd64)`, `Content-Type: application/json`, 657 bytes.

`make verify` → exit **0**, and `make check` → exit **0** in 5.6s with the real capture in the
tree (121 tests, including the Collector integration test, since the binary is present).

**Verdict:** the shipped flow produces a correct, verifiable capture on the first try, with one
real export from a stock SDK, and the two commands that are mistyped in the README are both
caught by an argument-parser refusal rather than by a half-made capture.

---

### (A) README vs. actual behaviour

| # | README | What it says | What actually happens | Bin |
|---|---|---|---|---|
| R1 | L55-58 | ```make collector``` / ```zoo capture --project z4 --run-id 2026-10-09T12-00-00Z``` — the "The tee" code block, the first `zoo capture` an operator meets | **Does not run.** Typed verbatim: `zoo capture: error: the following arguments are required: --kind, --project-manifest`, exit 2. The two required flags are introduced 65 lines later (L122-124). An operator reading top to bottom copies L57 first. | `blocks run 2` |
| R2 | L93-96 | ```zoo verify captures/z4/2026-10-09T12-00-00Z``` as the "one run" example | Works as a **form**, but the path shown is the path L42/L57 would have created, and L42 (`zoo sink`) creates a run dir with **no `MANIFEST.json`** — so following L42 then L95 gives `! no readable MANIFEST.json`, exit 1. See R3. | `thread` |
| R3 | L42 + L98 + L164-165 | `zoo sink --port 4318 --out captures/z4/<run>/raw`, and "`zoo verify` exits 0 on a tree with no captures", and "`make check` depends on it, so from now on every run of the gates re-checks this capture's bytes" | **A `zoo sink` run that received no POST permanently reddens `make check`.** I ran L42 exactly, stopped it with no traffic, and it left `captures/z4/<run>/raw/` with nothing in it. `make verify` → `! captures/z4/2026-10-09T12-00-00Z: no readable MANIFEST.json`, `make verify EXIT 2`, `make: *** [Makefile:37: verify] Error 1`. The only fix is deleting the directory, which the README never mentions. | `next batch` |
| R4 | L109 "**Five commands, in two terminals**" | five commands | **Six.** L113 requires `uv sync --extra dev` first, and it is prose rather than one of the numbered five. Also the `uv run` prefix appears on `zoo capture`/`zoo verify` (L122, L166) but **not** on `make collector`/`make verify`, which is correct but reads as an inconsistency. | `thread` |
| R5 | L70-71 "the ~100 MB binary is gitignored"; L204 "nothing in CI downloads 100 MB" | ~100 MB | The **download** is ~100 MB; what lands on disk is **407,498,914 bytes (389 MiB)**. An operator on a small disk is under-warned by ~4x. The ~100 MB figure is in the right ballpark for the tarball only. | `thread` |
| R6 | L146-148 ("Once per machine") | nothing about how long | **5.9 s** on this machine. The README prepares the operator for the *size* (L70) but not for the *time*, and does not say the figure is the compressed download. No action needed beyond R5. | `thread` (merge with R5) |
| R7 | L150-151 "It prints **one line per recorded body as it arrives**" | live progress | **True on a TTY, false everywhere else.** Under `script -qf` the lines appeared ~instantly: `  raw/0001.body  283 bytes  sha256:a002d6669409` / `  json/0001.json  657 bytes  sha256:416b937f6f43`, 5 s before I stopped it. With stdout redirected to a file, **6 seconds after the export landed** the log still held only the four banner lines; both body lines appeared only at shutdown. The four banner lines *are* flushed (they stream through a pipe at T0+0.414s) — so the flushing is **inconsistent**: banner flushed, per-body lines not. A supervisor tailing a capture log sees no progress. | `next batch` |
| R8 | L159-163 "Ctrl-C ends the capture … The exit status is non-zero if any body failed to reach the Collector — the capture is intact either way and the manifest says which bodies those were" | | **Verified, exactly as written.** `kill -9`'d the Collector mid-run, exported, Ctrl-C'd: `! raw/0001.body recorded, NOT forwarded: ConnectionRefusedError: [Errno 111] Connection refused` / `1 forward(s) FAILED -- json/ is incomplete and MANIFEST.json says which (SPEC.md section 4.4)`, **`CAPTURE_EXIT=1`**, `forwards: [{"error": "TimeoutError…"/"ConnectionRefused…", "file": "raw/0001.body"}]`, body + headers + digest all on disk. README **right**. | — |
| R9 | L72-73 "`zoo capture` refuses to start if the binary reports a version that is not the pin"; SPEC §4.6 "refuses … when the Collector does not accept a connection within the readiness budget" | a dead Collector is a refusal | **The readiness probe is satisfied by a *foreign* listener on the Collector's port.** Reproduced: a 6-line Python dummy holding `127.0.0.1:4320`, then `zoo capture --collector-port 4320 --port 14318 --json-port 14319 --collector-grpc-port 14317`. The Collector printed `Error: cannot start pipelines: failed to start "otlp" receiver: listen tcp 127.0.0.1:4320: bind: address already in use` and went `<defunct>` — and `zoo capture` printed **`zoo capture: collector 0.162.0 up, re-encoding to JSON`** and `the raw bytes are the record. Ctrl-C to stop.` and recorded for 25 s with no Collector at all. Final state: 1 body in `raw/`, `json/` **empty**, forward `TimeoutError: timed out`. This is the exact failure SPEC §4.6 says the refusal exists to prevent ("a capture *silently* missing its `json/`"), and it is the one way the operator can be lied to. The saving grace: the per-body `!` line and the `1 forward(s) FAILED` summary do tell the truth at the end. | `blocks run 2` |
| R10 | L109 "`<run-id>` is yours to choose"; SPEC §4.6 "`--project` … `z1` … `z6`"; `--help`: "z1 ... z6 (SPEC 2.1)" | a project id from the brief list | **`--project probe` was accepted without comment** and created `captures/probe/…`. Neither the README nor the help says the list is advisory. Either enforce it or stop printing it as a constraint. | `thread` |
| R11 | L180-182 "A run directory is never reused … pointing a capture at a directory that already holds part of one is refused **by name**" | | **Verified and the message is excellent:** `zoo capture: refusing to start: captures/probe/2026-10-10T12-00-00Z/json already holds 1 body file(s) and 1 headers file(s) from an earlier capture, starting 0001.json. A run directory is never reused and a capture is never edited (SPEC.md section 2.1): use a new run id.` exit 2. README **right**. But a run dir holding **only** a `MANIFEST.json` (what a refusal leaves behind, §Task 5) **is** re-used silently — see T5-2. | — |
| R12 | L45-51 "A POST to any other path is answered `404` and recorded anyway, under `rejected/`" | | **Verified.** `curl -X POST .../v1/metrics` → `HTTP 404`, and `rejected/0001.body` + `rejected/0001.headers.json` appeared and were listed in `bodies` as `rejected/0001.body`. README **right**. | — |
| R13 | L172-178 "The project's `MANIFEST.json` must already exist when the capture starts … The capture copies what is there when it starts" | | **Verified empirically — see (B).** README **right**, and precisely worded. | — |
| R14 | L61-66, L98-105, L241-246 (tee topology, both-directions verify, layout) | | **All verified.** raw on 4318, json on 4319, Collector on 4320/4317; the layout tree matches file for file (plus `json/NNNN.headers.json`, which the Layout block at L241-245 does not list — a reader comparing the block to `find` will see one unlisted name). README **right** apart from that one omitted line. | `thread` |

**Verdict:** the README is substantively accurate and unusually honest about refusals; the one
command that cannot be typed as printed is L57, the one claim that is wrong in practice is L151,
and the one place the *software* contradicts the README's promise of a loud refusal is R9.

---

### (B) When the project manifest is copied

**Copied at the START of the capture. Verified twice, empirically, without reading the code.**

Evidence 1 — it is already in the capture before any body arrives and long before Ctrl-C. With
the capture running, no export yet:

```
$ find captures/ | sort
captures/probe/2026-10-10T12-00-00Z
captures/probe/2026-10-10T12-00-00Z/MANIFEST.json      <-- already here
captures/probe/2026-10-10T12-00-00Z/json
captures/probe/2026-10-10T12-00-00Z/raw
$ python3 -m json.tool captures/probe/2026-10-10T12-00-00Z/MANIFEST.json
{ "bodies": [], "collector_version": "0.162.0", "kind": "recorded",
  "project_manifest": { ...the full project manifest... },
  "sink_version": "0.0.1", "started_at": "2026-10-09T22:26:01.673544+00:00" }
```

`bodies: []`, no `ended_at` — so this is the §5.5 "declaration written first" state, and
`project_manifest` is in it.

Evidence 2 — the mutation test. While the capture was still running I rewrote the source file:
`model: "stub-model-1"` → `"stub-model-2-MUTATED"` plus a new key
`MUTATED_WHILE_CAPTURE_RUNNING: true` (v1 sha256 `1c9687f9…`, v2 sha256 `d89c4b04…`). After
Ctrl-C:

```
landed == v1 (pre-mutation) : True
landed == v2 (post-mutation): False
landed model: stub-model-1
landed has MUTATED key: False
```

Evidence 3 (unasked-for, free) — every capture I started *after* the mutation carried **v2**,
including the one whose own start failed on a held port (`captures/probe/2026-10-10T12-30-00Z`
holds `"model": "stub-model-2-MUTATED"`). So the copy tracks the moment `zoo capture` starts and
nothing later.

**Verdict:** the "is" half of the WORKPLAN's open decision is settled — the copy is taken at the
start, matching `SPEC.md` §5.3 and §5.5 and README L176-178, and the capture therefore carries
the project's *previous* run's manifest. I take no position on the "should" half, but note one
thing an operator hits: the refused second attempt at a held port also copies the manifest, so a
stale `project_manifest` can exist in a directory that never recorded a byte (§Task 5).
`blocks run 2` only in the sense the WORKPLAN already says: Z4's first real run will carry its
recorded run's manifest unless the maintainer decides otherwise.

---

### (C) The readiness line

`zoo capture` prints, in this order, each flushed as it happens:

```
zoo capture: json sink on http://127.0.0.1:4319 -> captures/probe/<run>/json/
zoo capture: collector 0.162.0 up, re-encoding to JSON
zoo capture: recording POST /v1/traces on http://127.0.0.1:4318 -> captures/probe/<run>/raw/
zoo capture: the raw bytes are the record. Ctrl-C to stop.
```

`zoo sink` prints:

```
zoo sink: recording POST /v1/traces on http://127.0.0.1:4318
zoo sink: bodies to captures/z4/2026-10-09T12-00-00Z/raw/, anything else to captures/z4/2026-10-09T12-00-00Z/rejected/
zoo sink: it parses nothing. Ctrl-C to stop.
```

The confusable pair is real: **`recording POST /v1/traces on http://127.0.0.1:4318` is a
substring of both**, so `grep -m1 'recording POST'` matches either program. They differ only by
the `zoo capture:` / `zoo sink:` prefix and the trailing ` -> <dir>/`. Both end with
`Ctrl-C to stop.`, so that is confusable too.

Timing, measured (`T0` = fork of the `zoo capture` process; port times are the first successful
`connect()` from a polling loop; line time is when the line was readable in the output):

| run | T0 | 4319 json | 4320 collector | 4318 raw | ready line |
|---|---|---|---|---|---|
| pty-1 | 153.535 | +0.268 | +0.386 | +0.473 | +0.465 |
| c2 | 295.440 | — | — | — | +0.445, and at that instant `connect 4318/4319/4320: OK` for all three |

In `pty-1` the ready line and 4318 are 8 ms apart, which is inside my loop's noise (the loop
forks `date` per sample). The decisive test is `c2`: the instant the line matched, a Python
`socket.create_connection` to all three ports succeeded, and a real stock-SDK export immediately
after returned `force_flush -> True` and was recorded. So on the three criteria:

- **(i) appears exactly once** — yes, one occurrence in every run log I collected.
- **(ii) only after every port is genuinely accepting** — yes for the sockets, with the
  caveat that it is *measured* rather than *guaranteed*; I found no case where an export right
  after the line failed. **But "collector up" can be a lie** (§(A) R9): the line can appear while
  the Collector is dead and a foreign process holds 4320. So the line means "all three sockets
  accept", not "the Collector is up".
- **(iii) cannot be confused with `zoo sink`** — yes, *if* you anchor on `zoo capture:` or grep
  the distinctive tail `the raw bytes are the record`, which never appears in `zoo sink`'s
  banner. An unanchored `recording POST` grep is ambiguous and should not be used.

**The one-liner must not use `grep -m1` on a pipe.** I ran the obvious thing:

```
uv run zoo capture ... | grep -m1 'the raw bytes are the record' && echo MATCHED
```

grep matched and exited, closing the pipe, and at shutdown `zoo capture` died with an
**unhandled traceback**:

```
Traceback (most recent call last):
  File ".../spanweave_zoo/cli.py", line 259, in run_capture
    print("\nzoo capture: stopping", flush=True)
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored while flushing sys.stdout:
BrokenPipeError: [Errno 32] Broken pipe
```

and `captures/probe/c1/MANIFEST.json` was left **without `ended_at`** — an unfinished manifest
that `zoo verify` then reports as `0 problem(s)`. So the natural idiom both kills the capture and
leaves a manifest the zoo's own completion step never ran on. `next batch`.

**The one-liner that works** (verified: matched at T0+0.445 s, all ports accepting, export
succeeded):

```bash
uv run zoo capture --project z4 --run-id <id> --kind real \
                   --project-manifest ../streaming-concierge/MANIFEST.json > capture.log 2>&1 &
timeout 30 bash -c 'until grep -q "^zoo capture: the raw bytes are the record" capture.log; do sleep 0.1; done' \
  || { echo "capture did not come up"; exit 1; }
```

**Verdict:** a script *can* wait on `zoo capture`, but only via a log file and an anchored
`until grep -q`, never via `| grep -m1` (which SIGPIPEs the capture into a traceback and an
unfinished manifest). The line `zoo capture: the raw bytes are the record. Ctrl-C to stop.` is
already unique, once-only and correctly placed; what it needs is (a) a documented machine-readable
form — my suggestion: one final line `zoo capture: ready port=4318 json-port=4319 collector-port=4320
run=<capture dir>`, stable and grep-anchored, named in the README as *the* line to wait on — and
(b) a `BrokenPipeError` guard so a reader that stops reading does not take the capture down. `thread`
for the wording, `next batch` for the SIGPIPE.

---

### Task 5: a second capture on a held port

With the first capture holding 4317/4318/4319/4320, a second `zoo capture` with a different
`--run-id` and the stock ports:

```
$ uv run zoo capture --project probe --run-id 2026-10-10T12-30-00Z --kind recorded \
                     --project-manifest <scratchpad>/pet-probe/MANIFEST.json
zoo capture: refusing to start: [Errno 98] Address already in use
### EXIT CODE: 2
```

- **It is a clean refusal, not a traceback.** `zoo capture: refusing to start: [Errno 98] Address
  already in use`, exit **2**, one line. The operator can tell a held port from a bug. `Errno 98 /
  Address already in use` is exactly what the claim said. Good.
- **The error does not name the port, the host, or which of the three listeners collided.** On a
  machine where any of 4318/4319/4320 might be taken by something else, the operator has to guess
  which one. `next batch` — one f-string.
- **It does NOT record nothing. The claim's second half is false.**

```
### find captures/ -type d BEFORE
captures/probe/2026-10-10T12-00-00Z{,/json,/raw}
### find captures/ -type d AFTER
captures/probe/2026-10-10T12-00-00Z{,/json,/raw}
captures/probe/2026-10-10T12-30-00Z          <-- created
captures/probe/2026-10-10T12-30-00Z/json     <-- created
### find captures/ -type f AFTER
captures/probe/2026-10-10T12-00-00Z/MANIFEST.json
captures/probe/2026-10-10T12-30-00Z/MANIFEST.json   <-- written
```

  The leftover is half-populated: the run dir, an empty `json/` (no `raw/`), and a **labelled
  `MANIFEST.json`** carrying `kind`, `collector_version`, `sink_version`, `started_at` and the
  full `project_manifest` copy, with `bodies: []` and no `ended_at`. SPEC §5.1 says both new
  options are refused "before anything is started **and before a directory is made**" and §5.5
  says "a capture that never got as far as a labelled manifest is left with nothing written at
  all" — the directory and the label are both made before the first bind, so a *port* refusal
  lands after both. `blocks run 2`: the brief's claim is not what ships.
- **Which port.** It collided on **4319, the json sink** — the first listener started. Proven by
  attribution runs with only one port held at a time (the others moved to 14317-14319):

| held port | output | leftover shape |
|---|---|---|
| 4318 (raw) | refused, *after* printing `json sink on http://127.0.0.1:14319` and `collector 0.162.0 up` | `MANIFEST.json` + `json/` + `raw/` |
| **4319 (json)** | refused with **no banner line at all** | **`MANIFEST.json` + `json/`** |
| 4320 (collector HTTP) | **did not refuse** — false readiness, see (A) R9 | `MANIFEST.json` + `json/` + `raw/` |
| 4317 (collector gRPC) | refused with a good message: `the Collector exited with 1 before it listened on 127.0.0.1:14320. Its own log is above: the config it was given is collector/config.yaml.` | `MANIFEST.json` + `json/` |

  The task-5 leftover's shape (`MANIFEST.json` + `json/`, no `raw/`) and its silence match the
  4319 row exactly.
- **Does the leftover poison anything later?** Two answers, both tested.
  - `zoo verify` / `make verify` **count it as a verified capture**:
    `captures/probe/2026-10-10T12-30-00Z: kind=recorded, 0 body/bodies, 0 problem(s)` and
    `zoo verify: 2 capture(s) under captures/`, exit **0**. So a never-recorded attempt is
    reported, forever, as a clean capture — and the audit (§7), which is organised by `kind`,
    will find a `kind=recorded` capture with no bytes in it. `next batch`.
  - Re-using the leftover run id is **allowed**, not refused. The WORKPLAN's 2026-10-10 A3 note
    ("a directory holding only a headers file is refused") does not cover a directory holding only
    a `MANIFEST.json`: I re-ran the capture with `--run-id 2026-10-10T12-30-00Z`, it started, and
    it overwrote the stale manifest with a live one. That is a mitigation for the operator (retry
    with the same id works) and a second reason the stale manifest is a liability rather than a
    blocker.

**Verdict:** the refusal is clean and the exit code is right, but "records nothing" is wrong — a
run directory, an empty `json/` and a fully labelled `MANIFEST.json` (with a stale
`project_manifest` copy) are left behind, `zoo verify` then blesses that directory as a verified
capture, and the error names neither the port nor the sink it collided on.
