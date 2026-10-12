## A2 — 8c8299f (the Collector re-encodes beside the raw)

Reviewed commit `8c8299fe6af8c4c290dff3b4bf845e2f92209f7d`, batch A2.
Derived parent: `git rev-parse 8c8299f^` → **`01da2fb9aa188723c00d052916f07b1162e8c658`**
(`plan: A1 done, and the tee's two sinks need separate out directories` — a
`plan:` commit, as §0.2 warns).

Worktrees: `/tmp/claude-1000/.../scratchpad/wt-a2` and `.../wt-a2-parent`
(absolute, under the scratchpad, outside the repo). The repo's own working tree
was not touched: it is still `zoo` at `b913e2b`, `git status --porcelain` empty,
before and after.

### Hygiene

**Spec-first — holds, and visibly.** At the parent, `SPEC.md` §4 was an explicit
placeholder:

```
## 4. The Collector — A2
...
byte-identical forward from the raw sink. Not specified yet.
```

This commit replaces it with §4.1–§4.9 (+295 lines of `SPEC.md`) in the same
commit as `spanweave_zoo/capture.py`, `collector.py`, `forward.py` and the
`sink.py` changes. I checked §4.6 against the shipped CLI at *this* commit
rather than at HEAD: §4.6's option table lists exactly `--project --run-id
--captures --port --json-port --collector-port --collector-grpc-port --host
--collector-dir --forward-timeout`, and `zoo capture --help` at 8c8299f prints
exactly those ten. (`--kind` / `--project-manifest` appear in §4.6 only at HEAD;
they are A3's, and A2 did not pre-specify them.)

**The SIGINT fix is one concern, not a second smuggled in.** I checked this
rather than taking the plan's word for it. `git show 8c8299f -- spanweave_zoo/cli.py`
contains **no `-` lines** in the signal/wait area — `STOP_SIGNALS`,
`_stop_on_signal`, `_restore_signals` and the `serve_forever` short-hop wait are
all additions, and nothing in A1's `zoo sink` serve path was modified.
`zoo capture` is new in this commit, so the SIGINT defect existed only inside
this batch's own unreleased draft; fixing it is part of making the batch's one
command work, and `SPEC.md` §4.6 specifies it in the same commit.
CONTRIBUTING.md's "a drive-by fix noticed on the way is a second commit" is
about a pre-existing defect in other code, which this is not. **Judgement: one
concern.** It is also the right call editorially — a `zoo capture` that cannot
be stopped would have shipped a batch whose own acceptance command does not
work.

**CHANGELOG entry** — present, under `## A2 — the Collector re-encodes beside
the raw`, ~15 bullets including the SIGINT item and the two named mutations.

**No clock, randomness or network outside the named seams.** Grepped the whole
package:

```
spanweave_zoo/forward.py:32:import http.client
spanweave_zoo/collector.py:24:import os
spanweave_zoo/collector.py:25:import socket
spanweave_zoo/collector.py:26:import subprocess
spanweave_zoo/cli.py:31:import signal
spanweave_zoo/cli.py:33:import time
spanweave_zoo/cli.py:35:from datetime import UTC, datetime
```
and the only call sites: `cli.py:61 datetime.now(UTC).isoformat()`,
`cli.py:71 time.sleep(seconds)`. No `random`, `secrets`, `uuid`, `os.urandom`.
The outbound forward is **`http.client`**, inside `forward.HttpForward`, which
is the `forward` seam SPEC §4.8 names — **not** `requests` or `httpx`, which
CLAUDE.md forbids. `collector.py`'s `socket.create_connection` is the readiness
probe inside the `launch` seam, and it is attempt-counted rather than
clock-bounded (`collector.py:45`: "attempts, not a deadline, because a deadline
needs a clock"), with the pause taken through the injected `sleep`. `urllib` is
confined to `collector/fetch.py`, deliberately outside the package.

**Ports — no contention.** No test in the batch binds 4317–4320. Every sink in
the suite uses `make_server(..., port=0)`; `test_collector_real.py` uses its own
`free_port()` helper for the Collector and `raw_port=0 / json_port=0` for the
sinks. **Every test ran cleanly; none was skipped or re-run for port reasons.**
The one `[Errno 98]` I hit was in *my own* driver on 44317–44320, which fall
inside this machine's ephemeral range (`/proc/sys/net/ipv4/ip_local_port_range`
= `32768 60999`); I moved my driver to 24317–24320 and it was clean. That is my
environment, not a defect, and not a finding.

**The derived-parent run — vacuous, and the commit says so.** In
`wt-a2-parent` (at `01da2fb`) I copied in A2's four new test files and ran them:

```
collected 0 items / 3 errors
tests/test_tee.py:25: in <module>
    from spanweave_zoo import cli, forward, manifest, sink
