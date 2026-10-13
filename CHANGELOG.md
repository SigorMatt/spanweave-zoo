# Changelog

Pre-release. Nothing here is frozen: the CLI, the capture layout and
`MANIFEST.json` all still move. Entries are by batch id (`TASKS.md`'s registry; while a series is open, its
`WORKPLAN.md` §1).

## B7r — every captured project audited once more, with the one audit

`zoo audit` on Z4's, Z3's and Z5's six captures with B6a's audit (`07285bd`),
at the `audit` extra's pins (unchanged). No `SPEC.md` section touched, no code
or test changed, no capture touched (`make verify` green).

- **Reports replaced:** the six `audit/z{4,3,5}-*-{real,recorded}.md`,
  rewritten in place by `zoo audit` (same filenames; no old report kept beside
  a new one), exit 0 each. Findings unchanged: Z4 3 each, Z3 1 each, Z5 1 each.
- **Re-run determinism:** a second run of all six, into the scratchpad,
  differs from the committed reports only in the `listening` ports and the
  clock readings of `completed` and `late_arrival` events — identical line for
  line once those are normalised. No finding about the audit's method.
- **`PROBES.md`:** every probe cites the re-audit; observations marked
  *(B7r)*. Moved from *to establish* / *not observable* to observed: L3
  (`--quiet 0` completes Z3 real four times, once per body, three
  `late_arrival`s; `--root-grace 0` once, by `RootEnded`, at the last
  record), L4 (`Quiet(0)` completes Z5's rootless trace; under
  `--root-grace 0` the end-of-input `Cap(0)` does, never `RootEnded`), S5 and
  S9 (which nodes carry `unpaired_call`), S10 (the nine `llm:-` steps are the
  nine `llm` nodes with no `model` in the graph), S11 (both `http_get` nodes
  status `error`, one `exception` event each), S12 (which two nodes are
  orphaned). Observed further, still partly *to establish*: L2 (Z4 under each
  policy), S2, S3, S6, S13; S8 stays (the node table names codes, not keys).
  No new probe, no new finding; counts and the
  pins paragraph restated.
- **`ROADMAP.md`:** Z3's, Z4's and Z5's rows cite the re-audit.

## B6a — the audit observes every policy and names every node

`OPEN_QUESTIONS.md` §8, option 1 over a timed replay (the maintainer's decision
of 2026-10-13). `SPEC.md` §7.3, §7.5, §7.6. No capture touched, neither pin
moved; the committed `audit/*.md` reports are not regenerated here (B7r).

