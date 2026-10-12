## A1 — 69fb6bd (the sink records bytes, and nothing else)

Reviewed cold against `CONTRIBUTING.md` ("The bar"), `CLAUDE.md` §0.6 and
`WORKPLAN.md` §0.2. Derived parent: `git rev-parse 69fb6bd^` →
**`0bdab8e288146a8e5a0ab60128e342a1e7f03fb2`** (`plan: A0 done, and verify
refuses captures until A1 replaces it`), confirming §0.2's premise that
`plan:` commits interleave — the brief-named `d33059e` is A0, one further back.

Worktrees used, both absolute under the scratchpad and both removed afterwards:
`…/scratchpad/wt-a1` (69fb6bd) and `…/scratchpad/wt-a1-parent` (0bdab8e).

### Hygiene

| §0.2 / batch-bar check | Result |
|---|---|
| Spec changed in the same commit as behaviour | **Yes.** `git show 69fb6bd -- SPEC.md` turns the stub `## 3. The sink — A1` into `## 3. The sink` and adds §§3.1–3.7 (+165 lines), plus §2.3/§2.5 and the status line, in the same commit as `spanweave_zoo/sink.py`. |
| New tests red on the **derived** parent | **Partly, and the plan overstates the vacuity** — see finding A1-F1. |
| One mutation shown caught | **Verified, three** — see below. |
| No clock / randomness / network outside a seam | **Verified in the repo's own code**; one stdlib caveat, finding A1-F2. |
| One concern per commit | Yes. Sink + the manifest digest + the `verify` re-hash that digest exists for; the commit body argues why the digest could not be deferred to A3 (`CLAUDE.md` §0.6 rule 2). Message is `<area>: <one line>` with the batch id and the SPEC sections. |
| `CHANGELOG.md` entry | Yes, `## A1 — the sink records bytes, and nothing else`. |
| `make check` | **Green at 69fb6bd**: ruff + `ruff format --check` clean, `mypy --strict` "Success: no issues found in 4 source files", `56 passed in 0.54s`, gates `30 passed`, `zoo verify` "no captures … nothing to re-hash", `zoo 0.0.1`. `make install-check` also green ("install-check: OK -- what ships works"). |

Greps requested by §0.2, run in the A1 worktree:

```
$ grep -rnE "time\.time|datetime\.now|random|hash\(|socket|urllib|requests|httpx" spanweave_zoo/
spanweave_zoo/sink.py:4:better with nothing between it and the socket -- no framework reading the body
spanweave_zoo/sink.py:19:socket, and `before_record` / `after_record` so a test can hold two POSTs in
spanweave_zoo/sink.py:21:module reads a clock, sleeps, or draws a random number.
spanweave_zoo/sink.py:59:    the manifest's entries are in that same order however many requests are in
spanweave_zoo/sink.py:148:    closing the socket.
spanweave_zoo/sink.py:225:    """The listener seam (`SPEC.md` §3.6): the only socket bind in the package.
spanweave_zoo/cli.py:49:    return datetime.now(UTC).isoformat()
spanweave_zoo/cli.py:98:    # The port the socket actually got, which is not `port` when `port` is 0.
```

Every hit but one is prose. The one real hit is `spanweave_zoo/cli.py:49`
`_system_clock` — the `now` seam the plan names. No `random`, no `hash(`, no
`time.time`, no `sleep`, no network import. I verified `received_at` really
comes from the seam two ways: `tests/test_sink.py:…test_the_receipt_time_is_the_injected_clocks_value`
asserts the recorded values are the fake clock's *and* that `clock.ticks == 2`
(one read per request, no hidden second read); and on the live run below
`received_at` values are real wall-clock ISO-8601 strings in exactly
`_system_clock`'s `datetime.now(UTC).isoformat()` spelling.

#### A1-F1 — the derived-parent run is vacuous for `test_sink.py` only; two of A1's other new tests fail there by assertion. `thread`

`WORKPLAN.md` §4 (2026-10-09 A1, process) says the batch checked `d33059e`
instead of `0bdab8e` and that "both runs are vacuous". I reproduced both halves.