E   ImportError: cannot import name 'forward' from 'spanweave_zoo'
tests/test_capture.py:23: ImportError: cannot import name 'capture' from 'spanweave_zoo'
tests/test_collector_real.py:34: ImportError: cannot import name 'capture' from 'spanweave_zoo'
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
```

Collection/import errors, **not** assertion failures: the parent run is
vacuous and proves nothing about behaviour. The commit body states this
accurately and in the right words ("Parent run (`01da2fb`, derived): vacuous")
and leans on mutations instead, which is what §0.2 requires. No complaint.

**Gates.** `make check` green in `wt-a2` with the real binary present:
`94 passed in 2.42s`, **0 skipped** (so the three real-Collector tests actually
ran), `zoo verify: no captures under captures/ -- nothing to re-hash`,
`zoo 0.0.1`. `make install-check` green: `install-check: OK -- what ships works`.

**Row claims — all four verified against the files.**
- `collector/config.yaml` uses `otlp_http` (not the deprecated `otlphttp`) with
  `encoding: json`: confirmed, and `exporters: [otlp_http]` / `encoding: json` /
  `compression: none` are asserted as text by
  `tests/test_capture.py:157 test_the_pinned_config_is_stock_and_re_encodes_to_json`.
- Endpoints are `${env:NAME:-default}` with defaults 4317 / 4318 / 4319:
  confirmed — `ZOO_COLLECTOR_OTLP_GRPC:-127.0.0.1:4317`,
  `ZOO_COLLECTOR_OTLP_HTTP:-127.0.0.1:4318`,
  `ZOO_JSON_SINK:-http://127.0.0.1:4319`. The real binary accepted this file
  unedited, so the confmap `${env:...}` form is not aspirational.
- `zoo capture` moves the Collector's HTTP receiver to 4320: confirmed,
  `capture.py:49 DEFAULT_COLLECTOR_PORT = 4320`, and `--collector-port`
  defaults to 4320 in `--help`.
- The pin is **0.162.0** (`collector/VERSION`, one line, no `v`): confirmed.

**The sha256 is actually checked, and I proved it rather than reading it.**
`collector/fetch.py:main` downloads to a temp dir, computes `digest_of`,
compares against the `SHA256SUMS` line, and `raise SystemExit` **before**
`extract()` is reached. Real run:

```
collector: otelcol-contrib 0.162.0 for linux_amd64
  fetching https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.162.0/otelcol-contrib_0.162.0_linux_amd64.tar.gz
  sha256 fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3 matches collector/SHA256SUMS
collector: .../collector/otelcol-contrib ready (gitignored -- the pin is the record)
```
`otelcol-contrib --version` → `otelcol-contrib version 0.162.0`. Then I flipped
one hex digit of the linux_amd64 line and re-ran:

```
collector: REFUSING to unpack otelcol-contrib_0.162.0_linux_amd64.tar.gz.
  expected sha256 0cc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3  (collector/SHA256SUMS)
  downloaded       fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3
The pinned digest is the release's own. These are not the bytes that were pinned.
make: *** [Makefile:50: collector] Error 1   (EXIT=2)
```
and `ls collector/` afterwards held only `config.yaml fetch.py SHA256SUMS
VERSION` — nothing was unpacked. The check is live, and it gates extraction.

#### Finding H1 — a refused `zoo capture` writes a run directory and a manifest, which SPEC §4.6 says it does not

**Claim:** SPEC §4.6, written in this commit, says `zoo capture` "**refuses to
start**, writing nothing, when: … or the Collector does not accept a connection
within the readiness budget." It does write. `capture.py:166-167` does
`self.run.mkdir(parents=True, exist_ok=True)` and
`manifest.set_collector_version(self.run, version)` *before*
`capture.py:183 self._launcher.start(...)`, so every refusal after the version
check leaves the run directory behind.

