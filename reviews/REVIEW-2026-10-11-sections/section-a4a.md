# A4a — `29c9d5c` (replay: the captured head goes out as its octets, with only the Host line changed)

Reviewer: aux (cold), 2026-10-11. Worktrees under
`/tmp/claude-1000/-home-msi-git-spanweave/0cebe00d-6f1e-4d97-b470-8374b11d7075/scratchpad/a4a/`
(`commit` = 29c9d5c, `parent` = derived `29c9d5c^` = `d5436a6`, `mut` = 29c9d5c),
all removed (`git worktree remove --force` x3, `git worktree prune`). Sinks on
4391–4398, a scratch Collector on 4396; every process I started was stopped
(`ps … | grep -E '[o]telcol|[z]oo (sink|replay)'` → none).

## Bar (§0.2 / CONTRIBUTING)

| Check | Result |
|---|---|
| Spec in the same commit | **Yes.** SPEC §6 intro, §6.2 rewritten (lines 1358–1427 at 29c9d5c), §6.4 exit-1 row (1474), §6.5, §4.8 `forward` row (872). README §replay paragraph updated, CHANGELOG entry. |
| Derived parent | `git rev-parse 29c9d5c^` = `d5436a6` ("plan: A3f done…"), a `plan:` commit whose code is A3f's, so the run is against the old http.client replayer. |
| New tests on the parent | `cp commit/tests/test_replay.py parent/tests/` → **19 failed, 19 passed**. **Real**, not vacuous: all five `test_a_replayed_head_differs_from_the_captured_one_in_the_host_line_only[*]` fail on assertions showing the four N-6 differences plus the hop-by-hop drop (`host-not-first: At index 26 diff: b'H' != b'U'`; `http-1.0: b'1' != b'0'`; `lf-only: b'\r' != b'\n'`; `value-whitespace: b' ' != b'v'`; `hop-by-hop: b't' != b'n'`), and `test_the_replayer_does_not_send_through_http_client` fails with `'the replay opened an http.client connection'`. The others fail on API (`no attribute 'retarget'`) or message wording, so they are vacuous on the parent. |
| Row mutation: replay through `http.client` | `sender`'s `send` replaced by `forward.HttpForward(host, port)(method, path, split_head(head)["headers"], body)` → **7 failed**: all 5 head-identity params, the http.client structural test, the bare-CR test. **Caught.** |
| Extra mutations | M2 `retarget` returns the octets unchanged → 10 failed (fixture head identity, 4 shapes, --json, gzip, 3 retarget unit tests). M3 `terminated` always True → 2 failed (both unterminated cases). M4 `retarget` splits on bare LF too → 3 failed (`lf-only`, both bare-LF `retarget_touches_no_host` cases). All caught. |
| Clock / random / network | `replay.py` imports no socket; the one new socket is `forward.send_head` (`socket.create_connection`, forward.py:146), injected as `send` and passed only from `cli.py`. **`send` is defined in §6.2, not given its own §4.8 row**; §4.8's `forward` row names it ("one of the package's two outbound sockets, with §6.2's `send`"). See T-A4a-2 for the "two" count. |
| One concern | Yes. `sink.field_name` extracted from `split_head` (sink.py) so replay and the head split use one token rule. That serves the Host rule, not a drive-by. |
| `make check` in the commit's worktree | **Green**: `All checks passed!` (ruff), `328 passed, 4 skipped`, gates `31 passed`, `zoo verify` on the fixture OK, `EXIT 0`. |

## (a) Replayed head is byte-identical except Host: **confirmed**

I made a capture with raw-socket POSTs (`scratchpad/a4a/post.py`) into a live
`zoo sink --port 4391 --out …/cap1/run/raw`, all eight answered `HTTP/1.1 200 OK`.
I sealed it the way the tests' `crafted()` does (`manifest.label` + `manifest.finish`),
because `zoo sink` alone writes no `MANIFEST.json`. Then
`zoo replay …/cap1/run --to http://127.0.0.1:4392` into a fresh sink gave
`8 sent, 0 that did not answer 2xx`, exit 0. I compared each pair of `.headers.raw`
files split on CRLF (`scratchpad/a4a/cmp.py`):