- **Step 2 runs `serve` three times.** The end-of-input run (`--requests N`,
  untimed) as before, still the one step 3 compares; then `--quiet 0
  --requests N` and `--root-grace 0 --requests N`, each replayed with
  `--timing`. Per policy run the report tables every `completed`,
  `late_arrival`, `written` and `released` event -- trace, index, generation
  (counted from the receiver's events, which carry none) and reason (a
  `completed` detail's clause before its first colon) -- with the `finished`
  event, every body's status and the gap slept before it, and every event
  verbatim. The Method says the zeros are the audit's values: the pinned
  receiver documents no default. The policy runs yield no finding; one that
  could not be completed is an incomplete step (exit 1).
- **Step 4 adds a row per node**: id, kind, status, model, parent present
  (yes / no / absent from graph), the diagnostic codes naming it, and its span
  events as the record carries them (the record's `events`, verbatim as
  compact sorted JSON beneath the table, or *absent*).
- **`audit.audit()` takes a `sleep` seam**, keyword, no default; `cli.py`
  passes the one real `time.sleep`. A capture's timed runs take as long as
  its captured gaps: Z3's `real` audit now takes about 23 s, the others
  about a second.
- Tests: through the `serve_command` seam, the four `serve` argvs (step 1's,
  then step 2's three with their flags) and the captured gap slept on exactly
  the two policy runs; the policy table's reasons and generations, and the
  generation count on a crafted event stream (`forgotten` restarts it); a
  graph with one ERROR node whose row carries `error`, its model, `absent
  from graph` and its events; a node stating no parent and carrying no
  events; a row for every node of Z4's `recorded` report. Red on the parent.
- Mutations shown caught: the policy runs replayed untimed (no gap slept);
  the status cell not read from the node (`unset` for the ERROR node).

## B5c — a folded `Content-Length` is unframeable

B5b's open case; the maintainer's decision of 2026-10-13. `SPEC.md` §3.3,
§3.7. No capture touched; the sink still decodes no framing, and
`NNNN.headers.json` is derived as before.

- **A `Content-Length` continued on a folded line** (obs-fold: the next line
  of the head begins with a space or a tab) is unframed: a zero-byte body, the
  usual answer with `Connection: close`, the connection closed. Before, the
  stdlib joined `Content-Length:` CRLF ` 5` into `5` and the body was read by
  a length the record does not show -- there the header is empty and ` 5` is
  `unparsed`.
- **`SPEC.md` §3.7's table** gains the row.
- Tests: three folded cases (empty then a space fold, empty then a tab fold,
  digits then a fold), each followed on the connection by a well-formed POST
  that must not be read, with the head's split asserted unchanged -- the first
  two red on the parent, the third green on it by design (its joined value was
  never digits); one guard, a fold on another header keeps the connection.
- Mutations shown caught: recognising only a space as a fold (the tab case
  fails); treating a fold after any header as unframed (the guard fails).

## B5b — a `Content-Length` is digits, once

Review of B5a's remainder; the maintainer's decision of 2026-10-13. `SPEC.md`
§3.3, §3.7. No capture touched; the sink still decodes no framing.

- **A `Content-Length` is `1*DIGIT` and nothing else** (RFC 9110 §8.6), once
  the spaces and tabs around it are removed. `+5`, `5_0`, and a `5` beside
  whitespace that is not a space or tab are unframed: a zero-byte body, the
  usual answer with `Connection: close`, the connection closed. Before,
  `int()` read each as a length and the octets after the body were parsed as
  the next request.
- **Two `Content-Length` headers that differ are unframed** the same way.
  Before, the first one won. Identical repeats are one length and keep the
  connection, as before.
- **`SPEC.md` §3.7's table** gains the rows; "not a number" and "negative"
  are now one row, "not `1*DIGIT`".
- Tests: five unframed cases (`+5`, a vertical tab before the `5`, `5_0`,
  `5`/`6` and `6`/`5`), each followed on the connection by a well-formed POST
  that must not be read -- all red on the parent; three kept-connection
  guards (identical repeats, identical up to whitespace, trailing
  whitespace), green on the parent by design.
- Mutations shown caught: reading only the first header (2 cases fail);
  treating any repeat as unframed (2 guards fail).

## B7-Z5 — Z5 (`flaky-fetcher`) audited

`zoo audit` on `captures/z5/2026-10-13-real` and `captures/z5/2026-10-13-recorded`,
at the `audit` extra's pins (unchanged). No `SPEC.md` section touched, no code
or test changed, no capture touched (`zoo verify` green on both before the audit).

- **Reports:** `audit/z5-2026-10-13-real.md` and `audit/z5-2026-10-13-recorded.md`,
  as `zoo audit` wrote them (default `--out audit`), exit 0 each. One finding
  each: the `raw/` body answered 415 (spanweave-live).
- **Graphs:** one trace per capture, 4 records (`chain` 2, `tool` 2, no `llm`,
  no root), live = batch = incremental byte for byte (17,691 bytes); every
  record claimed by `openinference`; step 5 clean.
- **`PROBES.md`:** L1, S3 and S7 seen again in Z5; new L4 (no root: one
  completion, the end-of-input `Cap(0)`; `Quiet` and `RootEnded` not exercised
  by the audit), S11 (two `http_get` tool nodes; `<record>.events` unmapped; no
  status shown), S12 (`orphan_parent` × 2), S13 (real and recorded bodies
  differ in 380 of 5,934 bytes; graphs equal in size, not byte-identical —
  trace ids differ). Observations only; the open ones are marked *to establish*.
- **`ROADMAP.md`:** Z5's row reads audited.

## B7-Z3 — Z3 (`echo-planner`) audited

`zoo audit` on `captures/z3/2026-10-13-real` and `captures/z3/2026-10-13-recorded`,
at the `audit` extra's pins (unchanged). No `SPEC.md` section touched, no code
or test changed, no capture touched (`zoo verify` green on both before the audit).

- **Reports:** `audit/z3-2026-10-13-real.md` and `audit/z3-2026-10-13-recorded.md`,
  as `zoo audit` wrote them (default `--out audit`), exit 0 each. One finding
  each: every `raw/` body answered 415 (spanweave-live). A second run differs
  only in the `listening` port and a `completed` event's clock readings (§7.3).
- **Graphs:** one trace per capture, 102 records, live = batch = incremental
  byte for byte; every record claimed by `openinference`; step 5 clean.
- **`PROBES.md`:** L1 and S3 seen again in Z3; new L3 (root in the last of four
  bodies: one completion, at the end of input), S6 (two instrumentors: 50 `llm`
  nodes), S7 (unmapped OpenInference keys, 363 kB), S8
  (`droppedAttributesCount` on 18 nodes; the 599 SDK lines are not in the
  capture), S9 (`unpaired_call` × 48), S10 (nine `llm` steps with no model).
  Observations only; the open ones are marked *to establish*.
- **`ROADMAP.md`:** Z3's row reads audited.

## B5a — a request with `Transfer-Encoding` is never read by its `Content-Length`

Review of B5's remainder; the maintainer's decision of 2026-10-13. `SPEC.md`
§3.3, §3.7. No capture touched; the sink still decodes no framing.

- **Any `Transfer-Encoding` makes a POST unframed**, whatever its
  `Content-Length` says: a zero-byte body, the usual answer with `Connection:
  close`, and the connection closed. Before, a POST carrying both headers with
  a positive length was read by that length -- the first octets of its chunk
  frames recorded as the body and the rest parsed as the next request (a stray
  `400`/`501`, or a second request nobody sent).
- **A negative `Content-Length` closes too**, with or without
  `Transfer-Encoding`. Before, with none, it was a zero-byte body on a kept
  connection, and the octets after it were read as the next request.
- **`SPEC.md` §3.7 now has a table** of every framing case and its outcome.
- Tests: a POST with both headers followed by its chunk frames and a
  well-formed POST on one connection, a negative length alone likewise, and
  three new framings in the unframed parametrization (positive with
  `chunked`, positive with another `Transfer-Encoding`, negative alone) -- all
  red on the parent.
- Mutation shown caught: dropping the `Transfer-Encoding` check (4 cases
  fail).

## B4a — the replayer refuses a path outside the run

`OPEN_QUESTIONS.md` §7, option 1. `SPEC.md` §5.4, §6.1, §6.4, §6.5, §7.2. No
capture touched; every bad manifest in the tests is on a copy in a tmp dir.

- **`zoo replay` applies B4's path rule before reading anything** (`SPEC.md`
  §6.1): every `file` entry of `bodies` and `files`, on the side it sends and
  the side it does not, goes through `manifest.outside_run` -- the function
  `verify` uses, now public, with `manifest.misplaced` listing the entries.
  An absolute entry, a non-normalized one (`..`) or one resolving outside the
  run through a symlink is a refusal naming the entry, exit 2, nothing read
  and nothing sent. Before, `raw/../../outside.body` passed the `raw/` prefix
  filter and was sent (exit 0), and an absolute entry was refused only by
  accident, without being named.
- **The audit is unchanged**: such a run fails `verify`, so §7.2 already
  refuses it before step 1; a new test asserts the refusal names the entry
  (an absolute and a `..` entry, on fixture copies).
- Tests: 12 replay cases (absolute and `..` on the raw and json sides, a `..`
  in `files`, a symlink out; each sent `--raw` and `--json`) red on the
  parent, a check that `planned` reads no body or head before refusing, and
  the committed capture yielding no misplaced entry.
- Mutation shown caught: checking only the side being sent (8 of the 12
  cases fail).

## B2b — the per-body cost is a count, not a clock

`test_sixteen_hundred_bodies_cost_the_same_each` failed on the macOS leg again
at `7275b12`, on CPU time this time (510 -> 1,333 us/body). No capture touched;
the bytes the recorder writes are unchanged.

- **A new seam, `open_file`** (`SPEC.md` §3.6): the recorder opens every file
  it writes to record a body -- the body, both headers files, the journal
  append -- through it, binary. The default is the real filesystem.
- **What a body costs** is defined once, in §3.6: the files opened through the
  seam for that body, each as mode, octets read, octets written. The test
  records 1,600 bodies through a counting seam and asserts body 1,600's cost
  **equals** body 1's. A `sys.addaudithook` watch fails the test if the
  recorder opens a file under the run any other way while recording, so a
  rescan cannot bypass the count. No time is measured or asserted.
- Mutation shown caught: B2a's O(n) rescan of the journal in
  `manifest._journal`, both outside the seam (a bypassed open) and through it
  (body 1,600 reads 185,484 octets, body 1 reads none).

## B6 — the audit says "not run" when it cannot vouch

Qodo Q4, Q5 (`TASKS.md`, "Series 2"). `SPEC.md` §7.3, §7.5, §7.6.

- **(a) A step-3 reconstruction that does not match `serve` runs nothing
  after it** (`SPEC.md` §7.3). When the in-process re-read's statuses are not
  `serve`'s answers, or its record count is not `serve`'s `routed`, no
  partition is compared and steps 4 and 5 are not run: the report renders
  steps 3, 4 and 5 as *Not run*, step 3 naming the difference, and none of
  them yields a finding; exit 1. Before, step 3 was marked incomplete and its
  findings, `inspect` and the signature smoke were emitted anyway. Steps 1
  and 2's findings stand.
- **(b) A `serve` command that cannot be executed is `serve did not start`**
  (`SPEC.md` §7.5): `Popen` raising `OSError` becomes that step's problem
  (`serve did not start: FileNotFoundError: …`), the report is still written,
  exit 1. Before, the `OSError` escaped and no report was written.
- **A `reread` seam** on `audit.audit()` (`SPEC.md` §7.6), default the
  module's `reread`, so a test drives the mismatch without a defect in
  spanweave-live.
- **Tests** (`tests/test_audit_real.py`, `needs_audit`): statuses that do not
  match, and one record fewer than `routed`, each through the seam on the Z4
  `recorded` capture — exit 1, no step ≥ 3 finding, steps 3–5 *Not run*, no
  `inspect` in the report; a nonexistent serve command — exit 1, both serve
  steps `serve did not start: `, steps 3–5 *Not run*, the report written, and
  `zoo audit` through the CLI exits 1 with the report on disk. All three red
  on the parent.
- **Mutation shown caught**: `found = None` in the mismatch branch replaced by
  `pass` — both mismatch tests are red (step-3 findings emitted).

## B5 — the wire is honest at its edges

Qodo Q9, Q11, Q3 (`TASKS.md`, "Series 2"). `SPEC.md` §3.3, §3.7, §4.3, §6.2,
§6.3.

- **(a) A POST the sink cannot frame closes its connection** (`SPEC.md` §3.3,
  §3.7). No `Content-Length`, a non-numeric one, or a non-positive one with a
  `Transfer-Encoding` beside it: still recorded as a zero-byte body and
  answered as before, now with `Connection: close`, and the connection is
  closed after the answer. Kept alive, a chunked POST's chunks were read as
  the next request line and drew a stray `400`. The sink still decodes no
  framing (decision of 2026-10-12, B5(a)); B3's no-answer close after the
  journals close is unchanged. `Content-Length: 0` with no
  `Transfer-Encoding` keeps its connection.
- **(b) An IPv6 literal is bracketed in `Host`** (`SPEC.md` §4.3, §6.2):
  `forward.authority` writes `[::1]:4318`, used by `zoo replay`'s send and by
  `HttpForward`. Before, `--to http://[::1]:4318` sent `Host: ::1:4318`.
- **(c) `replay --timing` measures each gap from the body before it in the
  capture, sent or not** (`SPEC.md` §6.3): a body whose head cannot be read
  still advances the previous receipt to its own `received_at` (or to none,
  when that is unreadable too, and the next gap is said not computed).
- **Tests**: `tests/test_sink.py` — a chunked POST then a well-formed one on
  one connection is one body, one `200`, `Connection: close`, no `400`; each
  unframed shape (no length, `five`, `0` + TE, `-3` + TE) likewise; the
  rejected side (`404`) likewise; `Content-Length: 0` keeps the connection.
  `tests/test_replay.py` — `--to http://[::1]:<port>` into a real IPv6
  listener receives `Host: [::1]:<port>`; `forward.authority`;
  `HttpForward("::1", …)`; a skipped first and a skipped middle body; a
  skipped body with no `headers.json`. All red on the parent except the
  keep-alive guard.
- **Mutation shown caught**: `if self._unframed:` in `_answer` replaced by
  `if False:` — the chunked test and the five unframed cases are red.

## B4 — `verify` trusts nothing a manifest says about where a file is

Qodo Q10, Q12 (`TASKS.md`, "Series 2"). `SPEC.md` §5.4, §5.6.

- **A list that is not a list is a problem, not a `TypeError`**: `"files": 1`
  and `"problems": 1` used to crash `zoo verify` (in `_listed` and
  `_incomplete`); each is now one line (`'files' is not a list`, `'problems'
  is not a list`) and a non-zero exit, as `_rehashed` already did.
- **A `file` entry is a normalized relative path under the run directory**
  (`SPEC.md` §5.4): one that is absolute, has a `.`/`..`/empty part, or —
  symlinks followed — resolves outside `run.resolve()` is a problem naming
  the entry, and the file it points at is **not read**. Before, a resealed
  manifest listing an outside file with its correct digest verified. The seal
  decision of 2026-10-11 stands: a resealed manifest still verifies, within
  the run directory.
- **Tests** (`tests/test_manifest.py`): `"files": 1`, `"problems": 1`, an
  absolute entry, a `../../../` entry and a symlink out (each resealed, each
  asserting the outside file is never read), a `raw/../raw/0001.body` entry
  that lands back inside; all red on the parent. A symlink that stays inside
  the run directory still verifies.
- **Mutation shown caught**: the lexical checks kept and the
  `resolve().is_relative_to(run.resolve())` check removed — the symlink case
  verifies (exit 0) and is red.

## B3a — standalone `zoo sink` seals only once nothing can write

B3's close-then-seal extended to `run_sink` (decisions log 2026-10-13: "nothing
writes after the seal" has no exception). `SPEC.md` §3.3, §3.7, §5.5.

- **`zoo sink` stops in B3's order**: the loop returns and the listening socket
  is closed, every POST still being handled is waited for (the bound
  `zoo capture` uses, `capture.FLUSH_WAIT`, 10 s), the recorder's journals are
  closed (`Recorder.close`, B3's mechanism, not a second one), and only then is
  the manifest assembled and sealed. Before, it sealed while a handler could
  still write a body and a journal line into the sealed run.
- A POST still being handled at the close is a `problems` entry
  (`a POST not yet recorded: still being handled when the journals closed; …`,
  or the body it had recorded), printed as a `!` line after
  `zoo sink: stopped.`; the late body is recorded nowhere and answered nothing.
- **`zoo sink` exits 1** when the sealed manifest records a problem (that one,
  or an unreadable journal line `finish` reported, which it used to ignore), 0
  otherwise — as `zoo capture` does.
- **Test**: `test_a_post_the_standalone_sink_outwaits_writes_nothing_after_the_seal`
  holds a POST in `before_record` past a shortened bound; every sealed file is
  byte-identical after it is released, it gets no answer, and `zoo verify`
  fails on that one problem only. Red on the parent (sealed at 0 bodies, then
  `raw/0001.body` written and answered `200`).
- **Mutation shown caught**: `run_sink` without the `recorder.close()` call
  (the wait kept) — the late handler is answered `200` and writes after the
  seal.

## B2a — the per-body cost test measures the recorder, not the runner

The registry's "macOS wall-clock cost test" (`TASKS.md`, series 1), failed
again at B2's first CI run. Tests only: no behaviour change, `SPEC.md` §3.5
(the claim under test) unchanged, no capture touched.

- **`test_sixteen_hundred_bodies_cost_the_same_each`** times each body's
  `record` call by **CPU time** (`time.process_time`), not by wall clock, and
  compares the **median** of the first hundred bodies of a 1,600-body run with
  the median of the last hundred. The bound stays (last < 2.0 × first); the
  method and the bound are stated in the test's docstring.
- **Mutation shown caught**: an O(n) rescan of the journal per body (each
  append first re-reads and parses every line already written) — median
  561 → 3,870 µs/body, ratio 6.89, red. Unmutated: ratio 1.04–1.16.

## Between runs: export contract 1.3, the Z5 brief amendment, ROADMAP rows for Z3 and Z5

Docs only: no behaviour change, no capture touched.

- **`EXPORT-CONTRACT.md` 1.2 → 1.3**, from Z3's and Z5's reports: the real
  run is the operator's, not the implementer's (§1, §5); `MANIFEST.json` is
  written before the first model call (§1); §4 states the gateway's surface
  (chat completions with tools and streaming) and that a model id may contain
  `/` and is passed through unchanged; a closing "Changes from 1.2" paragraph.
- **`ZOO-BRIEFS.md`, Z5**: the retry edge backs off a scripted 3 s, the same
  in both modes, so a run that exits via `os._exit` outlasts the batch
  processor's delay.
- **`README.md`, Provenance**: both documents' new sha256s, "contract version
  1.3", Z4's 1.0 described as 1.3 minus all three closing change sections,
  and Z3 and Z5 named as built against 1.2.
- **`ROADMAP.md`**: the Z3 and Z5 rows filled (repository, contract,
  captures; not yet audited), and two operating notes — the Agents SDK's
  reading of `vendor/` in a model id, and the batch processor exporting
  nothing from a short run that exits via `os._exit`.

## B3 — nothing writes to a capture after its seal

Qodo Q2, Q7 (`TASKS.md`, "Series 2").

- **`SPEC.md` §4.6, §5.5**: `zoo capture`'s shutdown waits for the raw sink's
  handlers a second time, as long, after the Collector's stop has failed the
  forwards still waiting on it, and then **closes both recorders' journals**
  before it assembles the manifest. A recorder that is closed writes nothing:
  a forward that completes afterwards is journalled nowhere and is in no list
  (Q2), and a body that arrives afterwards is recorded nowhere. A POST still
  being handled at the close is one `problems` entry naming its body (or
  `a POST not yet recorded`) and one `!` line (§4.2). So a capture whose
  forward outlived every bound is sealed, every digest holds, and `zoo
  verify` names the one problem the run recorded.
- **`SPEC.md` §3.3**: a POST that reaches a closed recorder is not answered —
  the connection is closed with no status, since `200` means "recorded".
- **`SPEC.md` §5.5, §5.6**: the journals are decoded a line at a time; a line
  that is not UTF-8 is a `problems` entry naming the journal and the line,
  like a line that is not a JSON object, and `finish` still writes `ended_at`
  and the seal (Q7).
- **Tests**: a forward held past the flush bound (injected `flush_wait` and a
  forward the test releases) completes after the seal and leaves every file
  byte-identical, `verify`'s only line the recorded problem; a byte `0xff` in
  either journal yields a sealed, complete manifest listing the problem; a
  POST to a closed recorder writes nothing and is not answered.

## B2 — signals cover the whole life of a capture, and of the sink

Qodo Q1, Q6, Q8 (`TASKS.md`, "Series 2").

- **`SPEC.md` §4.6**: `zoo capture` installs its stop handlers **before** it
  starts anything. A `SIGINT`, `SIGTERM` or `SIGHUP` during the readiness wait
  ends the start as a refusal does — the Collector (its own session, A3e)
  stopped, both sinks closed, `refusing to start: <signal> arrived before the
  capture was ready …`, exit 2, no run directory. From the moment the run
  directory is made a signal only asks the run to stop. Every step of the
  start after the Collector is up — its log, the clock, the label, serving,
  the readiness line — is inside the same unwind that stops it (Q8). The
  launcher stops the child on any way out from the moment it exists, not only
  from its readiness wait.
- **`SPEC.md` §3.7**: `zoo sink` stops on `SIGTERM` and `SIGHUP` as on Ctrl-C:
  `serve_forever` returns, and the manifest is assembled and sealed (Q6).
  §5.5 says a failure anywhere in the start unwinds through `stop()`.
- **Tests**: a stop signal (each of the three) while the stand-in Collector is
  bound and not yet ready leaves no Collector process and no run directory,
  exit 2; a `manifest.label` that raises stops the Collector and closes both
  sinks; a readiness line that cannot be printed still ends in a sealed
  capture; `SIGTERM`/`SIGHUP` to a standalone `zoo sink` give a sealed,
  verified manifest. The `slow` stand-in and `ZooCapture(becoming_ready=True)`
  are the harness for the readiness window.

## B1 — the test harness does not lose a port race

`OPEN_QUESTIONS.md` §6, option 4: no product change. `zoo capture` still picks
no port and refuses a held one (`SPEC.md` §4.6).

- **`SPEC.md` §4.2, §4.6**: `--port 0` and `--json-port 0` — already accepted —
  are stated: a port the kernel chooses, read back from the two lines after
  the readiness line. `--collector-port` is not given that meaning.
- **`tests/ports.py`** (new): the suite's one `free_port()` pick, and a
  bounded retry (5) of a whole start whose refusal names an address in use,
  logging every port tried and failing after the last naming them all. Any
  other refusal is not retried.
- **`ZooCapture`** (`tests/test_shutdown.py`) passes `--port 0 --json-port 0`
  and reads the bound ports back; it picks only the Collector's two ports,
  through the retry, and is up when constructed. The in-process captures in
  `test_shutdown.py`, `test_collector_real.py`'s protobuf test and
  `test_capture.py`'s ready-Collector test start through the same retry.
- **Tests**: a Collector port held under the first pick is picked again and
  the run reaches readiness; sinks on `0` print two ports a test POSTs to; a
  refusal naming no address in use is not retried; the retry is bounded and
  names every port tried.

## B0 — the two reviews of the close, archived and dispositioned

Docs only: no behaviour change, no capture touched, no `SPEC.md` section.

- **`reviews/QODO-2026-10-12.md`** (new): Qodo's review of PR #1 (comment
  `6127903067`), byte for byte — the API's `body` without the trailing newline
  `gh api --jq .body` adds. Its sha256 appended to `reviews/SHA256SUMS`, now
  26 files, `sha256sum -c` green.
- **`TASKS.md`, "Series 2"**: Qodo's twelve items Q1–Q12 and the close
  review's two carried threads (the port race, the PR wording), each pointing
  at the batch that closes it.

## Between series: export contract 1.2 and ROADMAP.md

Docs only: no behaviour change, no capture touched.

- **`EXPORT-CONTRACT.md` 1.1 → 1.2**: the manifest gains `base_url`, and
  `started_at` is UTC with `Z`, taken before the first model call; §3 adds
  that a real run the gateway breaks is not the capture, and that a manual span
  carries only the attributes its brief lists; §4's credentials bullet names
  `OPENAI_API_KEY`/`OPENAI_BASE_URL` and `MODEL=` against a named
  OpenAI-compatible gateway; a closing "Changes from 1.1" paragraph.
- **`README.md`, Provenance**: the contract's new sha256, "contract version
  1.2", and Z4's 1.0 described as 1.2 minus both closing change sections.
- **`ROADMAP.md`** (new): the pet-project roadmap.

## Close review R-2, R-4, R-5, R-7 — the review archived, its dispositions registered

From `patches/decisions-zoo-2026-10-12b.md`, Commit 3. Docs and one test
rename: no behaviour change, no capture touched.

- **`SPEC.md` §7.6, the audit's seams** (R-7): `serve_command`,
  `inspect_command`, `signature` and `installed` as `audit()`'s injectable
  parameters, replay's `send` seam, `--port 0`, and each bounded wait with its
  constant: `START_WAIT` 30 s, `SEND_TIMEOUT` 10 s, `FINISH_WAIT` 60 s. A
  bounded wait on a stdlib timeout is ruled not a clock read. The two places a
  bound passed is not caught (a second `serve` wait after a kill, and
  `inspect`'s `subprocess.run`) are stated as the code behaves.
- **`PROBES.md` L2** (R-2): cites spanweave-live `cddc694` §1.1/§1.5 beside
  §4.3/§5.4/§8.5 and names their tension; says its command runs without
  `--deltas`; notes that `serve --deltas` writes the record as a delta carrying
  `unclaimed_record` and `missing_trace_id`. The "Expected" line is unchanged.
- **`CONTRIBUTING.md`** (R-4): the reading order names `WORKPLAN.md` only while
  a series is open, and `TASKS.md` between series.
- **Three, not two** (R-5): `pyproject.toml`'s dependency comment,
  `spanweave_zoo/__init__.py`'s docstring, and the gate test, renamed
  `test_the_package_imports_none_of_the_three`. `pyproject.toml`'s agentgolden
  comment cites step 5 at §7.3 and its seam at §7.6.
- **`tests/collector_check.py`**: the failure hint names both causes of a skip,
  the binary absent or a module-level skip (f60f69c's was the second); 701fc80
  had not changed it.
- **Registry**: `reviews/REVIEW-2026-10-12.md`, byte for byte from `patches/`,
  its sha256 in `reviews/SHA256SUMS` (25 files, `sha256sum -c`); `TASKS.md`
  records R-1 to R-8's dispositions, R-8 as spanweave-ops'.

## Close review R-3 — the hop-by-hop list is the zoo's own

From `patches/decisions-zoo-2026-10-12b.md`, Commit 2. Changes what the
Collector receives; no capture touched, and the recorded head keeps every line.

- **`SPEC.md` §4.3, `spanweave_zoo/forward.py`**: the hop-by-hop list is
  stated as the zoo's own, one reason per name. RFC 9110 §7.6.1 is cited for
  `Connection`, its connection-options and the fields it names for removal;
  RFC 2616 §13.5.1 for `Trailer`, `Proxy-Authenticate` and
  `Proxy-Authorization`. §6.2 no longer attributes the list to RFC 9110.
- **`Proxy-Connection`** joins the list (nine names, was eight).
- **Fields named in `Connection`** are dropped from the forward, as RFC 9110
  §7.6.1 requires of an intermediary (`forward.connection_options`): every
  `Connection` line's value read as a comma list, items stripped of spaces
  and tabs, compared in any case.
- Tests (`tests/test_tee.py`):
  `test_proxy_connection_does_not_reach_the_collector`,
  `test_fields_named_in_connection_are_dropped_across_lines_in_any_case`
  (repeats, case, empty items, and a `Connection:` after a bare LF that names
  nothing), and `test_a_field_named_in_connection_does_not_reach_the_collector`
  (`Connection: X-Foo, keep-alive` plus `X-Foo` through a real tee into a
  downstream sink: recorded, not delivered). All three red on 1ddf386; the
  mutation "skip the `Connection` parse" fails the last two.

## Close review R-1, R-6 — a divergence reaches the report

From `patches/decisions-zoo-2026-10-12b.md`, Commit 1. Tests only: no code,
no `SPEC.md` change, no capture touched.

- **R-1**: new `test_a_live_batch_divergence_reaches_the_report_with_its_owner`
  (`tests/test_audit_real.py`). The audit runs Z4's `recorded` capture through
  the real `spanweave-live serve`, wrapped so that one byte is appended to each
  graph it writes: live ≠ batch while incremental = batch, and the test asserts
  the step-3 finding, its owner (spanweave-live, as `divergence_owner` assigns,
  `SPEC.md` §7.4) and its heading and step-3 row in the written report. The
  mutation `owner = None` in `partition_findings`, which the review saw survive
  the suite, now fails it.
- **R-6**: the shadow packages in
  `test_without_the_extra_the_collector_selection_reports_no_skip`
  (`tests/test_audit.py`) raise `ModuleNotFoundError`, not `ImportError`, so on
  f60f69c the test goes red by the module-level skip CI saw
  (`('::tests.test_audit_real', 'skipped')`), not by a collection error.

## A6 — the series closes

Series 1's A6 row (`TASKS.md`). Docs only: no code, no test, no capture
changes.

- **`TASKS.md`**: the registry between series — A0–A6, each with the
  commit(s) that closed it; the plan's decisions log (§3) and resume notes (§4)
  folded in verbatim; the threads the next series inherits (the macOS
  wall-clock cost test and the fix it names, A3g's four readings, A5's four
  review items, `OPEN_QUESTIONS.md` §3, and the three reviews' threads).
- **`reviews/`**: the series' three reviews and the 21 section files they were
  assembled from, copied byte for byte from the orchestrator's untracked
  `patches/`, with `reviews/SHA256SUMS` (24 entries, `sha256sum -c`) and a
  `-text` line in `.gitattributes` so a checkout cannot rewrite them.
- **`PROBES.md`**: `audit/`'s findings and step-4 tables consolidated into the
  next series' probes — spanweave-live 2, spanweave 5, agentgolden 0 — each
  with its captures, its command and its owner, and no fix.
- **`WORKPLAN.md` deleted.** `CLAUDE.md` rules 6 and 8 now name the three
  libraries the 2026-10-12 decision gated and pinned (`agentgolden` beside
  `spanweave` and `spanweave_live`) and no longer cite the plan's §0.6 as
  their source; `SPEC.md` §2.3 and §4.2, `collector/config.yaml`'s comment,
  `CHANGELOG.md`'s header and `OPEN_QUESTIONS.md` repoint their `WORKPLAN.md`
  citations at `TASKS.md` (or `git show 22be077:WORKPLAN.md`);
  `OPEN_QUESTIONS.md` §5's status line reads resolved, as its body already
  did. `README.md` names `PROBES.md`, `TASKS.md` and `reviews/`.

## A5 — the audit: every capture through spanweave-live and spanweave

Series 1's A5 row (`TASKS.md`); the decisions of 2026-10-12 (`OPEN_QUESTIONS.md` §5).

- **`zoo audit <run> [--out audit]`** (`SPEC.md` §7): replays the capture's
  raw bytes, then the Collector's JSON, into a real `spanweave-live serve
  --requests N` (whose end of input runs `Run.finish()`, the `Cap(0)`-at-end);
  compares every graph `serve` wrote with `spanweave.build` and with a
  `spanweave.Builder` fed the same records, re-read in-process by the pinned
  `Endpoint` and partitioned by the pinned `trace_id_of`; runs `spanweave
  inspect` and tables diagnostics, unmapped keys and `unknown` nodes; computes
  `agentgolden.signature.signature(graph)` as a smoke. Writes
  `audit/<project>-<run-id>.md`, every finding a reproduction naming its owner
  by the rules of §7.4. Exit 0 written, 1 written but a step incomplete, 2
  refused (not a run, does not verify, extra missing, an installed sha that is
  not the pin).
- **`agentgolden` pinned** in the `audit` extra at
  `aa1847f2a2ad51a95b98ab3e180bc5d211e6b138`, beside the two existing pins;
  `uv.lock` relocked (it adds agentgolden alone: its `spanweave>=0.9.1,<1.0`
  is met by the pinned 0.9.1). The report header records all three shas,
  pinned and installed.
- **The import gate names three libraries**: `agentgolden` joins
  `ANALYSER_MODULES`, confined to `spanweave_zoo/audit.py` like the other two.
  `cli.py` imports the audit module only when `zoo audit` runs, so the bare
  wheel and every other subcommand work without the extra; without it `zoo
  audit` refuses, exit 2, naming `uv sync --extra dev --extra audit`.
- **A seventh CI leg, `audit`**, installs the extra and runs `make
  audit-check`: `mypy --strict` with the three libraries present, then the
  `needs_audit` tests, failing if any skipped (they skip on every `check`
  leg, by design).
- **The `collector` leg no longer sees the audit tests** (fixes f60f69c):
  `tests/test_audit_real.py` skips per item (`skipif` in `pytestmark`) rather
  than with a module-level `importorskip`, which skipped the module at
  collection and put that skip into `collector-check`'s `-m needs_collector`
  report. The guard is unchanged; a test runs that selection with the extra
  hidden and fails on any skip.
- **The Z4 captures audited**: `audit/z4-2026-10-12-real.md` and
  `audit/z4-2026-10-12-recorded.md`, three findings each (spanweave-live 2,
  spanweave 1, agentgolden 0). The live graph equals the batch graph byte for
  byte on every trace `serve` wrote.

## A3g — the run-2b review's `next batch` items, closed

Run-2b review (`patches/REVIEW-2026-10-11.md`) N-2 to N-12; the decisions of
2026-10-11 ("header rule", "the seal"). N-1 was the plan's own, made by the
orchestrator before this batch.

- **`headers.json` records the request line whole** (`SPEC.md` §2.3, §3.2):
  `request_line`, verbatim, beside `method` and `path`, so the HTTP version
  and anything after it are no longer dropped (N-8). A head with **no CRLF at
  all** is one `unparsed` entry, verbatim, with no `request_line`, `method`
  or `path`; it used to read as an empty, fully parsed head.
- **The tee forwards the recorded head, not the stdlib's parse** (`SPEC.md`
  §4.3, §4.8; N-7). The `forward` seam is now `(head octets, body)`; the
  Collector is sent `NNNN.headers.raw` with the `Host` line substituted and
  the hop-by-hop lines dropped, by the replay's own line rule
  (`forward.rewrite_head`). A CR-injected `Content-Encoding: gzip` no longer
  reaches the Collector as a header. `Recorder.record` takes the head, the
  body and whether the path was accepted, and nothing of the stdlib's parse.
- **`SIGHUP` ends a capture as Ctrl-C does** (`SPEC.md` §4.6; N-2): closing
  the terminal or dropping ssh completes the manifest and stops the Collector,
  which used to be left running. A write to a hung-up terminal (`EIO`) is
  handled as a closed pipe.
- **`SPEC.md` §4.2 lists every line `zoo capture` prints** (N-3), and a test
  holds the list both ways, the summary included. README step 5 names
  `zoo capture: stopping`.
- **README**: a test holds the log-to-file variant's redirect, its `grep`, its
  run id and its `timeout` together (N-4); the `timeout` is now 60 s, not
  less than the zoo's own readiness wait (52.5 s). Step 4 says `make
  run-real` needs `OPENAI_API_KEY` in that terminal (N-5).
- **The seal's claim narrowed** (`SPEC.md` §5; N-6): it catches accidental
  and incidental edits and is not authentication; a test shows a manifest
  resealed by hand verifies.
- **`zoo replay`'s summary counts only what was sent** (`SPEC.md` §6.4;
  N-10): `<n> sent, <n> that did not answer 2xx, <n> not sent`, where sent
  means a receiver answered.
- `SPEC.md` §6.2's chunked replay no longer says it "will time out": that is
  a framing-aware receiver's answer, and a `zoo sink` answers `200` (N-11).
- Test gaps on the CRLF split closed (N-9): a CR or LF at a value's edge
  stays, a non-token name is no header, and a seal present but not a string
  fails verify.
- **The committed fixture capture was regenerated** as a new run through the
  real tee, because its `headers.json` files lacked `request_line` under the
  ratified rule; both bodies are byte-identical to the last two fixtures'.
  Z4's captures of 2026-10-12 are untouched and keep the json they were
  taken with.
- The run-2b patch set was written under `patches/` (N-12; untracked).

## A0c — the README survives its own rehearsal

Run-2 review §1.5; `OPEN_QUESTIONS.md` §4 (option 2). Docs only, except the
`zoo verify` closing-line wording (review N-1).

- **The operator flow says what a run does.** Ctrl-C to the terminal's group
  exits 0 and leaves no Collector running; `make verify` and `make check` are
  green with the new capture present; the terminal shows the readiness line,
  the two lines naming the ports and directories, one line per body per side
  and the summary (`1 body/bodies in raw/, 1 in json/`), and none of the
  Collector's lines, which are in `collector.log`; step 2 checks against
  `collector/SHA256SUMS`, uses the cache on a second run, and is once per
  checkout; the pet project's `make run` rewrites its own `MANIFEST.json`,
  which the operator does not commit from the pet's checkout.
- **The log-to-file variant** writes to
  `"${TMPDIR:-/tmp}"/zoo-capture-<run-id>.log`, outside the checkout and the
  run directory; the operator log is not part of the record, because
  `collector.log` is.
- README Layout and the `SPEC.md` §2 tree list `collector.log` and
  `json/NNNN.headers.*`, which every capture already holds. The Makefile's
  `collector` comment names `collector/SHA256SUMS` as the pin.
- **`zoo verify`'s closing line** is `N problem(s), each named above -- not
  verified.`; it no longer says "these bytes are not the bytes that were
  recorded" for a recorded problem, a bad `kind`, a missing `ended_at` or a
  seal mismatch. Test: four non-byte failures, red on the parent.

## A4a — replay sends the captured head

Run-2 review, A4 (N-6); the decision of 2026-10-11 ("replay").

- **`zoo replay` writes `NNNN.headers.raw` onto the socket itself** (`SPEC.md`
  §6, §6.2), with only the `Host` line substituted, then the body; it no
  longer goes through `http.client`. The replayed head is byte-identical to
  the captured one except `Host`. Gone: `Host` moved to the front, value
  whitespace normalised (`x:v` sent as `x: v`), `HTTP/1.0` sent as
  `HTTP/1.1`, bare-LF line endings sent as CRLF — and the hop-by-hop
  headers, which the replay used to drop on §4.3's rule and now sends as
  captured (§6.5). The tee's forward to the Collector is unchanged.
- **The `Host` line** is a line of §2.3's CRLF split whose field name is
  `Host`: every such line names the destination, a head with none gets none,
  and a `Host:` inside another line (after a bare LF; an all-LF head) is not
  touched.
- **`--json`** replays `json/NNNN.headers.raw` — the head the Collector sent,
  as the json sink recorded it — by the same rule.
- **A bare CR in a header value now goes out** as it arrived, where the
  replay used to refuse it because `http.client` would not send it. A head
  that is empty or unterminated is refused per body, named, exit 1.
- A new seam, `send` (§6.2), whose real implementation is
  `forward.send_head`; with §4.8's `forward` it is the package's only
  outbound socket. `sink.field_name` is the one token rule the split and the
  substitution share.
- Tests: the head-identity test over five head shapes, red on the parent and
  on a replay through `http.client`; `retarget` (six); empty and unterminated
  heads (three); no `http.client` connection opened; the bare-CR test now
  asserts the head goes out identical.

## A3f — the manifest is sealed, and the parse cannot invent

Run-2 review, A3b-1 and A3c; the decisions of 2026-10-11 ("the seal", "the
parse").

- **`MANIFEST.json` carries `seal`** (`SPEC.md` §5, §5.5): the sha256 of the
  manifest's canonical JSON with `seal` absent — `json.dumps(document,
  sort_keys=True, separators=(",", ":"), ensure_ascii=True)` encoded as ASCII
  — written in the same atomic write as `ended_at`, by `zoo capture` and
  `zoo sink` alike. **`zoo verify` recomputes it** (§5.6) and fails on a seal
  that is absent, not a string, or different: `kind` flipped from `recorded`
  to `real`, a `problems` entry removed, or a `files` entry rewritten together
  with its file all used to pass, because every file still hashed as recorded.
  Re-indenting the file changes no seal; the document is sealed, not its
  whitespace.
- **`NNNN.headers.json` is derived from `NNNN.headers.raw`** (`SPEC.md` §2.3,
  §3.2) by a split on CRLF and nothing else, never from the stdlib's parse. A
  bare CR or LF stays inside the value it arrived in: `User-Agent:
  otel\rX-Injected: yes` is one `User-Agent` header, where the stdlib's parse
  reported an `X-Injected` header no client sent. A line that is not a header
  (a continuation line, no colon) is listed under `unparsed` rather than
  folded into one. The stdlib's parse is still what the sink handles the
  request with (framing, the echoed content type, the forward).
- **The committed fixture capture was regenerated** through the real tee with
  the stock Collector 0.162.0, so that it carries a seal — a seal cannot be
  added to a capture after it is taken. Its two bodies are byte-identical to
  A3d's; it now also holds `collector.log` (A3e), and its headers files are
  the new split.
- Tests: seven on the seal in `tests/test_manifest.py`, five on the split in
  `tests/test_sink.py`, two on the fixture. The A4 replay test whose premise
  was the stdlib's truncated `User-Agent` now reads the whole value.

## A3e — Ctrl-C stops the capture and nothing else

A review blocker (run-2 review, Z-1). A terminal sends Ctrl-C to its whole
foreground process group, and the Collector child was in `zoo capture`'s: it
heard the keystroke itself, exited 0, and was recorded as `problems:
["collector exited: 0"]` — exit 1, `verify` and `make check` red, on a capture
that was fine and is immutable. Reproduced on the parent by the new test, with
the stand-in and with the stock binary alike.

- **The Collector child runs in its own session** (`SPEC.md` §4.6). Only
  `zoo capture` hears Ctrl-C, and it stops the Collector itself.
- **The shutdown order is stated and kept** (`SPEC.md` §4.6): the raw sink
  stops accepting; every POST it is handling — every forward the Collector has
  not answered — finishes, for at most 10 s; one last look at the Collector,
  then `SIGTERM` (its own shutdown flushes into the json sink), `SIGKILL` after
  a bounded wait, said aloud; the json sink stops; the manifest is assembled.
  An exit before `SIGTERM` is a problem; an exit after it is not.
- **`collector.log` in the run directory** (`SPEC.md` §4.2, §5.5): the
  Collector's stdout and stderr, verbatim, from its first line, listed in
  `files` and re-hashed by `verify`. None of it is echoed to the terminal any
  more.
- **The body count counts bodies** by where they are: `1 body/bodies in raw/,
  1 in json/` in `zoo capture`'s summary and `zoo verify`'s line, rather than
  "2 body/bodies" for one export.
- A Ctrl-C during the readiness wait stops the child the launcher started,
  which its own session no longer does for it.
- Tests: `tests/test_shutdown.py` sends `SIGINT` to the process group of a real
  `zoo capture` process; the stock-binary variant is a `needs_collector` test
  in `tests/test_collector_real.py`.
- **A sink binds and resolves no name** (`SPEC.md` §3.7; fixes 89b8dbf's
  `check (macos-latest, 3.12)` leg). `http.server`'s bind follows with
  `socket.getfqdn(host)`, a reverse lookup; on the macOS runner the first one
  in a process took tens of seconds, during which the process's own signal
  handlers could not run. A `zoo capture` run as its own process paid it on its first sink bind and the
  stand-in Collector on its receiver bind, which overran the readiness wait.
  The sink now binds without the lookup; so does the stand-in.
  `tests/test_sink.py` fails if binding a sink resolves a name.

## A4 — `zoo replay`: the capture's bytes, and its head, sent again

`SPEC.md` §6, which was a heading. A capture is only worth recording if a
receiver that was not there can be handed it, and the audit (§7) is the first
caller: it sends the same capture to `spanweave-live serve` twice, once as the
exporter's own bytes and once as the Collector's JSON.

- **`zoo replay <run> --to http://host[:port] [--raw|--json] [--timing]`**
  (`SPEC.md` §6): every body of the chosen side, in the order the manifest
  recorded it — which is the journal's order, which is receipt order, read out
  of the record rather than re-derived by sorting a directory.
- **The head comes from `NNNN.headers.raw`, never from `NNNN.headers.json`**
  (`SPEC.md` §6.2). That is what A3c kept the octets *for*: a bare CR in a
  header value reaches the parse truncated, so a replayer built on the parse
  sends a tidied request no exporter made — with the capture that says
  otherwise sitting on disk beside it. A head the wire refuses is **not**
  tidied into one it accepts: it is one line, a non-zero exit, and the rest of
  the capture still sent.
- **The send is the tee's own forward** (`forward.HttpForward`, `SPEC.md`
  §4.3), pointed somewhere else. Re-sending captured bytes is one act, and a
  second implementation of it would be a second chance to improve them. So the
  two differences between the exporter's request and the replayer's are the two
  §4.3 already names: `Host`, and the headers that described a connection that
  no longer exists.
- **A send that does not succeed never stops the rest** (`SPEC.md` §6.4). A
  `415` on a protobuf body is an answer and a finding, not an error; a replay
  that stopped at it would hide what the next body would have done. Exit **1**
  if any answer was not a 2xx or any body could not be sent; **2** when nothing
  was sent at all — not a capture, an unreadable manifest, no body on the
  chosen side (`--json` on a capture whose Collector never ran), a `--to` that
  is not an `http://host[:port]`.
- **`--timing` sleeps the recorded gaps through the injected `sleep`**
  (`SPEC.md` §6.3), from the `received_at` the sink wrote down — the one thing
  in a headers file the request did not say. A gap it cannot compute is not
  slept and not guessed: a missing or unparseable receipt time, or one that
  went backwards, is a printed line and the send still happens. Nothing under
  `spanweave_zoo/` sleeps outside the seam, so the suite waits for none of it.
- **The replayer verifies nothing and records nothing** (`SPEC.md` §6.5):
  `zoo verify` re-hashes bytes and `make verify` runs it on every gate.
- `tests/test_replay.py` replays the **committed capture** under
  `tests/fixtures/capture/` wherever it fits — the byte-identity claim is made
  against bytes a real exporter sent — and crafts the rest by putting head
  octets on a socket, which is the only way to get a head into a capture that
  the stdlib cannot represent. A test may do that; `spanweave_zoo/` may not.
- `manifest.received_at`, `manifest.recorded_bodies` and
  `manifest.HEADERS_RAW_SUFFIX` are public now, because the octets have a
  reader as well as a writer; `manifest.moment_of` is public for the same
  reason — what is and is not a comparable moment has one home (§5.3, §6.3).

## A0b — CI proves the Collector claim

The claim is A2's: a real protobuf export through the tee comes back from the
stock Collector as OTLP JSON carrying the same trace and span ids. Three tests
check it, they need a gitignored ~100 MB binary, and they skip when it is
absent — so for five CI legs the claim was green everywhere and *checked*
nowhere but on the maintainer's machine (review thread T25).

- **A sixth CI job, `collector (ubuntu-latest)`** (`SPEC.md` §4.9): one
  interpreter, `make collector`, then `make collector-check`. It is the only
  job that downloads the binary and the only one that can say the stock
  Collector re-encoded anything. **Wall clock: 15 s** on a cold cache — 4 s of
  it the 112 MB fetch, 1.6 s the three tests — measured on this tree
  (run 38013503089); the five `check` legs it joins take 17 s and 58 s.
- **`make collector-check` fails when a Collector test skips.** It runs exactly
  `-m needs_collector`, reads pytest's own junit-xml report, and exits non-zero
  on any skip, failure or error — *and* when the marker selects **no test at
  all**, which is how a renamed marker or a dropped decorator would otherwise
  turn the job into a no-op that passes. What it cannot use is the exit code:
  **pytest exits `0` when every selected test skips**, which is the whole
  reason a green tick said nothing. It is deliberately not a prerequisite of
  `check`, which stays green on a machine with no binary.
- **The tests carry a named `needs_collector` marker**, registered in
  `pyproject.toml`, as well as the skip. A bare `skipif` has no name to select
  by. `tests/test_collector_ci.py` asserts every test in
  `tests/test_collector_real.py` carries the decorator *and* that `-m` selects
  exactly those tests, because the marker is now part of a gate.
- **The guard's verdict is a pure function of the report text**, run against
  planted reports — a skip, all skipped, an empty run, a failure, an error — the
  way the import gate is run against planted violations. A guard nobody has
  watched fail is a guard nobody knows works.
- **The downloaded archive is cached at `collector/.cache/<asset>`**
  (`SPEC.md` §4.1), so a second `make collector` does not fetch 100 MB again
  and CI restores it between runs, keyed on the **sha256 that pins it** —
  printed by `collector/fetch.py --print-pin`, read from `collector/SHA256SUMS`
  itself, so a `VERSION` or digest change is a miss and a fresh download rather
  than a stale hit. The cache changes nothing about the check: the archive is
  re-hashed every run, and **a cached archive whose digest is not the pin is
  refused exactly as a bad download is**, naming the file to delete. The
  download writes `<asset>.part` and renames it only once the digest matches,
  so an interrupted fetch never becomes the cache.

## A0a — the README is true, the licence exists, and the open question has a home

Documentation only: no module under `spanweave_zoo/` changed, and `SPEC.md` is
unchanged. What changed is what a stranger reads, plus the tests that hold it.

- **Every command the README prints is complete and runnable as printed**, and
  `tests/test_readme.py` parses each one with the CLI's own parser on every
  `make check`. The first `zoo capture` an operator met did not run -- exit 2,
  "the following arguments are required: --kind, --project-manifest", because
  both flags were introduced sixty lines further down the page (review finding
  F3). Every `zoo` command now carries the `uv run` prefix that makes it
  typeable in a bare checkout, every `make` target is checked against the
  `Makefile`, and every `uv sync --extra` against `pyproject.toml`. The pet
  project's own `make run-real` / `make run-recorded` are exempt from the
  target lookup and `EXPORT-CONTRACT.md` is asserted to be where they come
  from.
- **The operator flow is a numbered list of the commands themselves, starting
  with `uv sync --extra dev`, and nothing counts them.** Three counts
  disagreed: the plan's row said four commands and a `Ctrl-C`, the README said
  five, and an operator had to type six because the `uv sync` was prose beside
  the list rather than a step in it (review finding F15). The numbers are now
  the count, a test fails on any "N commands" phrasing, and the explanation of
  each step sits with the step rather than in a second list that could drift
  from the first. The verified way for a supervisor to wait on the readiness
  line is printed with it.
- **`LICENSE` (MIT) and `license` / `license-files` in `pyproject.toml`**
  (review thread T5). There was neither, so the built wheel carried no licence
  at all. Declared exactly as `spanweave` and `spanweave-live` declare it, with
  a `LICENSE` byte-identical to theirs; `make install-check` now asserts the
  wheel ships it, and `tests/test_packaging.py` that the file, the metadata and
  the README agree.
- **`OPEN_QUESTIONS.md` exists** (review finding F14). `CLAUDE.md` says a batch
  that would have to invent a rule stops and writes the options there, and
  there was no such file -- A3 met that trigger and recorded the question in a
  commit message instead. §1 is the manifest-timing question with the decision
  that settled it (copied at the end, A3b), §2 the licence, §3 the one edge
  that is still open as a preference. An answered question is kept with its
  answer.

## A3d — `verify` refuses what it did not check, and CI checks something

- **`zoo verify <path>` on a path that is not a capture exits 2, naming the
  path** (`SPEC.md` §5.6). An absent directory, a file, or a directory with no
  `MANIFEST.json`, no `raw/` and no `<project>/<run-id>` under it used to print
  "nothing to re-hash" and exit **0** — a typed path is a claim that a capture
  is there, so that was the reassuring pass this command exists to refuse. Two
  rather than one because nothing was checked, which is the distinction `zoo
  capture` and `zoo sink` already draw between refusing to start and going
  wrong. The **default** root keeps exiting 0 when it is empty: a repository
  that has recorded no captures yet is nothing to re-hash. `cli.py`'s docstring
  now lists the three exit statuses it actually produces.
- **One real capture is committed, and `make verify` reads it**
  (`SPEC.md` §5.6). `tests/fixtures/capture/` holds a single OTLP protobuf body
  through the real tee — `tests/otlp.py`'s hand-built export into the raw sink,
  the stock Collector behind it, its JSON re-encoding into the json sink — with
  `NNNN.headers.raw` and `NNNN.headers.json` on both sides, both journals and
  the manifest the run assembled, on a clock the run chose. `make verify` now
  runs `zoo verify` over `captures/` *and* over that fixture, so every
  `make check` and every CI leg re-hashes real bytes instead of reporting an
  empty tree. The capture is never edited and never regenerated, and it is not
  under `captures/`, which is for the zoo's own runs. A `.gitattributes` marks
  it `-text`, because `NNNN.headers.raw` is CRLF on purpose and a clone that
  converted line endings would fail verify for a reason that has nothing to do
  with the capture.
- **The README's two contract digests are recomputed on every `make check`**
  (`tests/test_readme.py`). The Provenance section says the sha256s of
  `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` are how "byte-identical to the ones
  handed to the project" is checked; nothing checked them. Now one appended
  byte to either document fails the suite and names which file.
- **The import gate's one exemption is a path, not a file name**
  (`tests/gates.py`, `SPEC.md` §7). It was matched on the basename, so any
  `audit.py` anywhere — `spanweave_zoo/replay/audit.py`, say — would have
  inherited the exemption and the rule could have been switched off by a
  `mkdir`. It is now `spanweave_zoo/audit.py` and nothing else.

## A3c — the header octets are the record

- **Every request leaves `NNNN.headers.raw`** beside its body and its
  `NNNN.headers.json` (`SPEC.md` §2.3, §3.2, §3.4): the request line and the
  header block as the octets arrived, CRLFs intact, up to and including the
  blank line that ends them. The octets are kept as they are read off the
  socket, before anything parses them; the body is not in the file. `SPEC.md`
  §2.3 now says which of the two files is the unmodified record (`.raw`) and
  which is the parse beside it (`.json`), on the same rule as the Collector's
  `json/`: if they disagree, the octets are what arrived.
- **A head the stdlib cannot represent is now in the capture.** `email`'s
  header parser splits a header line on a **bare CR** — HTTP forbids one and
  real clients emit one — so the value arrives truncated and every header
  after the split is absent from the parse altogether. That head is now
  recorded in full in `.raw`, while `.json` stays exactly what Python got: a
  recorder whose record was the parse would hold what Python can represent
  rather than what the exporter sent.
- **Nothing was added to `zoo verify`**, which is the point of A3b's walk: the
  manifest's `files` list is built by walking the run directory, so each
  `NNNN.headers.raw` gets a digest of its own without a recorder announcing it,
  and a bare CR tidied out of one fails verify (`SPEC.md` §5.6). The sink's
  startup refusal counts headers files of either kind, so a run directory
  holding only heads from an earlier capture is still refused (`SPEC.md` §3.1).

## A3b — the manifest is written once, at the end, and covers every file

- **Bodies are journalled, and the manifest is assembled when the run ends**
  (`SPEC.md` §3.5, §5.5, §2). Each recorded body is written to `bodies.jsonl`
  as one flushed line and each attempted forward to `forwards.jsonl`;
  `MANIFEST.json` is labelled at the start (`kind`, the two versions,
  `started_at`) and assembled once at the end from those journals plus a walk
  of the run directory. Recording a body no longer costs more the longer the
  run gets: rewriting a document that grows by an entry per POST is work that
  climbs with the number of bodies, and appending a line is not. Measured over
  1,600 bodies in one run: **301 us/body over the first 800, 307 us/body over
  the last 800, ratio 1.02**.
- **Every file in a run directory has a sha256 of its own** (`SPEC.md` §5.6).
  Bodies are in `bodies`; the headers files, the journals and anything else the
  capture holds are in the new `files` list, each file once, `MANIFEST.json`
  excepted. `zoo verify` re-hashes both lists and accounts for every file by an
  entry rather than by sitting beside one — so a rewritten `Content-Type` in a
  `NNNN.headers.json` now fails verify, where before every body still hashed
  correctly and the capture passed.
- **`zoo verify` refuses three more things** (`SPEC.md` §5.6): a capture with
  no `ended_at` (never completed — the line names the directory and the
  command that removes it), a `kind` that is neither `recorded` nor `real`, and
  any capture whose manifest records a `problem`. A3a wrote `problems` and
  nothing read it; `verify` reads it now.
- **The project's own `MANIFEST.json` is copied when the run ends**
  (`SPEC.md` §5.3), per the manifest-timing decision. The contract has the
  project write that file *while it runs*, so the copy a capture carries is now
  the recorded run's and not its predecessor's. The path is still checked at
  the start, so a typo is refused while nothing is on disk. The capture dates
  the document against its own `started_at` — the one field of it the zoo
  reads, for that and nothing else: a document written before the capture
  started is an earlier run's, so the capture carries **none**, records a
  `problem` naming both times, exits non-zero and does not verify. A document
  that is gone by the end is the same. A document the zoo cannot date is kept
  — it does not drop a record it was handed — with a problem recorded all the
  same.
- **Progress lines are flushed as they are written, and a closed stdout ends
  the run rather than killing it** (`SPEC.md` §4.6). `zoo capture | head` used
  to raise `BrokenPipeError` out of a recording thread and leave a capture
  whose manifest was never assembled; the first broken pipe now asks the run to
  stop the way Ctrl-C does, later lines go nowhere, and the exit status is what
  the capture was.
- **Degenerate cases covered**: a half-written line in `bodies.jsonl` (the body
  it recorded is still hashed as a file and the capture records a problem —
  nothing is dropped and nothing is claimed), a project manifest with no
  `started_at`, a project manifest that vanished mid-run.

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