`tests/test_sink.py` copied into the parent worktree:

```
ERROR collecting tests/test_sink.py
E   ImportError: cannot import name 'manifest' from 'spanweave_zoo'
=========================== short test summary info ============================
ERROR tests/test_sink.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

So **vacuous, as claimed**: zero assertions ran, nothing was held — the module
cannot import because `spanweave_zoo/manifest.py` and `sink.py` do not exist at
`0bdab8e` (`git ls-tree -r --name-only 0bdab8e` lists only `__init__.py`,
`cli.py`, `py.typed`). The same would have been true of `d33059e`, so the
batch's wrong-sha run reached the same (uninformative) answer by luck.

But A1 also changed `tests/test_cli.py`, and *that* file's run on the derived
parent is **not** vacuous — A1's version of it on `0bdab8e`:

```
FAILED tests/test_cli.py::test_verify_refuses_a_capture_with_no_manifest - As...
FAILED tests/test_cli.py::test_the_only_clock_in_the_package_is_the_sinks_now_seam
2 failed, 4 passed in 0.05s
```

and the second fails on a real assertion about the seam, not on an import:

```
>       assert offenders, "the clock seam's implementation went missing from cli.py"
E       AssertionError: the clock seam's implementation went missing from cli.py
E       assert []
```

So the plan's §4 line is right about the batch's process error and about
`test_sink.py`, and **over-claims** when it says the whole parent run was
vacuous and "the named mutation is what carried the bar". Two of A1's new tests
do discriminate the parent. This is a plan-text correction, not a code defect —
bin `thread` (for the builder, when §4 is folded into `TASKS.md` at A6).

#### A1-F2 — the sink's *answer* carries a `Date` header from the stdlib's real clock, which the AST clock gate cannot see. `thread`

`spanweave_zoo/sink.py:220` calls `self.send_response(status)`, and
`BaseHTTPRequestHandler.send_response` emits `Server:` and `Date:` — the latter
from `date_time_string()`, i.e. `time.time()` inside `http.server`. Observed on
every one of my nine live probes:

```
    status  : 200 OK
    headers : [('Content-Length', '0'), ('Content-Type', 'application/x-protobuf'), ('Date', 'Fri, 09 Oct 2026 22:25:58 GMT'), ('Server', 'zoo-sink ')]