```
0001 python-exporter  head_identical=False lines 10/10 len 223/223 body_identical=True
     line 1: orig=b'Host: 127.0.0.1:4391'   repl=b'Host: 127.0.0.1:4392'
0002 host-not-first   lines 7/7  len 119/119   line 3: orig=b'Host: 127.0.0.1:4391' repl=b'Host: 127.0.0.1:4392'
0003 no-space (x:v)   lines 7/7  len 104/105   line 1: orig=b'Host:127.0.0.1:4391'  repl=b'Host: 127.0.0.1:4392'
0004 http-1.0         lines 6/6  len 102/102   line 1: orig=b'Host: 127.0.0.1:4391' repl=b'Host: 127.0.0.1:4392'
0005 lf-only          head_identical=True lines 1/1 len 97/97
0006 repeated         lines 8/8  len 126/126   line 1: (Host only)
0007 bare-cr          lines 7/7  len 125/125   line 1: (Host only)
0008 gzip             lines 7/7  len 126/126   line 1: (Host only)
body 1..8 cmp ok
```

- Every differing line is the Host line. Host stays where it was (line 3 in 0002), the line count is unchanged, and `HTTP/1.0`, `x:v`, `X-Rep` x2 in order, `Connection: keep-alive`, the bare CR and `Content-Encoding: gzip` all go out as captured. The replayed 0007 head reads `…Host: 127.0.0.1:4392\r\nX-Evil: a\rInjected: b\r\n…`.
- In 0003 the Host line itself gets re-spaced (`Host:` becomes `Host: `). §6.2 says this: "the name as sent, `: `, and the `--to` destination".
- **0005, the LF-only head, is identical, Host included.** The replay sent `Host: 127.0.0.1:4391`, the *capture's* destination, to the sink on 4392. §6.2 states this ("a head whose every line ends in a bare LF … is not touched"), and the test comments on it. See (b).
- `--json` on the committed fixture into a fresh sink on 4393 gave `json/0001.json 200 391 bytes`, exit 0:
  ```
  orig b'POST /v1/traces HTTP/1.1\r\nHost: 127.0.0.1:39691\r\nUser-Agent: OpenTelemetry Collector Contrib/0.162.0 (linux/amd64)\r\nContent-Length: 391\r\nContent-Type: application/json\r\nAccept-Encoding: gzip\r\n\r\n'
  repl b'POST /v1/traces HTTP/1.1\r\nHost: 127.0.0.1:4393\r\nUser-Agent: OpenTelemetry Collector Contrib/0.162.0 (linux/amd64)\r\nContent-Length: 391\r\nContent-Type: application/json\r\nAccept-Encoding: gzip\r\n\r\n'
  ```
  `cmp json/0001.json …/0001.body` → identical.

## (b) §4's consequences: **all five stated in SPEC §6.2/§6.4**. Two spot-checks hold; chunked holds only against a framing-aware receiver

Where each one is stated:
- bare CR sent as captured: §6.2 "A head HTTP forbids goes out as it arrived".
- hop-by-hop sent: §6.2 second bullet and §6.5.
- Host after a bare LF left alone: §6.2 first bullet, line 1378.
- empty or unterminated head refused per body, exit 1: §6.2 line 1412 and §6.4 exit-1 row.
- chunked POST times out: §6.2 line 1398.

Spot-checks:
- **Bare CR**: 0007 above. It goes out as captured and the zoo sink answers 200. Against the scratch stock Collector 0.162.0 (`collector/otelcol-contrib`, OTLP/HTTP on 4396, `debug` exporter) the same replay got `raw/0007.body 400`. That is the receiver's answer, as §6.2 intends.
- **Host after a bare LF.** I captured `…Host: 127.0.0.1:4394\r\nX-A: a\nHost: 127.0.0.1:4394\r\n…` and replayed it to a fresh sink on 4395. The receiving sink recorded:
  ```
  b'POST /v1/traces HTTP/1.1\r\nHost: 127.0.0.1:4395\r\nX-A: a\nHost: 127.0.0.1:4394\r\nContent-Type: application/json\r\nContent-Length: 20\r\n\r\n'
  headers.json: [['Host','127.0.0.1:4395'], ['X-A','a\nHost: 127.0.0.1:4394'], ['Content-Type',…], ['Content-Length','20']]
  ```
  **Yes:** the new target receives the *original* Host value as a second Host-like line. The zoo sink files it under X-A's value. The Go receiver treats bare LF as a line end and sees two Hosts, giving `400 Bad Request` from the Collector. Controls on 4396:
  - the same head with `\nX-B: b` in place of the bare-LF Host → 200;
  - two CRLF `Host:` lines with the same value → 400.

  So the 400 comes from the duplicate Host. The capture's original destination would have answered the same, so this is faithful, as specified. For an LF-only head the old Host is the only one sent (0005). The Collector took it with 200, but a receiver that routes by Host would get the old authority. Specified and deliberate, so no defect (T-A4a-1).
