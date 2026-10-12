# Section a3c — cold review of 8af242d (A3c, "sink: the octets of each request's head are the record")

Reviewer: aux (cold). Ports used: 4410-4415 only. Worktrees:
`$SP/wt-a3c-commit` (8af242d) and `$SP/wt-a3c-parent` (derived parent), both
removed at the end. `$SP` = `/tmp/claude-1000/-home-msi-git-spanweave/c6ce1da1-d130-4eba-ab34-b9b8ec6c6489/scratchpad`.
Python in the worktree venv: 3.14.6.

## 0. Derived parent

```
$ git rev-parse 8af242d^
23d1ddb8ead986dd932e86e29c4534e802886237   # plan: A3b done, and the per-body cost criterion found a quadratic parent
```

A `plan:` commit, as expected. The source under it is A3b's.

## 1. Spec in the same commit

Yes. The commit touches SPEC.md §0 preamble, §2 (layout), §2.3 (rewritten: `.raw` is the
unmodified record, `.json` the parse), §3.1 (refusal counts both kinds), §3.2, §3.4, §4.5,
§5.6, plus README (two places) and a CHANGELOG `## A3c` entry. Body names A3c and the sections.

Stale/inaccurate spec text left behind (see A3c-3, A3c-4):
- SPEC.md:343 (§3.5) still says "**This is the whole of what the sink writes** (that, and each
  request's `NNNN.headers.json`)" — `.headers.raw` is not named there.
- SPEC.md:268 (§3.2) "It is written from the bytes as they are read off the socket, before
  anything parses them" — the bytes are *captured* before the parse, but the file is *written*
  only by `Recorder.record` after a successful parse (see claim e).
- SPEC.md:158 (§2.3) "every header after the split is absent from the parse altogether" — only
  true when the text after the bare CR is not header-shaped (see claim a).

## 2. Parent run (commit's tests copied into the parent worktree)

`cp tests/test_sink.py tests/test_manifest.py` from the commit into the parent, then
`uv run pytest -q tests/test_sink.py tests/test_manifest.py` → **27 failed, 29 passed**.

| Test (new in A3c) | Parent result | Kind |
|---|---|---|
| test_sink::test_the_headers_raw_file_is_the_octets_the_client_sent | FAIL | FileNotFoundError `raw/0001.headers.raw` — real (file not produced) |
| test_sink::test_a_bare_cr_in_a_header_value_is_in_raw_and_not_in_json | FAIL | FileNotFoundError — real |
| test_sink::test_each_request_on_one_connection_gets_its_own_head | FAIL | FileNotFoundError — real |
| test_sink::test_a_rejected_post_keeps_its_head_too | FAIL | FileNotFoundError `rejected/0001.headers.raw` — real |
| test_sink::test_the_manifest_covers_the_head_it_was_never_told_about | FAIL | AssertionError `'raw/0001.headers.raw' in {'bodies.jsonl', 'raw/0001.headers.json', ...}` — real |
| test_manifest::test_a_rewritten_head_in_headers_raw_fails_verify | FAIL | AttributeError `sink.HEADERS_RAW_SUFFIX` — **vacuous** |
| 20 pre-existing test_manifest tests | FAIL | 20× AttributeError `HEADERS_RAW_SUFFIX` (helper) + 1× TypeError `record() got an unexpected keyword argument 'head'` — collateral, vacuous |