**Evidence** — the spec's own listed refusal, driven for real:

```
$ uv run zoo capture --project z4 --run-id readiness-refusal --captures $R \
    --port 24318 --json-port 24319 --collector-port 1 --collector-grpc-port 24317
Error: cannot start pipelines: failed to start "otlp" receiver: listen tcp 127.0.0.1:1: bind: permission denied
zoo capture: refusing to start: the Collector exited with 1 before it listened on 127.0.0.1:1.

$ find $R
.../z4/readiness-refusal
.../z4/readiness-refusal/json
.../z4/readiness-refusal/MANIFEST.json

$ cat .../z4/readiness-refusal/MANIFEST.json
{
  "bodies": [],
  "collector_version": "0.162.0"
}
```

`tests/test_capture.py:136 test_capture_refuses_a_collector_that_does_not_report_the_pin`
asserts `assert not run.exists()` — but only for the version-mismatch refusal,
which is the one refusal that happens *before* the `mkdir`. The other refusals
§4.6 enumerates are unguarded in that direction. I also confirmed the ordering
is unchanged at repo HEAD (`capture.py` start: `check_version` → `mkdir` →
`manifest.label` → json sink → `launcher.start`), where A3 made the leftover
*more* assertive: the orphan manifest now also carries `kind` and
`project_manifest`, i.e. a directory that claims to be a `real` capture of
nothing. Nothing lies about bytes (`bodies: []`), so this is a spec-vs-code
mismatch and an operator-ergonomics wart, not a capture-integrity break — but
the spec sentence is this commit's own and it is false as written.
**Bin: `next batch`** (either the write moves after readiness, or §4.6 stops
saying "writing nothing").

#### Finding H2 — `.gitignore`'s A2 line was pre-added in A0

**Claim:** `.gitignore` is not in 8c8299f's diffstat, yet it already carries
`collector/otelcol-contrib` / `collector/*.tar.gz` under the comment "The
Collector binary `make collector` fetches (A2)". `git log --follow -- .gitignore`
returns only `d33059e` (A0). So A0 pre-specified a later batch's artifact, which
is the shape CLAUDE.md's "a section belonging to a later batch stays an empty
heading rather than a guess" exists to prevent — applied to `SPEC.md`, not to
`.gitignore`, so this is at most a letter-of-the-rule note. The commit body's
claim "the ~100MB binary is gitignored" is true; it just was not made true here.
**Bin: `thread`.**

#### Note — the manifest-equals-VERSION test guards the plumbing, not the pin's value

Worth recording so nobody over-reads the row. `test_capture.py:123
test_the_collector_version_in_the_manifest_equals_collector_version` compares
`manifest.read(run)[COLLECTOR_VERSION]` against `pinned_version()`, and the
`Capture` under test is built with `FakeLauncher(pinned_version())` and
`pin=collector.pin(COLLECTOR_DIR)` — **both sides read `collector/VERSION`**, so
editing that file moves both and the test still passes (I confirmed: it was not
among the three failures for mutation (iii)). It is not vacuous, though: I
proved it guards the code path with a fourth mutation (below). The *value* of
the pin is independently held by
`test_every_pinned_platform_has_a_digest_for_the_pinned_version`, which cross-checks
`VERSION` against `SHA256SUMS` and is the test that fails in CI without the
binary. The two together are sound. No bin.

### Claim: identical trace and span ids through the real Collector

Verified, with the real binary, on my own ports, and I extracted the ids myself
rather than trusting `test_collector_real.py`'s assertions.

I drove `zoo capture` as an operator would — 24318 raw / 24319 json / 24320
collector HTTP / 24317 grpc — POSTed a 128-byte hand-built OTLP protobuf to
`/v1/traces`, waited for `json/0001.json`, then `SIGINT`:

```
POSTing 128 bytes of protobuf to 127.0.0.1:24318/v1/traces
  sink answered 200
zoo capture: json sink on http://127.0.0.1:24319 -> .../aux-review-2/json/
zoo capture: collector 0.162.0 up, re-encoding to JSON
zoo capture: recording POST /v1/traces on http://127.0.0.1:24318 -> .../aux-review-2/raw/
  raw/0001.body  128 bytes  sha256:abb3460ed377
  json/0001.json  391 bytes  sha256:403f27e12d26
zoo capture: stopping
zoo capture: 2 body/bodies under .../aux-review-2/
--- exit code: 0
```
(`SIGINT` did stop it and exit 0 — the §4.6 fix works against the real binary.)