- **Chunked.** A chunked POST is captured as a zero-byte body. Replayed into a **zoo sink** it answers at once: `raw/0002.body 200 0 bytes`, exit 0, 0.10 s. The sink does not decode framing (§3.7), so nothing waits. Replayed into the **Collector** it gives `raw/0002.body not sent: TimeoutError: timed out` after the 2 s `--timeout`, exit 1. §6.2's "leaves the receiver waiting for chunks; the timeout that follows is the answer" is true only for a receiver that reads chunked framing. The outcome depends on the receiver (N-A4a-2).

## (c) N-7: **still present**

`zoo replay …/cap1/run --to http://127.0.0.1:4397` with nothing listening:
```
  raw/0001.body  not sent: ConnectionRefusedError: [Errno 111] Connection refused
  … (all 8)
zoo replay: 8 sent, 8 that did not answer 2xx
exit 1
```
The cause is `cli.py:444` at 29c9d5c: `f"zoo replay: {len(outcomes)} sent, …"` counts every outcome, including those with `error` set and `status None`. A4a did not touch it. The run against the Collector shows it in mixed form too: `2 sent, 2 that did not answer 2xx` with 0002 `not sent: TimeoutError`. §6.4 line 1477 says "how many were sent", so the code contradicts the spec. → **next batch** (N-7 carried). It does not affect what a capture records.

## (d) Captured Content-Length disagreeing with the body: **safe for every capture the sink can make; one hand-made case delivers an extra request**

The sink reads exactly the declared length: `_read_body`, sink.py:508–528, `return self.rfile.read(length)`. A sink-made capture can therefore only have body ≤ Content-Length:
- **CL missing or not a number**: the body is recorded empty and the head is sent as captured. The receiver frames it its own way (chunked → timeout, as in (b)).
- **Body shorter than CL** (the client closed early): the replay sends CL=N and fewer than N octets. The receiver waits, the request times out, it is counted not sent and exit is 1. No extra bytes reach the receiver. This is safe, and it is the same "framing does not match" case §6.2 covers.

**Body longer than CL is only possible by hand.** `zoo replay` does not verify (§6.5), so a body edited after capture is sent as-is. I appended a complete second request to a copy's `raw/0002.body`
(`POST /v1/smuggled HTTP/1.1\r\nHost: x\r\n…Content-Length: 20\r\n\r\n{…}`).
Replayed into a fresh zoo sink on 4398, the replayer printed only `raw/0002.body 200 131 bytes` and `8 sent, 0 that did not answer 2xx`. The **receiver recorded an extra request** under `rejected/0001.headers.raw`:
`b'POST /v1/smuggled HTTP/1.1\r\nHost: x\r\n…'`.
`send_head` reads one response and closes, but the excess is already in the server's buffer and gets served as a pipelined request. This is the case §6.2 rejects for the unterminated head ("would arrive as … a request no exporter made"), and the replay does not apply that reasoning to a body longer than its CL. The sink cannot produce such a capture, and `zoo verify` would flag the edited body's hash, so it cannot affect Z4 → **thread** (T-A4a-3): a body longer than a numeric captured CL could be refused per body, on the unterminated-head rule.

## Findings, binned

- **Blocks Z4 capture:** none. A4a changes only the replayer, and the sink and capture path are untouched apart from the `field_name` extraction, which `make check` covers.
- **Next batch:**
  - **N-7** (carried, reproduced above): the summary counts unsent bodies as "sent", `cli.py:444`.
  - **N-A4a-2**: SPEC §6.2 line 1398 says a replayed chunked capture "leaves the receiver waiting". That is only true for a receiver that decodes chunked framing. Into a zoo sink it is `200 0 bytes`, exit 0. Reword as receiver-dependent; it is a doc line.
- **Thread:**
  - **T-A4a-1**: an LF-only head (and any Host after a bare LF) carries the *capture's* authority to the new target. A Go receiver 400s on the duplicate, and a Host-routing receiver would misroute an LF-only head. This is specified and faithful. Record it as a known property for A5's audit reading, so a 400 there is not misread.
  - **T-A4a-2**: §4.8's row and §6.2 line 1427 say `forward` and `send` are "the only outbound socket(s) in the package". `collector.py:405` (`_accepts`, `socket.create_connection`, from 2b3c499) is a third outbound connect. §4.6 describes it but it is behind no named seam. This predates A4a; A4a restated the count.
  - **T-A4a-3**: from (d), a hand-edited body longer than its numeric Content-Length delivers the excess to the receiver as a pipelined request, and the replay reports one 200.
  - (Observed, A3f's territory and not A4a's) An LF-only head's `headers.json` lists `headers: []` with no `unparsed` key. The whole head is "the request line" on the CRLF split, so the Host and Content-Type lines appear nowhere in the parse. The raw file keeps them.