Verdict: the five sink tests are red on the parent for the real reason (no `.raw` file).
The one new manifest test is vacuous on the parent (it would pass against A3b's walk-based verify
once the helper constant exists — it tests A3b's walk, which is what its comment says).

## 3. Mutations (commit worktree; each reverted with `git checkout spanweave_zoo/sink.py`)

**M1 — the row's mutation: write the stdlib's reconstructed head to `.raw`** (sink.py `do_POST`):
```diff
-            head=self._head,
+            head=(self.requestline + "\r\n" + "".join(f"{k}: {v}\r\n" for k, v in self.headers.items()) + "\r\n").encode("latin-1"),
```
Full suite: **1 failed, 146 passed, 3 skipped**. Only
`test_sink.py::test_a_bare_cr_in_a_header_value_is_in_raw_and_not_in_json`:
```
E       AssertionError: the head was reconstructed, not recorded
E       assert b'POST /v1/tr...rd: a\r\n\r\n' == b'POST /v1/tr... a\rb\r\n\r\n'
E         At index 130 diff: b'\n' != b'b'
```
`test_the_headers_raw_file_is_the_octets_the_client_sent` **passes** under M1 (well-formed head
reconstructs byte-identically) — WORKPLAN §4's claim confirmed exactly.

**M2 — body leaks into the head** (`_Head.read` appends to the buffer; recording ended in
`do_POST` after the body is read instead of in `parse_request`):
```diff
-        return self._stream.read(size)
+        data = self._stream.read(size)
+        self._head += data
+        return data
-        self._head = self._stream.end()
-            head=self._head,
+            head=self._stream.end(),
```
→ 4 failed: test_the_headers_raw_file_is_the_octets_the_client_sent,
test_a_bare_cr_in_a_header_value_is_in_raw_and_not_in_json,
test_each_request_on_one_connection_gets_its_own_head, test_a_rejected_post_keeps_its_head_too.

**M3 — `begin()` does not reset the buffer** (`-        self._head = bytearray()` in `_Head.begin`)
→ 1 failed: test_each_request_on_one_connection_gets_its_own_head
(`assert 2 == 1` on `head.count(b'POST /v1/traces')`).

**M4 (equivalent mutant, noted)** — `_Head.end()` no longer sets `_recording = False` → 147 passed.
Survives because the body is read with `read`, never `readline`, and `begin()` resets per request;
the flag is belt-and-braces, not observable today. Not a finding.

## 4. Clock / randomness / network

Diff adds only `import io` under `spanweave_zoo/`. No `time.`, `datetime.`, `random`, `socket`,
`urllib`, `http.client`, `subprocess`. `_Head` wraps the handler's existing `rfile`; no new seam. OK.

## 5. One concern / message form

`sink: the octets of each request's head are the record` — `<area>: <one line>`; body names A3c
and SPEC sections; one concern (the startup refusal glob change is the direct consequence of a new
headers file kind). OK.

## 6. make check (commit worktree)

`make check` → exit 0: ruff "All checks passed!", "19 files already formatted", mypy "Success: no
issues found in 7 source files", pytest **147 passed, 3 skipped**, gates 30 passed, `zoo verify`
"no captures under captures/ -- nothing to re-hash", `zoo 0.0.1`.
The 3 skips are `tests/test_collector_real.py` (binary absent in a worktree). Copied the real
binary in and ran them: **3 passed** (binary removed again). `install-check` not run (no packaging
change in this commit).

## 7. Specific claims, reproduced with a real `zoo sink` and raw sockets

Harness: `$SP/a3c-probe/run.sh NAME PORT probe...` launches
`.venv/bin/zoo sink --port <4410..4415> --out $SP/a3c-probe/cap-NAME/captures/z4/run-NAME/raw`
(SIGINT reset to default so Ctrl-C finalizes), sends each probe file on its own connection via
`send.py` (raw `socket.sendall`, 3 s read timeout; `.shut` probes half-close after sending),
then SIGINTs the sink and lists the run directory.

### (a) bare CR in a header value — PARTLY REFUTED

Sent (head then body `hello world`):
```
POST /v1/traces HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/x-protobuf\r\nContent-Length: 11\r\nConnection: close\r\nUser-Agent: otel\rX-Injected: yes\r\n\r\n
```
Answer: `HTTP/1.1 200 OK ... Content-Type: application/x-protobuf\r\nContent-Length: 0`.
`xxd raw/0001.headers.raw` (tail):
```
00000070: 2063 6c6f 7365 0d0a 5573 6572 2d41 6765   close..User-Age
00000080: 6e74 3a20 6f74 656c 0d58 2d49 6e6a 6563  nt: otel.X-Injec     <- 0d bare CR, no 0a
00000090: 7465 643a 2079 6573 0d0a 0d0a            ted: yes....
```
`cmp raw/0001.headers.raw a.head` → IDENTICAL (156 bytes, through the blank line). Body cmp → IDENTICAL.

**But `X-Injected` IS a header in `.headers.json`:**
```
[["Host","127.0.0.1"],["Content-Type","application/x-protobuf"],["Content-Length","11"],
 ["Connection","close"],["User-Agent","otel"],["X-Injected","yes"]]
```
`email`'s parser splits on the bare CR and, when the remainder is header-shaped, takes it as a new
header. The commit's own test uses `X-Weird: a\rb`, where the remainder `b` is not header-shaped,
so the parser stops there and later headers vanish — that is the only shape SPEC §2.3 describes.

Consequence probe (`a2`, port 4411): `User-Agent: otel\rContent-Encoding: gzip` with an
uncompressed body `hello world`. `.json` gains `["Content-Encoding","gzip"]`, and **the manifest's
`bodies[0].content_encoding` is `"gzip"`** — a value read from the parse (SPEC §2.3/§5.4) for a
header line the client never sent. `.raw` is correct (one `Content-Encoding`, preceded by `0d`, not
`0d0a`). `zoo verify` passes. Also: `Recorder.record` forwards the parsed `headers` to the tee
(sink.py:269), so the Collector would receive the invented `Content-Encoding: gzip` (not run here).

### (b) the row's mutation — CONFIRMED

See M1: only the bare-CR test fails; the octet-identity test passes under the mutation.

### (c) bare CR early drops Content-Length — CONFIRMED, and worse than "honest"

Probe `c` (port 4412): `Host`, then `User-Agent: otel\rpython/1.0`, then `Content-Type`,
`Content-Length: 11`, `Connection: close`, body `hello world`.
- Answer: `HTTP/1.1 200 OK ... Content-Length: 0` — **no Content-Type echoed** (it was dropped from
  the parse), and the connection is **not closed** (`Connection: close` dropped too; client timed
  out after 3 s).
- `.json`: `bytes: 0`, headers `[["Host","127.0.0.1"],["User-Agent","otel"]]`.
- `.raw` = client head byte-for-byte (cmp IDENTICAL); it shows `Content-Length: 11`.
- Manifest: `bytes 0, content_type null, content_encoding null`, `problems: None`; verify exit 0.

Probe `c2` (port 4413), to see where the 11 bytes go: connection 1 = same request, half-closed;
connection 2 = same request **followed by a well-formed second request**
(`Content-Type: application/json`, `Content-Length: 15`, body `{"second":true}`).
- Conn 1 answer: `200 OK` and then an HTML page `Error code: 400 ... Bad HTTP/0.9 request type ('hello')`.
- Conn 2 answer: `200 OK` and then `HTTP/1.1 400 Bad request syntax ('hello worldPOST /v1/traces HTTP/1.1')`.
- On disk: `raw/0001.body` 0 bytes, `raw/0002.body` 0 bytes, two `.raw`/`.json` pairs. **Nothing
  else**: the 11 body bytes of each request and the whole second request (head + 15-byte body) are
  in no file, not in `rejected/`, not in `problems`. `zoo verify` exit 0 ("every recorded body still
  hashes to what was recorded").
- Same probe against the parent sink (port 4415): identical answers and identical loss, minus the
  `.raw` files. So the loss is pre-existing (A1 framing via the parse), and A3c's `.raw` is an
  improvement (it shows `Content-Length: 11` against `bytes: 0`) — but WORKPLAN §4's "honest" is
  not the whole story: leftover body bytes are read as the next request line, answered 400 by the
  stdlib, and they *and any following request on the connection* vanish silently.

### (d) other head shapes (probe `d`, port 4414, one connection each, half-closed)

| Shape | Client got | `.raw` | `.json` | Silent loss? |
|---|---|---|---|---|
| obs-fold `X-Fold: a\r\n  folded b` | 200 | client head byte-identical (cmp) | `["X-Fold","a\r\n  folded b"]` (fold kept verbatim, incl. CRLF) | no |
| header line 70,000 bytes | **431 Line too long** + HTML | **none** | none | **yes** — nothing recorded anywhere |
| 101 headers | **431 Too many headers** + HTML | **none** | none | **yes** |
| LF-only line endings | 200 | `POST ... HTTP/1.1\n...\n\n` byte-identical (cmp) | parsed normally | no |
| no headers (`POST /v1/traces HTTP/1.1\r\n\r\n` + `hello`) | 200, then **400 HTML** (`hello` read as an HTTP/0.9 request) | `POST ... HTTP/1.1\r\n\r\n` byte-identical | `bytes: 0`, `headers: []` | **yes** — the 5 trailing bytes, as in (c); zero-byte body is per §3.7, the trailing bytes are not mentioned |

Manifest for run `d`: 3 bodies, 0 problems, verify exit 0 — the two 431s and the trailing bytes
leave no trace in the capture.

### (e) ".raw is written before the parse" — REFUTED (as a statement about the file)

Code path: `_Handler.handle_one_request` → `_stream.begin()` (sink.py:362); `parse_request`
(sink.py:368) calls `super().parse_request()` then `self._head = self._stream.end()` — the octets
are *buffered* before/while parsing; but the only write is
`(directory / (stem + HEADERS_RAW_SUFFIX)).write_bytes(head)` in `Recorder.record` (sink.py:222),
reached only from `do_POST` (sink.py:385), which `http.server` calls only after a successful parse.
When `parse_request` returns False (or `parse_headers` raises → 431) the buffered octets are dropped.

Run: `POST /v1/traces HTTP/1.x` → client got an HTML 400 page; `HTTP/2.0` → HTML 505 page; the two
431s above. **No `.raw` in `raw/` or `rejected/`**, no `rejected/` directory at all, no problem in
the manifest. Pre-existing for `.json`/`.body` (SPEC §3.4 only speaks of non-POST methods → 501),
but A3c's SPEC §3.2 sentence implies the head file survives the parse, and it does not.

## Findings

**A3c-1 — the parse can invent headers, and the manifest carries the invention.** (thread → next batch)
SPEC.md:158 (§2.3) says a bare CR truncates the value and "every header after the split is absent
from the parse altogether". Reproduced (claim a): when the text after a bare CR is header-shaped
(`User-Agent: otel\rX-Injected: yes`), `email` parses it as a **new header**; `.headers.json`
contains `X-Injected: yes`. With `\rContent-Encoding: gzip` the manifest's
`bodies[].content_encoding` becomes `"gzip"` for an uncompressed body, because §5.4 reads it from
the parse, and the tee forwards the parsed headers (sink.py:269). `.raw` is correct throughout, and
SPEC already says `.raw` wins on disagreement, so the record itself is not wrong. Proposed bin:
**next batch** — correct §2.3's description (both directions: truncation *and* injection) and add
the injection shape as a test; decide whether the manifest's content headers should be flagged
(or read differently) when `.raw` and the parse disagree. Not Z4-blocking: stock Python OTel
exporters go through `http.client`/urllib3, which refuse CR in header values.

**A3c-2 — bytes after a head whose framing the parse lost are silently unrecorded, and take the
next request with them.** (next batch)
Reproduced (claims c, d): an early bare CR drops `Content-Length` and `Connection` from the parse;
the sink records a zero-byte body, answers 200 without closing, and the stdlib then reads the body
bytes as a request line, answers 400 with an HTML page, and closes — a following well-formed request
on the same keep-alive connection is lost too. The same happens for a request with no
`Content-Length` and a body (and would for `Transfer-Encoding: chunked`). Nothing reaches disk,
`problems` is empty, `zoo verify` exits 0. Pre-existing (identical on the parent sink, sink.py
`_read_body`), and A3c's `.raw` makes the first half detectable, but WORKPLAN §4's "honest" overstates
it, and CLAUDE.md's losslessness / "a capture is never silently fine" is not met. Proposed bin:
**next batch** — at minimum close the connection after a request recorded without a usable
`Content-Length` and say so in §3.7; better, record what the sink could not frame. Not
Z4-blocking on the expected exporter (it sends `Content-Length`; no bare CR), but the operator
should know a chunked or bare-CR exporter would produce a quietly short capture.

**A3c-3 — a head the stdlib refuses leaves no record at all; SPEC §3.2 implies otherwise.** (next batch)
Reproduced (claim e, d): `HTTP/1.x` → 400, `HTTP/2.0` → 505, a 70 KB header line → 431, 101
headers → 431; each answered with an HTML error body (not the sink's uniform empty answer), and no
`.raw`, `.json` or `.body` in `raw/` or `rejected/`, no manifest problem. The octets were in
`_Head`'s buffer (sink.py:368-377) and were discarded. SPEC.md:268 says `.raw` "is written from the
bytes as they are read off the socket, before anything parses them", which reads as surviving a
failed parse. Proposed bin: **next batch** — either record parse-rejected heads (e.g. under
`rejected/` with the octets) or state in §3.4/§3.7 that a head the stdlib refuses is answered by
the stdlib and not recorded.

**A3c-4 — §3.5 still lists only `.headers.json` as what the sink writes.** (next batch, doc-only)
SPEC.md:343 "This is the whole of what the sink writes (that, and each request's
`NNNN.headers.json`)" omits `NNNN.headers.raw`. One-line fix.

Not findings (confirmed results): `.raw` byte-identical to the client head for bare CR, obs-fold,
LF-only and empty heads; per-request heads on keep-alive; rejected-path heads kept; `.raw` covered
by the manifest walk; the row's mutation caught only by the bare-CR test, as §4 says.

## Cleanup

Worktrees removed with `git worktree remove --force` + `git worktree prune`; probe captures live
only under `$SP/a3c-probe/`. `git -C /home/msi/git/spanweave-zoo status --short` empty.