```

This does **not** break anything the spec claims: no clock value enters the
*record* (`received_at` is the seam's), and §3.3's claim is about status, body
and echoed content type. It is worth a thread for two reasons: (1) the gate
test `test_the_only_clock_in_the_package_is_the_sinks_now_seam`
(`tests/test_cli.py`) walks the AST of `spanweave_zoo/*.py` only, so it would
never notice a clock reaching the wire through a stdlib call — the invariant it
asserts is narrower than the sentence in `SPEC.md` §3.6 ("The sink never reads
the clock, never sleeps, never binds a socket … outside these"); (2) it means
the answer is invariant in *shape* but not in *bytes*, which matters when A4's
replayer and A5's audit start comparing responses. Also cosmetic: `Server:
zoo-sink ` has a trailing space (`sys_version = ""` plus `version_string()`'s
separator).

#### A1-F3 — `NNNN.headers.json` is the stdlib's *parse* of the header block, not the header bytes; `SPEC.md` §2.3's "every header as received … unmodified" is stronger than what happens. `thread` / `next batch` (A4)

`SPEC.md` §2.3 and §3.2 promise "every header as received (names and values
unmodified)". What is recorded is `list(self.headers.items())`, i.e. what
`http.client`/`email.parser` made of the bytes. I probed three malformed header
blocks against a live sink and read back `headers.json`:

| sent on the wire | recorded in `headers.json` |
|---|---|
| `Content-Type: application/json\r\n\tX-Injected: yes` (obs-fold) | `['Content-Type', 'application/json\r\n\tX-Injected: yes']` — fold preserved, one header |
| `Content-Type: application/json\rX-Injected: yes` (bare CR) | `['Content-Type', 'application/json'], ['X-Injected', 'yes']` — **split into two headers the exporter never sent as two** |
| `Content-Type: a\x00\x01b` | `['Content-Type', 'a\x00\x01b']` — control bytes kept |

The bare-CR row is the interesting one. The record now asserts an
`X-Injected: yes` request header; §1.2 ("a capture is what the exporter sent")
and §2.3 both read as stronger than that. §3.7 already concedes the same shape
of limit for framing ("what it could see is what the capture says it saw"), so
the honest fix is a sentence in §2.3 saying the headers record is what the HTTP
parser resolved, not the header octets — the *body* is byte-faithful, the
header block is not. Flagged to A4 as well: `zoo replay` re-sends captured
headers, so it would re-send that invented header as a genuine one.

Related, same probe: the echoed `Content-Type` is relayed verbatim, folds and
control bytes included —

```
b'HTTP/1.1 200 OK\r\nServer: zoo-sink \r\nDate: …\r\nContent-Type: application/json\r\n\tX-Injected: yes\r\nContent-Length: 0\r\n\r\n'
```

I could **not** produce a true response split (a bare CR is consumed by the
request parser before the sink sees it, and a bare LF terminates the header
line), and the only party who could inject is the exporter into its own
response, so this is not a security finding — but a recorder echoing untrusted
bytes into a response header is worth knowing about.

#### A1-F4 — the manifest is re-read, re-serialized and rewritten on every POST, under the sink's one global lock: quadratic. `next batch`

`spanweave_zoo/manifest.py:92-105` (`append_body`) calls `read()` (a full
`json.loads` of the manifest) and `write_json()` (a full `json.dumps` plus an
atomic replace) for each body, and `spanweave_zoo/sink.py:113-130` does it
inside `with self._lock:` together with the body write. Measured in the A1
worktree with 4 KiB bodies:

```
  200 bodies:   0.145s total,  0.726 ms/body, MANIFEST.json     28.9 KiB
  800 bodies:   1.093s total,  1.366 ms/body, MANIFEST.json    115.6 KiB
 1600 bodies:   3.942s total,  2.464 ms/body, MANIFEST.json    231.3 KiB
```

Per-body cost grows linearly with the number already recorded, as the shape of
the code predicts. Nothing in A1's row or the spec promises throughput, and the
atomic-rewrite rationale in `manifest.write_json`'s docstring is sound (a
reader must never see half a document). But Z4's *real* run is the next thing
to happen, and a stock Python OTLP exporter batching every 5 s for an hour is
in the low thousands of POSTs, serialized behind this lock. Worth sizing before
the real run rather than discovering it in one. Bin `next batch`.

---

### Claim (a) gzip stored still-encoded

Probed end to end against the real CLI, not the test harness: `zoo sink --port
47731 --out <scratchpad>/cap2/z9/run-1/raw` from the A1 worktree, nine POSTs
from a script, then the bytes on disk compared with the bytes sent.

Sent `gzip.compress(JSON_BODY, mtime=0)` with
`Content-Type: application/json` and `Content-Encoding: gzip`, saved to
`sent-gzip.bin`:

```
$ cmp sent-gzip.bin cap2/z9/run-1/raw/0003.body
cmp: byte-identical, no output

$ xxd -l 16 cap2/z9/run-1/raw/0003.body
00000000: 1f8b 0800 0000 0000 0203 ab56 2a4a 2dce  ...........V*J-.

$ file cap2/z9/run-1/raw/0003.body
… : gzip compressed data, max compression, from Unix, original size modulo 2^32 66
```

Magic bytes `1f 8b`: **still gzip**, not decompressed. The headers file keeps
both claims verbatim, in receipt order, with the seam's receipt time
(`cap2/z9/run-1/raw/0003.headers.json`):

```json
  "headers": [["Host","127.0.0.1:47731"], ["Accept-Encoding","identity"],
              ["Content-Length","69"], ["Content-Type","application/json"],
              ["Content-Encoding","gzip"]],
  "method": "POST", "path": "/v1/traces",
  "received_at": "2026-10-09T22:25:58.769203+00:00"
```

And the digest is the digest of the **encoded** bytes, which I checked against
the alternative rather than assuming:

```
encoded sha256: ca6947389d252cb2477e9b426c92bd778f2ad83c69d78a39df73c4e1d646bf83
decoded sha256: 8a3806d19640a8ea3285303d03ed8e1f8c3fa604212a49b0b43f91a3259b4b19
MANIFEST.json : {'bytes': 69, 'file': 'raw/0003.body', 'sha256': 'ca6947389d25…bf83'}
sha256sum sent-gzip.bin → ca6947389d25…bf83
```

`bytes: 69` is the encoded length (the decoded body is 66). `zoo verify` on the
live capture passes and then catches a single flipped bit:

```
$ uv run zoo verify …/cap2
  …/cap2/z9/run-1: 8 body/bodies, 0 problem(s)
zoo verify: every recorded body still hashes to what was recorded

# flip bit 0 of byte 40 of raw/0003.body
$ uv run zoo verify …/cap2
  ! …/cap2/z9/run-1: raw/0003.body sha256 is 517aa9faf3215fa0…, MANIFEST.json says ca6947389d25…
zoo verify: 1 problem(s). A capture is immutable (CLAUDE.md section 0.6): …
exit=1
```

Mutation shown caught — **the plan's named one, applied for real** in
`spanweave_zoo/sink.py` (gunzip when `Content-Encoding: gzip`, before the write):

```
>       assert written == GZIP_BODY, "the gzip bytes were not stored as received"
E       AssertionError: the gzip bytes were not stored as received
E       assert b'{"resourceS...eSpans":[]}]}' == b'\x1f\x8b\x0...B\x00\x00\x00'
E         At index 0 diff: b'{' != b'\x1f'
tests/test_sink.py:139: AssertionError
=========================== short test summary info ============================
FAILED tests/test_sink.py::test_a_gzip_body_is_written_still_compressed - Ass...
FAILED tests/test_sink.py::test_a_body_that_lies_about_its_encoding_is_still_recorded
2 failed, 18 passed in 0.57s
```

Two tests catch it, including the degenerate "lies about its encoding" one
(which crashes the mutant with `gzip.BadGzipFile: Not a gzipped file (b'no')` —
a decompressing sink does not merely improve the capture, it loses it).
Reverted; suite back to `56 passed`.

**Verdict: confirmed.** I verified byte-identity with `cmp`, the `1f 8b` magic,
the verbatim `Content-Encoding: gzip` in `headers.json`, and that the manifest
sha256 is the encoded digest and not the decoded one.

### Claim (b) the sink parses nothing

Structural, not by reading. `spanweave_zoo/sink.py`'s complete import set
(`sink.py:24-32`) is `__future__`, `threading`, `collections.abc`, `http`,
`http.server`, `pathlib` and `spanweave_zoo.manifest`. The transitive
first-party closure is just that one module, confirmed at runtime:

```
first-party modules imported by sink: ['spanweave_zoo', 'spanweave_zoo.manifest', 'spanweave_zoo.sink']
```

Parser/codec vocabulary across the whole package:

```
$ grep -rniE "json\.loads|json\.load\(|gzip|zlib|brotli|decompress|decode\(|protobuf|_pb2|opentelemetry" spanweave_zoo/
spanweave_zoo/manifest.py:80:    document = json.loads(path.read_text(encoding="utf-8"))
spanweave_zoo/sink.py:5:for it, no middleware helpfully decompressing, nothing with an opinion about
spanweave_zoo/sink.py:9:What this module will not do, ever: decode, decompress, parse or validate a
```

Two hits are the module docstring. The third is the one real one and I judge it
out loud: `manifest.read()` → `json.loads` is reachable from the sink's hot
path (`sink.record` → `manifest.append_body` → `read`), but **its input is the
file the sink itself wrote** — `MANIFEST.json` — never a request body. That is
exactly the exception `SPEC.md` §1.1 names ("the capture's own `MANIFEST.json`,
which the zoo wrote"). The `json.dumps` in `manifest.dumps` is serialization of
the sink's own document in the other direction, likewise not parsing of a body.
No body is ever handed to a parser: the body's whole life is
`self.rfile.read(length)` (`sink.py:194`) → `write_bytes(body)` (`sink.py:119`)
→ `hashlib.sha256(body)` (`manifest.digest`). The only place a body is read
*back* is `manifest.py:137` `data = body.read_bytes()` inside `problems()`,
which hashes it and compares — it does not interpret it.

No protobuf anywhere: no `google.protobuf`, no `opentelemetry.proto`, no
`_pb2`, and `pyproject.toml` declares **zero runtime dependencies** (the
`audit` extra is A5's and is not installed by `make check`).

One honest caveat, stated as a caveat rather than a defect: `zlib` **is** in
`sys.modules` after `import spanweave_zoo.sink` —

```
parser/codec modules present after importing sink: ['zlib']
$ uv run python -X importtime -c "import spanweave_zoo.sink" | grep -E "zlib|gzip"
100:import time:        91 |         91 |       zlib
$ uv run python -c "import sys; import http.server; print('zlib after http.server alone:', 'zlib' in sys.modules)"
zlib after http.server alone: True
```

`zlib` arrives via the stdlib `http.server` import chain, not via any zoo code,
and nothing under `spanweave_zoo/` references it. `gzip` is absent entirely
from the import graph. The mutation I applied for claim (a) is also the proof
in the other direction: adding a decode is a *visible* change to this module
that two tests reject.

**Verdict: confirmed.** Nothing under the sink path touches a parser of a
body; the only parse is of the sink's own manifest, which `SPEC.md` §1.1 names
as an explicit non-exception.

### Claim (c) the answer to any POST is the same shape

Nine live probes against `zoo sink` on port 47731 (deliberately not 4317-4320;
I note a port caveat at the end). Exact observations:

| # | request | status | response headers | body |
|---|---|---|---|---|
| 1 | `POST /v1/traces`, `Content-Type: application/x-protobuf`, 23 B | **200 OK** | `Content-Length: 0`, `Content-Type: application/x-protobuf`, `Date: …`, `Server: zoo-sink ` | `b''` (0 B) |
| 2 | `POST /v1/traces`, `application/json`, 66 B | **200 OK** | same, `Content-Type: application/json` | `b''` |
| 3 | `POST /v1/traces`, `application/json` + `Content-Encoding: gzip`, 69 B | **200 OK** | same, `Content-Type: application/json` (no `Content-Encoding` echoed) | `b''` |
| 4 | `POST /v1/traces`, `application/json`, **0 B** | **200 OK** | same | `b''` |
| 5 | `POST /v1/traces`, `Content-Type: pancakes/syrup; charset=moon`, 8 B | **200 OK** | same, `Content-Type: pancakes/syrup; charset=moon` | `b''` |
| 6 | `POST /v1/traces`, **no `Content-Type`**, 12 B | **200 OK** | `Content-Length: 0`, `Date`, `Server` — **no `Content-Type` at all** | `b''` |
| 7 | `POST /v1/metrics`, `application/json`, 66 B | **404 Not Found** | `Content-Length: 0`, `Content-Type: application/json`, `Date`, `Server` | `b''` |
| 9 | `POST /v1/metrics`, no `Content-Type`, 1 B | **404 Not Found** | `Content-Length: 0`, `Date`, `Server` | `b''` |
| 8 | `GET /v1/traces` | **501** `Unsupported method ('GET')` | `Connection: close`, `Content-Length: 481`, `Content-Type: text/html;charset=utf-8`, … | 481-byte stdlib HTML error page |

Row by row against the A1 row and §3.3/§3.4:

- **200 + empty body + the request's content type echoed, for `/v1/traces`:
  holds for all six POSTs**, including protobuf, gzip, an empty body and a
  content type no receiver has ever heard of. The status does not depend on a
  byte of the payload.
- **No `Content-Type` to echo → none invented** (probe 6). `SPEC.md` §3.3 says
  so explicitly ("no `Content-Type` at all if the request had none — the sink
  has no content type of its own to invent") and
  `test_a_request_with_no_content_type_gets_none_echoed_back` pins it. So the
  answer's header *set* is not literally constant; it is constant as a
  function of the request's own claim, which is the stronger honesty property.
  Mutation 2 below proves a test holds this.
- **404 and still recorded: yes, verified on disk.** `rejected/0001.body` is
  byte-identical to the JSON I POSTed to `/v1/metrics` (`cmp` silent), and
  `rejected/0001.headers.json` records `POST /v1/metrics 66
  2026-10-09T22:25:58.773944+00:00`. The rejected counter is separate and
  started at `0001` while `raw/` was already at `0006`, so `raw/NNNN` stays
  the contiguous sequence `json/NNNN` pairs with (§3.4). `MANIFEST.json`
  carries both kinds in record order, `rejected/` paths distinguishable:
  `{'bytes': 66, 'file': 'rejected/0001.body', 'sha256': '8a3806d19640…'}`.
- **`GET` is the one answer of a different shape**: 501 with a 481-byte HTML
  page and `Content-Type: text/html;charset=utf-8` — a content type the sink
  did not get from the request. `SPEC.md` §3.4 specifies exactly this
  ("Methods other than `POST` are answered `501` by `http.server` and are not
  recorded"), and `CLAUDE.md` §0.6 rule 3 scopes the claim to POSTs ("answers
  every POST the same way"), so this is in-spec. It is still the one place the
  recorder emits a body and a content type of someone else's invention, and
  the only untested answer in the suite.
- `Date` varies per request (finding A1-F2), so the answer is invariant in
  shape and not in bytes.

Two further mutations of my own, applied for real in
`/tmp/.../scratchpad/wt-a1/spanweave_zoo/sink.py` and reverted after:

**Mutation 2 — echo a content type of the sink's own invention** (replace the
`Content-Type` echo in `_answer` with a hardcoded `application/json`):

```
>       assert answer_headers["Content-Type"] == "application/x-protobuf"
E       AssertionError: assert 'application/json' == 'application/x-protobuf'
E         - application/x-protobuf
E         + application/json
=========================== short test summary info ============================
FAILED tests/test_sink.py::test_a_protobuf_body_round_trips_byte_for_byte - A...
FAILED tests/test_sink.py::test_a_request_with_no_content_type_gets_none_echoed_back
2 failed, 18 passed in 0.51s
```

Both halves of the echo claim are held: the right value when there is one, and
*nothing* when there is not.

**Mutation 3 — receipt-order numbering: one counter for the whole sink**
(`number = sum(self._counters.values()) + 1`, so `raw/` and `rejected/` share a
sequence):

```
E       FileNotFoundError: [Errno 2] No such file or directory: '…/captures/z4/run-1/raw/0001.body'
=========================== short test summary info ============================
FAILED tests/test_sink.py::test_the_two_counters_are_independent - FileNotFou...
1 failed, 19 passed in 0.54s
```

**Verdict: confirmed with caveat.** For POSTs the shape is genuinely invariant
— 200/404 by path alone, always an empty body, always the request's own content
type and never one invented — and a 404 really does record the bytes. The
caveats are that the header *set* legitimately loses `Content-Type` when the
request had none (specified, tested), that `Date` makes the answer non-constant
byte-wise (A1-F2), and that non-POST methods get a shape of their own from the
stdlib (specified in §3.4, untested).

---

### Caveats on the run itself

- **Port contention, not a defect.** My first live run used port 44318 and
  recorded two POSTs I did not send — 128-byte protobuf, `User-Agent:
  Python-urllib/3.14`, service name `zoo-synthetic`, trace id
  `4bf92f3577b34da6a3ce929d0e0e4736` — i.e. another agent's A2 synthetic export
  landing on the same "unused high port" at `22:24:38`, one second before my
  probes. I discarded that capture, re-ran the whole probe on port **47731**,
  and every number in this section comes from the clean run. No test ever hit
  4317-4320 and I saw no `Address already in use`.
- Both worktrees were created by absolute path under the scratchpad and removed
  with `git worktree remove --force`. Nothing in
  `/home/msi/git/spanweave-zoo` was edited, added, committed or checked out;
  `git status` there was clean before and after.
