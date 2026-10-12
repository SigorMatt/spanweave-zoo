# Section a4 — 0c1e538 `replay: a capture's bytes and its captured head, sent again` (batch A4)

Reviewer: aux (cold). Ports used: 4450-4458 only. Scratch: `$SP/a4/` (SP = the session scratchpad).
Worktrees: `$SP/wt-a4-commit` (0c1e538), `$SP/wt-a4-parent` (derived `git rev-parse 0c1e538^` = 5006d7d,
`plan: A0b done, and pytest exits 0 when every selected test skips`). Both removed at the end.

## 1. Spec / changelog in the same commit
Yes. SPEC.md status line + §6 (6.1-6.5) written in this commit; CHANGELOG `## A4` entry; README table row and a
"The replayer" section. manifest.py gains public `moment_of`, `received_at`, `recorded_bodies`, `HEADERS_RAW_SUFFIX`
(sink.py now aliases the constant) — supporting refactor for replay, acceptable within one concern.

## 2. Parent run
`cp tests/test_replay.py` into the parent worktree, `uv run pytest tests/test_replay.py -q`:

| run | result | kind |
|---|---|---|
| parent 5006d7d | 1 error in collection | `ImportError: cannot import name 'replay' from 'spanweave_zoo'` — **vacuous** (new module) |
| commit 0c1e538 | 25 passed | — |

The parent run proves nothing; the mutations below carry the burden.

## 3. Mutations (each applied in the commit worktree, `pytest tests/test_replay.py`, reverted; tree clean after)