**The raw side is protobuf, not JSON.** `raw/0001.body` is 128 bytes beginning
`b'\n~\n!\n\x1f\n\x0c'` and does not decode as UTF-8, let alone as JSON. I then
walked it with my own varint/wire-type decoder (no repo import, no protobuf
library) down `ExportTraceServiceRequest.resource_spans=1 →
ResourceSpans.scope_spans=2 → ScopeSpans.spans=2 → Span{trace_id=1, span_id=2,
name=5}`.

**The JSON side is valid OTLP JSON.** `json/0001.json` parses with stdlib
`json`, top-level keys `['resourceSpans']`, and its headers record
`Content-Type: application/json` with no `Content-Encoding` (so
`compression: none` is doing its job), `User-Agent: OpenTelemetry Collector
Contrib/0.162.0 (linux/amd64)`.

**The ids, extracted independently from each side:**

```
raw/0001.body  128 bytes  first 8 = b'\n~\n!\n\x1f\n\x0c'
  not JSON (UnicodeDecodeError) -> consistent with protobuf
  decoded by hand from the wire format:
    traceId=4bf92f3577b34da6a3ce929d0e0e4736  spanId=00f067aa0ba902b7  name='GET /checkout'

json/0001.json  valid OTLP JSON, top-level keys = ['resourceSpans']
  read straight out of the Collector's JSON:
    traceId=4bf92f3577b34da6a3ce929d0e0e4736  spanId=00f067aa0ba902b7  name='GET /checkout'

protobuf side == JSON side : True
```

trace id `4bf92f3577b34da6a3ce929d0e0e4736`, span id `00f067aa0ba902b7`, equal on
both sides. `zoo verify` re-hashes the result at 0 problems, and `MANIFEST.json`
carries `collector_version: "0.162.0"` and `forwards: [{"file":
"raw/0001.body", "status": 200}]`.

**Mutation (i), shown caught.** I changed `sink.py:205` to forward
`bytes([body[0] ^ 1]) + body[1:]` — one flipped byte, everything else identical:

```
>       assert forwarded == GZIP_BODY
E       AssertionError: assert b'\x1e\x8b\x0...4\x00\x00\x00' == b'\x1f\x8b\x0...4\x00\x00\x00'
E         At index 0 diff: b'\x1e' != b'\x1f'
tests/test_tee.py:142 ...
FAILED tests/test_capture.py::test_both_sinks_write_one_manifest_for_the_run
FAILED tests/test_collector_real.py::test_a_protobuf_export_through_the_tee_comes_back_as_json_with_the_same_ids
FAILED tests/test_tee.py::test_the_forwarded_body_is_the_bytes_that_arrived
FAILED tests/test_tee.py::test_a_protobuf_body_is_forwarded_as_protobuf
FAILED tests/test_tee.py::test_the_http_forward_delivers_the_same_bytes_to_a_real_listener
5 failed, 89 passed
```
Five tests, including the real-Collector integration test. Reverted.

**Mutation (iii), shown caught.** `collector/VERSION` → `0.163.0`:

```
>           assert asset.startswith(f"otelcol-contrib_{pinned_version()}_"), asset
E           AssertionError: otelcol-contrib_0.162.0_linux_amd64.tar.gz
tests/test_capture.py:185
...
E  CollectorRefused: the Collector reports version '0.162.0' but the pin is '0.163.0' (collector/VERSION)
FAILED tests/test_capture.py::test_every_pinned_platform_has_a_digest_for_the_pinned_version
FAILED tests/test_collector_real.py::test_the_binary_on_disk_is_the_pinned_version
FAILED tests/test_collector_real.py::test_a_protobuf_export_through_the_tee_comes_back_as_json_with_the_same_ids
3 failed, 91 passed
```
Caught — by the `SHA256SUMS` cross-check (which is the one that fires in CI,
with no binary) and by both real-binary tests. Reverted.

**Mutation (iv), extra, to settle the note above.** I replaced
`capture.py:167 manifest.set_collector_version(self.run, version)` with a
literal `"0.1.0-whatever"`:

```
FAILED tests/test_capture.py::test_the_collector_version_in_the_manifest_equals_collector_version
FAILED tests/test_capture.py::test_both_sinks_write_one_manifest_for_the_run
FAILED tests/test_collector_real.py::test_a_protobuf_export_through_the_tee_comes_back_as_json_with_the_same_ids
3 failed, 91 passed
```
So the manifest-version test does hold the plumbing — it is tautological only
with respect to the file's value. Reverted.

**Verdict: confirmed.** The ids are identical through the real pinned 0.162.0
binary, and I extracted them from both sides myself.

### Claim: the raw sink writes before it forwards

**From the code.** `spanweave_zoo/sink.py`, `Recorder.record`:

- `sink.py:158` `body_file.write_bytes(body)` — inside `self._lock` (taken at
  `:152`)
- `sink.py:159-168` `manifest.write_json(... NNNN.headers.json ...)`
- `sink.py:169-174` the `BodyEntry` with its sha256, and
  `manifest.append_body(self.run, entry)`
- lock released, then `sink.py:178-179` `if accepted: self._tee(method, path,
  headers, body, entry)`
- `sink.py:205` `status = self._forward(method, path, headers, body)`

So the body, its headers *and* its digest are all on disk and in the manifest
before the socket to the Collector is opened. `sink.py:182-201`'s docstring says
so in the same words as SPEC §4.3 and gives the reason the forward is outside
the lock. Observed in the real run too: `raw/0001.headers.json` has
`received_at 2026-10-09T22:27:15.536015+00:00` and `json/0001.headers.json`
`...15.644539+00:00` (108 ms later), and `MANIFEST.json`'s `bodies` are ordered
`raw/0001.body` then `json/0001.json`.

**Mutation (ii), applied for real, and the suite does catch it.** I moved the
`_tee` call *above* the write — forward first (building the `BodyEntry` the tee
needs up front from the same values), then write — and deleted the post-write
forward:

```
>       assert spy.on_disk == [PROTOBUF], (
            "the body was not on disk, or not complete, when the forward happened"
        )
E       AssertionError: the body was not on disk, or not complete, when the forward happened
E       assert [None] == [b'\n~\n!\n\x1f\n\x0cservice.name\x12\x0f\n\rzoo-synthetic...']
E         At index 0 diff: None != b'\n~\n!\n\x1f...'
tests/test_tee.py:142

FAILED tests/test_tee.py::test_the_body_is_on_disk_before_the_forward_is_attempted
FAILED tests/test_capture.py::test_both_sinks_write_one_manifest_for_the_run
    E AssertionError: assert ['json/0001.json', 'raw/0001.body'] == ['raw/0001.body', 'json/0001.json']
FAILED tests/test_tee.py::test_the_http_forward_delivers_the_same_bytes_to_a_real_listener
3 failed, 91 passed
```

So the invariant is **guarded**, not merely asserted in prose. The mechanism is
`tests/test_tee.py:44 class Spy`, whose `__call__` reads
`raw/NNNN.body` back off disk *at the moment the forward is invoked* and records
`None` if it is not there — which is the right way to test an ordering claim,
because it observes the filesystem from inside the forward rather than checking
final state afterwards. The manifest-order test is a second, independent witness.
The commit body's claim about this mutation is accurate.

Worth knowing: **the real-Collector integration test does *not* catch the swap**
(it was among the 91 that passed). That is expected and is what SPEC §4.9 says —
the integration test proves re-encoding, the seam tests prove mechanics — but it
means the ordering guarantee rests entirely on `test_tee.py`'s seam-level `Spy`.
Fine as designed; just not redundant.

**Is the code actually safe under the failure modes the ordering protects against?**

1. *The forward raises (Collector absent, wedged, or answering an error).* Safe.
   The body, headers and digest are already written and are not touched;
   `sink.py:204-212` catches `Exception` and turns it into a
   `ForwardEntry(file=..., error=...)`, `:215` appends it to the manifest, `:216`
   announces it, and `zoo capture` exits non-zero on
   `Recorder.failed_forwards`. Held by
   `test_a_failed_forward_is_recorded_in_the_manifest_and_the_capture_stands`,
   `test_a_collector_that_answers_an_error_status_is_a_failed_forward`, and
   `test_a_failed_forward_leaves_the_capture_intact_and_exits_non_zero`.
