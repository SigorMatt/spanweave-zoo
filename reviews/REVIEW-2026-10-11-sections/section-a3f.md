# A3f — 46b2c15 (manifest sealed; headers.json split from the octets)

Reviewer: aux (cold). Parent derived: `46b2c15^` = `0ed7fb3` ("plan: A3e done...", a `plan:` commit; its
code is A3e's). Worktrees: `$S = /tmp/claude-1000/-home-msi-git-spanweave/0cebe00d-.../scratchpad/a3f/{head,parent,mut}`.

## Bar

| Item | Result |
|---|---|
| Spec in same commit | yes: SPEC.md status, §2, §2.3 ("The split", SPEC.md:168-189), §3.2, §5 ("The seal", SPEC.md:986-1012), §5.5, §5.6 (SPEC.md:1222-1229); CHANGELOG A3f entry; README two lines |
| Parent run (commit's 4 test files copied onto `0ed7fb3`, parent fixture kept) | **real**: 14 failed / 87 passed. The red ones are every seal test (`KeyError: 'seal'` or `assert 0 == 1` from `cli.verify`), the four split tests (e.g. `assert 'x-injected' not in [..., 'user-agent', 'x-injected']`, `['X-Weird', 'a\rb'] in [... ['X-Weird', 'a']]`), the fixture's sealed/collector.log tests and the A4 replay premise test. Green on the parent by construction (controls): `test_the_seal_is_over_the_document_and_not_its_whitespace`, `test_headers_json_is_the_crlf_split_of_headers_raw` (ordinary head), `test_each_headers_json_is_the_crlf_split_of_its_headers_raw` (ordinary fixture head: stdlib parse == split) |
| `make check` in `$S/head` | exit 0 (ruff, format, mypy --strict, pytest, gates, `zoo verify tests/fixtures/capture`: "kind=recorded, 1 body/bodies in raw/, 1 in json/, 0 problem(s)") |
| Clock / random / network | none added: `split_head` (sink.py:115-157) and `canonical`/`seal_of` (manifest.py) are pure; no new imports |
| One concern | two decisions ("the seal", "the parse") in one commit, but the A3f row bundles them and the fixture regeneration needs both. Accept; **thread** |

## Mutations (`$S/mut`, harness reverts after each; 111 tests over test_manifest/sink/fixture_capture/replay/cli)

| # | Mutation | Result |
|---|---|---|
| M1 (row's) | verify skips the seal (`return found + _incomplete(...)`, manifest.py:746) | **caught**: kind_flipped, problems_removed, file_entry_edited, no_seal, not_a_string (5 failed) |
| M2 | absent seal accepted (`if sealed is None: return []`) | caught: no_seal, not_a_string |
| M3 (CRLF split) | `split("\r\n")` -> `splitlines()` | **caught**: bare_cr, header_shaped_text_after_bare_cr, bare_lf, A4 replay premise (4 failed) |
| M6 | canonical = `json.dumps(sort_keys=True)` (default separators) on both sides | caught: seal_section_5_defines, fixture verify |
| M7 | seal omits `kind` | caught: section_5_defines, kind_flipped, fixture verify |
| M8 | headers.json from stdlib parse again | caught: 5 |
| M4 | `value.strip(_OWS)` -> `value.strip()` (strips a CR/LF at a value's edge) | **survives** (111 passed) |
| M5 | name token check removed (`if colon:`) | **survives** (111 passed) |
| M9 | OWS = SP only (tab kept) | survives |

`test_a_seal_that_is_not_a_string_fails_verify` sets `"seal": None` (test_manifest.py:675), which takes the
*absent* branch (manifest.py:758) — "not a string" is never exercised as such (a `123` would hit "differs").

## (a) Hand edits on a fresh copy of tests/fixtures/capture/ (`$S/edits.py`)

Independent seal recompute (SPEC's canonical form, my code): `6016b685...8527` == recorded. Baseline copy: exit 0.

| Edit | exit | The failing line (only line printed besides the summary) |
|---|---|---|
| `kind` recorded->real | 1 | `MANIFEST.json's seal is '6016b685...8527', its contents seal to dc574fa8...: the manifest was changed after the run sealed it` |
| `kind` deleted | 1 | seal line (`... seal to d35403d9...`) |
| `project_manifest.framework` edited | 1 | seal line (`5674e125...`) |
| `forwards[0].status` 200->500 | 1 | seal line (`582ff1b6...`) |
| `seal` removed | 1 | `MANIFEST.json has no seal, so nothing vouches for what it says about this capture (SPEC.md section 5.6)` |
| `collector.log` rewritten + its `files` sha256/bytes rewritten to match | 1 | seal line (`9e59aa87...`) — file digests agree, only the seal fails |
| `problems: ["x"]` added and resealed by hand (a capture "with a problem") | 1 | `MANIFEST.json records a problem from the run: x` (the problem check, not the seal) |
| ...then `problems` removed, not resealed | 1 | seal line (`seal is '69d2eb7a...', its contents seal to 6016b685...`) |
| ...then `problems` removed **and resealed** | **0** | `0 problem(s)` |
| `kind`->real resealed / file+entry resealed / `kind` deleted resealed / forward 500 resealed | **0** each | "every recorded body still hashes to what was recorded" |

The unit test covers the honest variant (stale/missing project manifest -> real `problems` entry, test_manifest.py:624-634).
Each failure above is the seal line: the per-capture line shows `1 problem(s)` and the `!` line is the seal's.

**The seal is a checksum against accident and naive edits, not authentication**: anyone who reads SPEC §5 can
reseal, and a resealed edit verifies 0. SPEC does not say that limit, and two sentences claim more:
SPEC.md:1010 "A seal cannot be added to a capture after it is taken" (it can — that is a rule, not a property;
I added one in 1 line) and WORKPLAN §3 "the seal": "`kind`, `problems`, `project_manifest` and the file list
**cannot be changed by hand afterwards**" (they can, with a reseal). **F-a1 — next batch:** one SPEC sentence that
the seal detects accidental or naive edits only, is not a signature, and that "cannot be added afterwards" is the
zoo's rule. Does not block Z4 (honest captures come out right).

N-1 still live and visible here: the closing line for a recorded problem says "these bytes are not the bytes that
were recorded" — prior finding, not A3f's scope.

## (b) `otel\rX-Injected: yes` — live `zoo sink` on a free port (`$S/live.py`, port 33041), raw socket POSTs

- `0001.headers.raw` byte-identical to what was sent (compared as bytes).
- `headers.json`: `["User-Agent", "otel\rX-Injected: yes"]`; **no `X-Injected` key**; `unparsed` absent. N-2's json half: fixed.
- `User-Agent: otel\rContent-Encoding: gzip`: headers.json `["User-Agent", "otel\rContent-Encoding: gzip"]`;
  manifest body entry `content_encoding=None` (it now reads the split). N-2's manifest half: fixed.
- `X-A: a\rContent-Type: text/evil` with no real Content-Type: manifest `content_type=None`; the stdlib parse
  sees `Content-Type: text/evil` and that is what the sink echoes (§3.3 — handled-with, as SPEC §2.3 says).

**The forward still carries the invention.** (1) Recorder + `HttpForward` into my own socket listener
(`$S/fwd.py`): the "Collector" received
`...Content-Length: 5\r\nUser-Agent: otel\r\nX-Injected: yes\r\n\r\n` and, for the second,
`...User-Agent: otel\r\nContent-Encoding: gzip\r\n\r\n`, while headers.json says neither header was sent.
(2) A real `zoo capture` with the stock Collector 0.162.0 (`$S/realtee.py`, three POSTs of tests/otlp.py's body):
`! raw/0003.body forwarded, collector said 400`; manifest `forwards: [..., {'file': 'raw/0003.body', 'status': 400}]`
against a body entry with `content_encoding: None`; `zoo verify` exit 0. A reader (A5) sees "the Collector refused
an un-encoded protobuf body" when the 400 was caused by a `Content-Encoding` the zoo's forward asserted from the
stdlib's parse. **F-b1 — next batch** (with N-3, the head-parse family): forward from the split, or record in
`forwards` that the forwarded head differed from `.headers.raw`. Does not block Z4: Python's `http.client`
refuses a CR/LF not followed by whitespace in a header value, so a Python exporter cannot emit this head.

## (c) The unparsed-line rule

SPEC.md:176-185, verbatim:
> Every **later non-empty line** is a header if what precedes its first colon is a non-empty field-name token
> (RFC 9110 §5.6.2: letters, digits and ``!#$%&'*+-.^_`|~``). Its pair is `[name, value]`: the name as sent, the
> value as sent with the spaces and horizontal tabs around it removed (RFC 9110 §5.5's optional whitespace, which is
> not part of a value) — a CR or LF inside it stays. Pairs are in the order received, repeats included.
> Every **other non-empty line** — a continuation line (RFC 9110's obsolete line folding), a line with no colon, a
> line whose name is not a token — is no header and is not joined to one. It is listed verbatim, in order, under
> `unparsed`, which is **absent** when there is none.

Live sink results (all answered `200` by the stdlib; `.raw` byte-identical in all 16 cases):

| Head line(s) sent | headers.json | unparsed |
|---|---|---|
| `X-Fold: a` + `\r\n b` (obs-fold SP) | `["X-Fold","a"]` | `[" b"]` |
| `X-Fold: a` + `\r\n\tb` (obs-fold HTAB) | `["X-Fold","a"]` | `["\tb"]` |
| `no colon here` | — | `["no colon here"]` |
| `: v` (empty name) | — | `[": v"]` |
| `Name : v` (WS before colon; RFC 9112 §5.1 MUST reject with 400 — the stdlib accepted) | — | `["Name : v"]` |
| `X(Y): v` (non-token) | — | `["X(Y): v"]` |
| `X-A: a\nb` (bare LF) | `["X-A","a\nb"]` | absent |
| `X-L: caf\xe9 \xff` (Latin-1) | `["X-L","café ÿ"]` (`\u00e9`, `\u00ff`; recoverable by latin-1 encode) | absent |
| `X-E:` / `X-E:   \t ` (empty value) | `["X-E",""]` both | absent |
| `X-T: a\r` (CR at value end) | `["X-T","a\r"]` | absent |
| `X-T:\ra` (CR at value start) | `["X-T","\ra"]` | absent |
| **LF-only head** (`split_head` direct): `POST /v1/traces HTTP/1.1\nHost: x\nContent-Type: ...\n\n` | `[]` | **absent** |
| mixed (one CRLF after Content-Type, rest LF; live, 0015) | `["Content-Length","5\nConnection: close\nUser-Agent: lf\n\n"]`; Host and Content-Type **in no field** | **absent** |
| `POST /v1/traces HTTP/1.1 extra junk` | path `/v1/traces`; ` HTTP/1.1 extra junk` in no field | absent |
| `POST  /v1/traces HTTP/1.1` (double SP) | `path: ""` (the stdlib routed it to `/v1/traces`) | absent |

Judgement:
- **Lossless** for the record: every head octet is in `.headers.raw` (byte-identical in all cases), and the Latin-1
  decode is invertible. Header lines are honest: every non-header line is listed.
- **Trimming is fine**: RFC 9110 §5.5 says OWS is not part of the value, so stripping it is the parse, not an
  improvement; `.raw` is the record and SPEC §2.3 says so. Only SP/HTAB are stripped (CR at an edge stays — shown
  live; but no test holds it: M4 survives).
- Obs-fold: `["X-Fold","a"]` is the first line's value only; the `unparsed` entry is the signal. Acceptable
  (not joining is the no-improvement choice), **thread**: SPEC could say a reader must look at `unparsed` before
  trusting a value.
- **F-c1 — the request line is not covered by the rule: next batch.** `split_head` keeps method and the first
  token after it (sink.py:138-139) and discards the rest of `lines[0]` without listing it. For an LF-only head the
  whole header block is inside `lines[0]`: headers.json says `headers: []`, no `unparsed`, and the manifest says
  `content_type: null` — the json now *omits* without saying so, the mirror of N-2. Same for a request line with
  trailing text, and the HTTP version is in no field. Not Z4-blocking (Python clients send CRLF). Fix: list any
  request-line remainder beyond `method SP target SP version` (or the whole request line when it is not that shape)
  under `unparsed`, or record `request_line` verbatim.
- **F-c2 — test gaps: next batch.** The token rule (M5) and "a CR or LF inside it stays" at a value's edge (M4)
  are unheld; `Name : v` and `X-T: a\r` would each change behaviour silently. The "not a string" seal test uses
  `None` (absent branch).
- **"Absent when empty"**: consistent with `problems` and the `forwards` key, so keep it — but only once F-c1 is
  fixed, because today absence is read as "everything was parsed" and the LF-only case shows that is false.

## (d) Fixture regeneration

- `raw/0001.body` sha256 `abb3460ed37754be...` at `46b2c15^` and at `46b2c15`; `json/0001.json` `403f27e12d267575...`
  both. Byte-identical.
- Diff vs A3d: dates 10->11, ports in Host lines (raw .raw/.json and json .json), headers files' digests,
  `collector.log` added, `seal` added. Nothing else. Every `headers.json` equals `split_head(.raw)` + bytes/received_at
  (`test_each_headers_json_is_the_crlf_split_of_its_headers_raw`, green in make check). Seal recomputed independently: matches.
- **Thread:** `collector.log` carries the Collector's own wall clock and the maintainer's zone
  (`2026-10-11T19:20:46.047+0300`) and a random `service.instance.id`, while the commit says "on a chosen clock
  (2026-10-11T09:00:0N)". The record is honest; the sentence is partial.
- **Thread (pre-existing, also in A3d's fixture):** `project_manifest.started_at` 09:00:30 is *after* the capture's
  `ended_at` 09:00:04. The F4 check is one-directional, so an impossible project manifest verifies.

## (e) Unsealed manifests in the wild

`git ls-files | grep MANIFEST` -> only `tests/fixtures/capture/MANIFEST.json` (now sealed); `captures/` does not
exist in the checkout; `find / -path '*captures*' -name MANIFEST.json` outside scratchpads -> only pytest/tmp dirs.
No capture affected. A3d's fixture at older commits fails verify if checked out — expected by the decision.

## Bins

| Id | Finding | Bin |
|---|---|---|
| F-a1 | SPEC/§3 overclaim the seal ("cannot be added", "cannot be changed by hand"); a hand reseal verifies 0 | next batch |
| F-b1 | forward sends the stdlib parse: CR-injected `X-Injected`/`Content-Encoding: gzip` reach the Collector; real Collector 400 recorded against an un-encoded body | next batch |
| F-c1 | request-line remainder / LF-only head silently dropped from headers.json; `unparsed` absent | next batch |
| F-c2 | M4, M5 survive; "not a string" test is the absent branch | next batch |
| — | obs-fold note; two concerns in one row-sanctioned commit; collector.log clock sentence; project started_at after ended_at | thread |

Nothing blocks Z4 capture.

Cleanup: worktrees `$S/{head,parent,mut}` removed (`git worktree remove --force` + `prune`); every sink, capture and
Collector I started exited (my real tee's Collector stopped with `zoo capture`); the running `otelcol` under
`scratchpad/a4a/` is another reviewer's and was left alone.