| id | diff (summary) | result |
|---|---|---|
| M1 (WORKPLAN §4's) | `replay.request`: build method/target/headers from `NNNN.headers.json` (`_d["method"], _d["path"], _d["headers"]`) instead of `head(octets)` | **caught by exactly one test**: `test_a_head_the_wire_refuses_is_not_tidied_into_one_it_accepts` — `AssertionError: a head the wire refuses was tidied and sent` (test_replay.py:524). Every other test passes, because parse == octets on every other capture in the suite. |
| M2 | `break` after the first non-2xx outcome | caught: `test_a_non_2xx_does_not_stop_the_rest_and_exits_non_zero` — `a refused send stopped the rest of the capture` (:483) |
| M3 | `sleep(min(seconds, 1.0))` | caught: `test_timing_sleeps_the_recorded_gaps...` — `assert [1.0, 1.0] == [4.0, 2.0]` (:384) |
| M4 | `seconds = abs(seconds)` before the negative check | caught: `test_a_receipt_time_that_went_backwards_is_not_slept` — `assert [5.0] == []` (:456) |
| M5 | `planned`: sort the directory (`sorted(glob)`) instead of reading manifest order | **survives** (25 passed). Equivalent on every capture the sink can make (NNNN is assigned in receipt order); see A4-3. |
| M6 | manifest order reversed `[::-1]` | caught by 5 tests incl. `test_the_bodies_go_out_in_the_order_the_capture_recorded_them` (:301) |
| M7 | `planned`: no refusal on an empty side | caught: `test_a_capture_with_no_body_on_the_chosen_side_exits_2` — `assert 0 == 2` (:563) |
| M8 | forward.py `NOT_FORWARDED = HOP_BY_HOP` (Host passed on too) | caught: 3 tests (`..._with_only_the_host_changed`, `json_side`, `gzipped`) — head bytes differ |
| M9 | `_lines`: split on CR as well (the wrong impl its docstring names) | caught: `test_head_joins_a_folded_value_as_it_arrived` (:349) and the bare-CR test (`'ValueError' in ...` fails: message became `a header line carries no colon: 'python/1.0'`, :528) |
| M10 | drop `.strip(" \t")` on values | caught: 5 tests (heads compare, `Content-Encoding:  gzip`, repeats) |

## 4. Clock / randomness / network under spanweave_zoo/
`replay.py` imports: `collections.abc`, `dataclasses`, `pathlib`, `urllib.parse.urlsplit` (string parsing only),
`spanweave_zoo.capture` (for `RAW_DIR`/`JSON_DIR` constants), `forward`, `manifest`. No socket, no clock, no random.
The only sleep is the injected `sleep` param (replay.py:323-325); `cli.run_replay` passes `_system_sleep` only when
`--timing`. The only socket is `forward.HttpForward` (http.client), which SPEC §4.3/§6.2 names. `moment_of` is
`datetime.fromisoformat`, no clock read. Note: no test gate enforces "no socket outside forward/sink"; the import gate
(tests/gates.py) covers only spanweave/spanweave_live. (Pre-existing; not new here.)

## 5. One concern / message form
`replay: <one line>`; body names A4 and SPEC sections (status line, §6.1-6.5). One concern. OK.

## 6. make check (commit worktree)
`make check` exit 0: ruff clean, ruff format clean, mypy --strict "no issues found in 8 source files",
pytest **294 passed, 3 skipped** (the 3 skips are the real-Collector tests; binary not copied in), gates 31 passed,
`zoo verify` (nothing under captures/) + `zoo verify tests/fixtures/capture` "1 capture, 2 body/bodies, 0 problem(s)".
`UV_OFFLINE=1 make install-check`: `install-check: OK -- what ships works`. CI not checked (no network used).

## 7. Specific claims

### (a) byte-identical bodies and .headers.raw into a fresh `zoo sink`
Committed fixture, raw side (`zoo sink --port 4450 --out $SP/a4/fix-again/raw`; `zoo replay tests/fixtures/capture --to http://127.0.0.1:4450` → exit 0, `raw/0001.body 200 128 bytes`):
```
IDENTICAL raw/0001.body
fixture/raw/0001.headers.raw fix-again/raw/0001.headers.raw differ: byte 43, line 2
< Host: 127.0.0.1:33131^M$
> Host: 127.0.0.1:4450^M$
```
`--json` side (port 4451): `IDENTICAL json/0001.json`; headers.raw differ only in line 2, `Host: 127.0.0.1:37027` → `Host: 127.0.0.1:4451`.

Own multi-body capture through `zoo sink --port 4452` from a raw-socket client (`$SP/a4/client.py normal`):
JSON body, gzip body (`Content-Encoding: gzip`), 512-byte binary as `application/x-protobuf`, same with a repeated
`X-Twice` header; all CRLF, Host first, `Name: value`. Replayed into a fresh `zoo sink --port 4453`: exit 0, 4×200.
All 4 bodies `cmp`-identical; all 4 `.headers.raw` differ **only** in the `Host:` port (line 2). Repeats and
`Content-Encoding: gzip` survive byte-for-byte.

So: bodies byte-identical — **confirmed**. `.headers.raw` byte-identical — **refuted as stated, confirmed modulo Host**,
which SPEC §6.2/§6.5 and §4.3 name; the committed test asserts exactly that (`with_host`, test_replay.py:202).

Edge heads (`client.py edge`, capture via port 4454, replayed into fresh sink 4455, all bodies identical) — differences
**beyond** the two SPEC names:
```
0001 Host not first:   Host line moved from line 3 to line 2 (re-ordered)
0002 'content-type:application/json' -> 'content-type: application/json'; 'X-Pad:   padded   ' -> 'X-Pad: padded'
0003 'Connection: keep-alive' dropped              (hop-by-hop: named by SPEC, expected)
0004 'POST /v1/traces HTTP/1.0' -> 'POST /v1/traces HTTP/1.1'
0005 LF-only head -> every line CRLF
```
→ finding A4-1.

### (b) --timing on a fake clock
Test: `test_timing_sleeps_the_recorded_gaps_through_the_injected_sleep` (:363), sink clock 12:00:00/:04/:06 → asserts
`sleeps == [4.0, 2.0]`, outcome.slept `[None, 4.0, 2.0]`. Gap source: `NNNN.headers.json` `received_at`
(`manifest.received_at`, via `_parsed_head`), not MANIFEST.json. Own driver `$SP/a4/timing.py` (Spy send, list sleep):

| capture | received_at | sleeps requested |
|---|---|---|
| multi (real sink clock, client slept 1.0/2.0/0.5) | 11:58:33.806260, 34.808521, 36.810332, 37.314181 | `[1.002261, 2.001811, 0.503849]` (exact differences) |
| zero gap | :00, :00, :03, :03.25 | `[0.0, 3.0, 0.25]` (sleep(0.0) is called) |
| negative | :00, :05, :02, :06 | `[5.0, 4.0]`; line `! raw/0003.body: no gap was slept: ... is before ...` |
| missing #2 | :00, None, :03, :04 | `[1.0]`; two lines (0002 and 0003 both unslept) |
| naive #2 (`12:00:01`, no offset) | | `[1.0]`; two lines |
| mixed offsets (+03:00, Z) | | `[2.0, 1.0, 1.0]` — compared as moments, correct |
All 4 bodies sent in every case; exit status unaffected (SPEC §6.3). Real CLI: `zoo replay $SP/a4/multi --timing --to :4456`
took 3.87 s; the fresh sink's received_at gaps were 1.006/2.004/0.521 vs recorded 1.002/2.002/0.504. **Confirmed.**
Edge behaviour → thread A4-4.

### (c) non-2xx reported, rest still sent
Tiny server `$SP/a4/server.py 4457 200,500,200,200`: replay printed `0001 200 / 0002 500 / 0003 200 / 0004 200`,
`4 sent, 1 that did not answer 2xx`, `! raw/0002.body: status 500`, **exit 1**; server log shows all 4 received. **Confirmed.**
Connection refused mid-way (server 4458 answers 200 then 415 then closes its listener): `0003/0004 not sent:
ConnectionRefusedError`, exit 1, summary `4 sent, 3 that did not answer 2xx`. Nothing listening (4459): all four
`not sent`, summary **`4 sent, 4 that did not answer 2xx`**, **exit 1** → finding A4-2.
Not a capture: `zoo replay $SP/a4/client.py` and `zoo replay $SP/a4` → `refusing to send ... Nothing was sent`, exit 2. **Confirmed.**
`--json` on the `zoo sink` capture (no json side) → `holds no body under json/ ... Nothing was sent`, exit 2. **Confirmed.**

### (d) WORKPLAN §4's mutation (build from .headers.json)
Caught — by **one** test only: `test_a_head_the_wire_refuses_is_not_tidied_into_one_it_accepts` (M1 above). Confirmed,
with the note that it hangs on a single bare-CR case; on the edge capture above the parse would also differ (whitespace),
but no test exercises that.

### (e) socket gate
replay.py imports no socket/http.client; it sends only through `forward.HttpForward` (`replay.sender`, asserted by
`test_the_replayer_sends_through_the_tees_own_forward`). **Confirmed.** Test-side raw sockets live in tests/ only.

## Findings

**A4-1 — the replayed head differs from the captured one in more than the two ways SPEC names.** (bin: **next batch**)
SPEC §6.5 (SPEC.md:1300-1305) says "no re-ordering. The only two differences ... are ... Host ... and the hop-by-hop
headers", and the commit body repeats it. Observed through real `zoo sink` → `zoo replay` → fresh `zoo sink`:
(1) `Host` is always emitted first (forward.py:109-112 `putrequest(..., skip_host=True)` then `putheader("Host", ...)`),
so a captured head with Host later is re-ordered; (2) value whitespace is normalized to `": "` and trimmed
(replay.py:220 `.strip(" \t")` plus http.client's `putheader` format); (3) the request line's version is forced to
`HTTP/1.1` (http.client); (4) LF-only line endings become CRLF. Bodies are unaffected. The committed test
`with_host` (test_replay.py:202) rewrites Host *in place*, so it passes only because the fixture's Host is its first
header. Impact for Z4: Python's http.client/urllib3 writes Host first, CRLF, `Name: value`, HTTP/1.1 — so a Python
exporter's capture replays identical modulo Host (as shown with the fixture). Exporters that place Host later (I believe
Node's http client appends Host after caller headers; not verified here) would be re-ordered. Fix is either SPEC stating
these normalizations (3 and 4 are http.client limits) or the forward placing Host at its captured position and the
raw splitter keeping spacing. Does not affect the capture path, so not a Z4 blocker.

**A4-2 — "nothing was sent" can exit 1 and the summary says "N sent" for bodies that were never sent.** (bin: **next batch**)
With no receiver listening, `zoo replay` prints `4 sent, 4 that did not answer 2xx` and exits 1
(cli.py:440 counts `len(outcomes)`, every planned body, as "sent"; cli.py:444). The SPEC §6.4 table (SPEC.md:1285-1286)
puts "a connection that failed" under 1, so the code matches the table, but the commit body and CHANGELOG say "2 when
nothing was sent at all", and the summary line misstates what went over the wire — exactly the line SPEC §6.4 says is
"the one that is read". A5 will run this unattended against `serve`; a summary that says "4 sent" when 0 were sent is
a reassuring line. Fix: count sends that got a status separately from bodies not sent; decide (SPEC) whether
all-failed-to-connect is 1 or 2.

**A4-3 — manifest order vs directory order is not distinguished by any test.** (bin: **thread**)
M5 (sort the directory instead of reading `bodies`) survives all 25 tests. Not a defect: on every capture the sink can
produce, NNNN order == journal order. Worth a test only if a capture can ever exist where they differ.

**A4-4 — `--timing`'s "previous" after an uncomputable gap is unspecified.** (bin: **thread**)
replay.py:326 sets `previous = recorded.received_at` whatever it was, so one missing/naive timestamp costs two gaps
(0002 and 0003 both unslept, though :00→:03 is computable), and after a backwards timestamp the next gap is measured
from the backwards value (sleeps `[5.0, 4.0]`, 9 s over a 6 s recorded span). Every such case is printed, sends still
happen, exit unaffected, so the honesty rule holds; SPEC §6.3 just does not say which moment the next gap is from.
Also: `replay(timing=True, sleep=None)` computes gaps and silently sleeps none (replay.py:323) — API only; the CLI
always passes a sleep with `--timing`.

Nothing here blocks the Z4 capture: the replayer is not on the capture path, and on a Python exporter's capture it
sends identical bodies and identical heads modulo Host.

## Cleanup
Mutations reverted (`git status --short` empty in the commit worktree after each). Worktrees removed and pruned;
`git -C /home/msi/git/spanweave-zoo status --short` empty.