2. *The write itself fails (disk full).* Safe in the right direction:
   `write_bytes` raises inside `record()`, `_tee` is never reached, and nothing
   is forwarded. There is no path that forwards a body it did not record.
3. *The Collector's own POST reaching the json sink before the raw bytes are
   there.* Impossible by construction — the Collector cannot POST what it has
   not received, and it is not sent until after the write. The two sinks are
   separate `Recorder`s with separate locks but share one manifest lock keyed on
   the run directory (`manifest.py`), so the raw entry is appended before the
   json entry as well; verified in the real manifest and asserted by
   `test_both_sinks_write_one_manifest_for_the_run`.
4. *Crash durability.* `write_bytes` writes and closes but does not `fsync`, and
   neither does the manifest append. "On disk" here means *visible to any
   process on the machine* — which is what the invariant needs — not
   *crash-durable*. A kernel panic between the write and the writeback could in
   principle leave a `json/NNNN.json` whose `raw/NNNN.body` is gone. Very low
   stakes, and SPEC §4.3's actual promise ("no arrangement of **failures** in
   which the zoo forwarded something it did not record") is about forward
   failures, which are covered. Recording it only so the word "durable" is not
   read as more than the code does. **Bin: `thread`.**

#### Finding C1 — the exporter's `200` is serialized behind the forward, so a wedged Collector adds the full `--forward-timeout` to every export

**Claim:** `_Handler.do_POST` (`sink.py:243-254`) calls `recorder.record(...)` —
which calls `_tee` **synchronously** at `:179` — and only then `self._answer(...)`
at `:254`. So the exporter's response waits for the forward to finish or time
out. SPEC §4.3 says the answer "does not depend on the bytes and it does not
depend on the forward", which is true of the *status* and false of the
*latency*; SPEC §4.4 says "a recorder that blocks the system it is recording has
changed the thing it was supposed to observe", and it does, by up to
`--forward-timeout` per POST.

**Evidence** — measured against a black-hole listener that accepts and never
answers (a wedged Collector), default 5 s timeout:

```
exporter got 200 after 5.01s (forward timeout is 5.0s)
raw/0001.body on disk: b'xyz'
```

The record-first invariant held (the body is on disk), and the status is
genuinely independent — which is what `tests/test_tee.py:222
test_the_answer_does_not_depend_on_the_forward` asserts: `(status, answer) ==
(200, b"")` plus the echoed content type. It asserts **nothing about latency**,
so this coupling is unguarded by a test. Mitigating, and I checked it: the sinks
are `ThreadingHTTPServer` with `daemon_threads = True`, so concurrent exports
get their own threads and one wedged forward delays only its own POST rather
than queueing the rest. And SPEC §4.4's letter is satisfied — the exporter does
get an answer, because the timeout is bounded. So this is a spec-precision and
test-coverage gap rather than a hang: the 5 s bound is the *observable cost of
recording*, and §4.3/§4.4 do not say so where an operator would read it.
**Bin: `thread`** (say the bound in §4.3 beside "does not depend on the
forward", and consider asserting it).

**Verdict: confirmed.** Write-before-forward holds in the code (`sink.py:158`
write, `sink.py:179` tee), it is guarded by a test that observes the filesystem
from inside the forward, and I showed the swap caught — three failures including
the dedicated `test_the_body_is_on_disk_before_the_forward_is_attempted`. It is
not "asserted in the spec but unguarded".

### Findings, collected

| # | One line | Bin |
|---|---|---|
| H1 | A refused `zoo capture` leaves `<run>/MANIFEST.json` + `json/` although SPEC §4.6 (new here) says it refuses "writing nothing"; only the version-mismatch refusal is tested for it, and the gap is live at HEAD where A3 labels that orphan manifest with `kind` | `next batch` |
| H2 | `.gitignore`'s `collector/otelcol-contrib` line, commented "(A2)", was added by A0 (`d33059e`), not by this commit | `thread` |
| C1 | The exporter's `200` is held behind the forward — measured 5.01 s against a wedged Collector; the status is independent, the latency is not, and no test asserts the bound | `thread` |
| C2 | `write_bytes`/manifest appends are not `fsync`ed, so "on disk" means visible, not crash-durable | `thread` |

Nothing found blocks run 2.
