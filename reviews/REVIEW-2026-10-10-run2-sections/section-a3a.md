# Section a3a -- cold review of 2b3c499 (A3a)

"capture: a capture exists only once it is ready, and a refusal writes nothing"

- Derived parent: `git rev-parse 2b3c499^` = `34c43690e8bbf3af6487ea6ff2e76e0e843a93da`
  ("plan: run-1 review decided, run 2 ordered") -- a `plan:` commit, as expected.
- Worktrees (all under the scratchpad, absolute): `wt-a3a-commit` (2b3c499),
  `wt-a3a-parent` (34c4369), `wt-a3a-head` (040b194, for claim (d) comparison).
  The real Collector `collector/otelcol-contrib` (0.162.0) was copied into each.
  Every live run passed `--captures <scratchpad>/a3a-live/caps-*`.
- Ports: default 4317-4320 (allowed for this section only), plus 4471 for `zoo sink`.
  Nothing else of mine was listening on them before or after (`ss -ltn` empty).

## 1. Spec / changelog in the same commit

`git show --stat 2b3c499`: SPEC.md +140/-?, CHANGELOG.md +48, README.md +7,
collector/config.yaml, capture.py, cli.py, collector.py, manifest.py, sink.py,
tests/test_capture.py. SPEC §4.6 (readiness order, steps 1-6, the one readiness
line, refusal = exit 2 and no directory, a Collector exiting mid-run -> `problems`),
§4.5 (`problems` key, absent when none), §4.2 (log level `info`), §3.1
(`create_directory`). SPEC §4.6 says explicitly "`zoo verify` reads `problems` in
A3b; until then the non-zero exit and the manifest entry are what report it."
OK.

## 2. Parent run (commit's tests/test_capture.py copied into wt-a3a-parent)

`uv run pytest tests/test_capture.py` on 34c4369 -> **8 failed, 28 passed**.

| test | failure on parent | kind |
|---|---|---|
| test_the_pinned_config_is_stock_and_re_encodes_to_json | `assert 'level: info' in ...` | assertion (real) |
| test_a_foreign_listener_on_the_collector_port_is_refused_and_writes_nothing | `Failed: DID NOT RAISE CollectorRefused` | assertion (real) |
| test_a_collector_that_holds_the_port_without_reporting_ready_is_refused | `Failed: DID NOT RAISE CollectorRefused` | assertion (real) |
| test_a_collector_that_cannot_start_at_all_is_refused_naming_the_cause | `assert 'cannot start pipelines' in 'the Collector exited with 1 before it listened on ... Its own log is above'` | assertion (real) |
| test_a_ready_collector_makes_the_directory_and_prints_one_readiness_line | `assert 'zoo capture:...json/' == 'zoo capture:...rl-C to stop.'` | assertion (real) |
| test_the_collector_exiting_mid_capture_is_recorded_and_reported | `AttributeError: 'Capture' object has no attribute 'check_collector'` | missing API (runtime, not collection) |
| test_a_capture_with_no_problems_exits_zero | `AttributeError: ... no attribute 'problems'` | missing API |
| test_the_sink_banner_is_distinct_from_the_captures_readiness_line | `AttributeError: module ... has no attribute 'READY_LINE'` | missing API |

Not vacuous: five are behavioural assertion failures; three fail on absent API
(the mutations below cover their behaviour). Parent file restored with
`git checkout tests/test_capture.py`.

Live parent check (same port-4320 scenario as claim (a), foreign listener with
SO_REUSEADDR held via `hold.py 4320`): the parent **created**
`capsP/z4/r1/{raw,json,MANIFEST.json}`, printed `zoo capture: collector 0.162.0 up`
and the readiness line, while the Collector's own output said
`Error: cannot start pipelines: ... listen tcp 127.0.0.1:4320: bind: address already in use`.
So the F2 race is real on the parent and is what A3a closes.

## 3. Mutations (wt-a3a-commit, each reverted with `git checkout spanweave_zoo`)

M1 -- the row's/commit's named mutation (connect-only probe):
```
-            if running.log.says(READY_MARKER) and self._accepts():
+            if self._accepts():
```
-> 2 failed: `test_a_foreign_listener_on_the_collector_port_is_refused_and_writes_nothing`,
`test_a_collector_that_holds_the_port_without_reporting_ready_is_refused`, both
`Failed: DID NOT RAISE CollectorRefused`. The commit body's claim is accurate.

M2 -- problem not written to the manifest:
```
-            manifest.append_problem(self.run, problem)
+            pass
```
-> `test_the_collector_exiting_mid_capture_is_recorded_and_reported` fails.

M3 -- run directory made before readiness (capture.py `start()`, right after
`check_version`): `+        self.run.mkdir(parents=True, exist_ok=True)`
-> 3 failed (`assert not True` on `run.exists()`): foreign-listener, holds-port,
cannot-start-at-all.

M4 -- exit status ignores problems (cli.py `_exit_status`):
```
-    return 1 if running.failed_forwards or running.problems else 0
+    return 1 if running.failed_forwards else 0
```
-> `test_the_collector_exiting_mid_capture_is_recorded_and_reported` fails, `assert 0 == 1`.

M5 -- SURVIVES: readiness reduced to the marker alone (drop the connect half of
the AND that SPEC §4.6 insists on, "Both, because neither implies the other"):
```
-            if running.log.says(READY_MARKER) and self._accepts():
+            if running.log.says(READY_MARKER):
```
-> full suite **128 passed**. No test covers "a ready line without a connection"
(the stub only logs ready after it has bound). See A3a-4.

## 4. Clock / randomness / network in the diff

`collector.py`: `subprocess.Popen`, `socket.create_connection`, `threading` --
all inside `Binary`, which is the `launch` seam SPEC §4.8 names; the wait uses
the injected `sleep`. `capture.py`: no clock, no sleep, no socket (uses `now`,
`make_server`, the launcher). `cli.py`: `_system_clock`/`_system_sleep` are the
production seams. No `random`, no `urllib`/`http.client` added. OK.

## 5. One concern / message form

`capture: <one line>`, body names A3a and the SPEC sections. Readiness + refusal
+ mid-run exit is what the row defines as one batch. The config log-level change
is the precondition for reading the ready line. OK.

## 6. make check (wt-a3a-commit, with the real Collector present)

`make check` -> exit 0: ruff "All checks passed!", mypy "Success: no issues found
in 7 source files", pytest **128 passed in 3.90s** (0 skipped -- the real-Collector
test ran because the binary was copied in), gates 30 passed, `zoo verify`: no
captures, `zoo 0.0.1`.

Side observation: when an A3a stub test fails (parent run, M1 run), the stub
child (`time.sleep(600)`) is never stopped and survives the pytest process
holding its ephemeral port -- I found six such orphans from pytest-5124..5126
and killed them. Green runs leak nothing. (thread, A3a-6)

## 7. Specific claims

### (a) foreign listener on the default ports -> refusal, exit 2, nothing on disk

`zoo capture --project z4 --run-id r1 --kind recorded --project-manifest pm.json --captures <sp>/caps-<port>`
with `hold.py <port>` (bind+listen) running:

| held port | exit | captures dir | first line of stderr |
|---|---|---|---|
| 4320 | 2 | absent | `zoo capture: refusing to start: the Collector exited with 1 before it reported ready on 127.0.0.1:4320. ... Its own log says:` + tail incl. `Error: cannot start pipelines: failed to start "otlp" receiver: listen tcp 127.0.0.1:4320: bind: address already in use` |
| 4318 | 2 | absent | `zoo capture: refusing to start: [Errno 98] Address already in use` (whole message) |
| 4319 | 2 | absent | `zoo capture: refusing to start: [Errno 98] Address already in use` (whole message) |
| 4317 | 2 | absent | `... the Collector exited with 1 before it reported ready on 127.0.0.1:4320 ...` + tail `listen tcp 127.0.0.1:4317: bind: address already in use` |
| 4320, HTTP-200 responder (`hold200.py`, curl POST -> 200) | 2 | absent | same as 4320 row (the responder's only logged request was my own curl; zoo's probe is connect-and-close) |

Confirmed for the core claim (exit 2, no `caps-*` and no `captures/<project>/`).
But the "names the port" half holds only for 4320: the sink ports give a bare
`[Errno 98] Address already in use` with no port, and for 4317 zoo's own sentence
names 4320 while the cause (4317) is only in the quoted Collector log. See A3a-2.
The refusal also prints the Collector's log twice (echoed live on stdout, then
quoted in the stderr message).

Row mutation "a probe that only connects to the port" = M1 above, caught by
`test_a_foreign_listener_on_the_collector_port_is_refused_and_writes_nothing` and
`test_a_collector_that_holds_the_port_without_reporting_ready_is_refused`.
The HTTP-200 inverse is refused live at 2b3c499 (and would have passed on the
parent's connect-only probe, as the plain-listener parent run shows).

### (b) Collector killed mid-capture

`run.sh` (setsid, POST one body, sleep, signal the otelcol-contrib child only,
POST a second body, then `kill -INT <zoo python pid>`):

| signal to child | zoo exit | MANIFEST problems | bodies | raw / json | `zoo verify` at 2b3c499 |
|---|---|---|---|---|---|
| `kill -9` | **1** | `['collector exited: -9']` | 3 | raw 0001,0002; json 0001 only | **exit 0** ("0 problem(s)") |
| `kill -TERM` | **1** | `['collector exited: 0']` | 3 | raw 0001,0002; json 0001 only | **exit 0** |

Raw kept recording after the Collector died (second POST -> 200, raw/0002.body
written). Codes are Popen's: `-9` (negative signal number, not shell `137` as the
SPEC example shows) and `0` (the Collector exits 0 on SIGTERM). "zoo verify fails
on it" is **refuted at 2b3c499** -- by design: SPEC §4.6 at this commit defers
verify reading `problems` to A3b. At HEAD 040b194 verify does fail on a capture
with problems (see (d): `verify hpty1=1`).

### (c) readiness line once per capture, never by `zoo sink`

Count of `zoo capture: the raw bytes are the record. Ctrl-C to stop.` over whole
logs incl. stop: out-k9, out-tm, out-pgint, out-pidint, out-pidterm, and all 10
pty runs -> **1** each; `grep -c '^zoo capture: the raw bytes are the record'` -> 1.
`zoo sink --port 4471 --out <sp>/sinkout/raw`, one POST, SIGINT: output is
`zoo sink: recording ...`, `zoo sink: bodies to ...`, `zoo sink: it parses nothing. Ctrl-C to stop.`,
one body line, `zoo sink: stopped. 1 body/bodies.`, exit 0; readiness phrase count **0**.
Confirmed.

But at 2b3c499, with stdout redirected to a file, the readiness line is **not in
the file until the capture stops**: `print()` unflushed, block-buffered. Measured:
directory existed after 0.41 s; 3 s later `capture.log` had 0 lines; after SIGINT,
1 readiness line. At HEAD 040b194 the same measurement shows the line (10 lines)
within 3 s. So the README's supervisor grep (`until grep -q "^zoo capture: the raw
bytes are the record" capture.log`, README.md:225, added later) would have hung on
2b3c499 and works at HEAD. Fixed downstream; a result, not a finding.

### (d) terminal Ctrl-C -> SIGINT to the whole process group -> capture marked failed

Code:
- `spanweave_zoo/collector.py:273-281` -- `subprocess.Popen([...], env=..., stdin=DEVNULL, stdout=PIPE, stderr=STDOUT)`:
  **no `start_new_session`, no `process_group`, no `preexec_fn`**. Live: `zoo pgid=2910541`,
  `collector pgid=2910541` -- same group, so the tty's SIGINT reaches the child.
- `spanweave_zoo/capture.py:314-322` -- `stop()`: `raw.stop()` then
  `self.check_collector()` **before** `self.collector.stop()`; comment: "the one
  worth recording is the one it had before anybody asked it to go".
- `spanweave_zoo/capture.py:338-347` -- `check_collector()` records any non-None
  returncode as `collector exited: <code>`, including 0, with no regard for
  `self._stopping` being set.
- `spanweave_zoo/cli.py:286` -- any problem -> exit 1.

So it is a race between the Collector's own SIGINT shutdown (~1 ms: "Received
signal from OS ... Shutdown complete.") and zoo's path handler -> `raw.stop()`
(`server.shutdown()` waits up to the 0.05 s `poll_interval`) -> `check_collector()`.
Instrumented (monkeypatched timestamps, no tracked edit): losing run
`request_stop 69.6674 / stop() 69.6675 / check_collector during stop: returncode=0 at 69.7166`
(raw.stop took 49 ms); winning runs reach the check in ~1 ms with `returncode=None`.

Rates measured:

| how | commit 2b3c499 | HEAD 040b194 | parent 34c4369 |
|---|---|---|---|
| real tty Ctrl-C (`ptyrun.py`: pty.fork, write `\x03` to the master) | **5/10 failed** (`exit 1`, `['collector exited: 0']`) | **1/8 failed** (exit 1, `zoo verify` exit 1 on it) | 0/6 (no `problems` concept; exit 0) |
| `setsid` + `kill -INT -- -<pgid>` | 0/11 plain, 2/26 instrumented | 0/5 | -- |
| `kill -INT <zoo pid>` | 0/13 (Collector log: `"signal": "terminated"` -- zoo's own terminate) | 0/2 | -- |
| `kill -TERM <zoo pid>` | 0/1 | -- | -- |

Collector logs `"signal": "interrupt"` in every group/tty run, `"terminated"` in
every PID-only run -- direct proof the child got the tty's SIGINT. The signalled
pid was the python process (`ps -o comm=` = `zoo`, the venv entry-point script,
not a `uv` wrapper).

The lead's observation is **confirmed as a race, not deterministic**: the
README's own stop path (Ctrl-C) marks a clean capture failed at a high rate at
2b3c499 (5/10) and still at HEAD (1/8). The parent had the same signal delivery
but no `problems`, so nobody looked: **introduced by A3a** (and its exposure
carried into A3b's verify, which turns it into a verify failure).

Tests: A2's `test_a_signal_ends_the_run_rather_than_leaving_the_collector_behind`
(tests/test_capture.py:469) uses `signal.raise_signal(SIGINT)` in-process with
the `FakeLauncher` -- no child at all; `test_both_stop_signals_are_handled` only
checks handlers; A3a's `test_the_collector_exiting_mid_capture...` sets
`launcher.running.exited = 137` on a fake. No test signals a process group or
has a real child receive the signal.

Minimal fix the spec would need (not applied): SPEC §4.6 states the Collector
child runs in **its own process group** (`start_new_session=True` or
`process_group=0` on the Popen at collector.py:273), so the operator's Ctrl-C
reaches only zoo, which stops raw -> Collector -> json in order (this also keeps
the Collector up until raw has stopped, so no body in that window gets a failed
forward). Belt-and-braces, or alternatively: an exit observed after
`request_stop()` is not a `problem` (check `self._stopping` in `check_collector`,
or check returncode before setting the event). The first is the better fix; the
second alone would still let the group SIGINT shut the Collector down before
raw stops. A test: spawn a real child (the stub) and `os.killpg` the test's own
child group, or assert `start_new_session` on the Popen.

### (e) log level warn -> info: Collector logs on the operator's terminal

Confirmed. `out-pidint.log`: readiness line is **line 8**; lines 1-7 are the
Collector's `info` lines (`Internal metrics telemetry disabled`, `Starting
otelcol-contrib...`, `Starting extensions...`, `Starting GRPC server`, `Starting
HTTP server`, `Everything is ready. ...`), echoed verbatim by `ChildLog` via
`print` (collector.py:168, `Binary(log=print)`), followed after stop by four more
(`Received signal from OS`, `Starting shutdown...`, `Stopping extensions...`,
`Shutdown complete.`). Each line ~250-400 chars with a `resource` JSON blob.
README.md (A3a's added paragraph) says "`zoo capture` prints one line -- `the raw
bytes are the record. Ctrl-C to stop.`" and the commit body says the line is
"first": true only of zoo's own `Capture._log` lines (which is all
`test_a_ready_collector_..._prints_one_readiness_line` captures -- the stub's
echo goes to `Binary`'s separate `log`). On a real terminal it is the 8th line,
after 7 Collector lines. It is unique and the `^zoo capture:` anchored grep works,
so supervisors are fine; the README's "prints one line" overclaims. See A3a-3.

## Findings

**A3a-1 -- a terminal Ctrl-C marks a clean capture failed (race).** The Collector
child shares zoo's process group (collector.py:273-281, no `start_new_session`),
so the tty's SIGINT reaches it directly; it shuts down in ~1 ms and exits 0,
and `Capture.stop()` (capture.py:314-322) calls `check_collector()` after
`raw.stop()` (up to 50 ms) and records any exit -- including 0, after a stop was
requested -- as `collector exited: 0` (capture.py:338-347) -> exit 1, and at HEAD
`zoo verify` fails. Measured 5/10 tty Ctrl-Cs at 2b3c499 and 1/8 at HEAD; 0 when
only the zoo PID is signalled. Introduced by A3a (the parent had no `problems`).
No test exercises group delivery. Fix in spec + code: own process group for the
child (and/or: an exit after stop-requested is not a problem). **Bin: blocks Z4
capture** -- the README's documented stop marks a real capture failed at random,
and the operator cannot tell a real Collector death from this.

**A3a-2 -- a held sink port is refused without naming the port.** Holding 4318 or
4319: `zoo capture: refusing to start: [Errno 98] Address already in use` and
nothing else (cli.py:255-261 prints the bare OSError; the comment there says
"address already in use names the port it is about", which is false for the
stdlib's message). SPEC §4.6 says each refusal "names the port or the cause".
Holding 4317: zoo's sentence says "before it reported ready on 127.0.0.1:4320";
the right port is only in the quoted Collector tail. Exit 2 and no directory
hold in all cases, so nothing is quietly wrong. No test holds a sink port. **Bin:
next batch.**

**A3a-3 -- README "prints one line" / "first" overclaim after the info log level.**
With `level: info` the operator's terminal shows 7 Collector info lines before the
readiness line and 4 after stop (each with a resource JSON blob); the readiness
line is unique and the anchored grep works, so this is documentation, not
behaviour. **Bin: next batch** (doc wording; or filter/redirect the echo).

**A3a-4 -- the connect half of readiness is untested (M5 survives).** Dropping
`and self._accepts()` (collector.py:323) leaves 128/128 green, although SPEC §4.6
argues for both halves. **Bin: thread.**

**A3a-5 -- refusal prints the Collector's log twice** (echoed live to stdout by
`ChildLog`, then quoted as `tail()` in the stderr refusal). Cosmetic. **Bin: thread.**

**A3a-6 -- a failing A3a stub test leaks its child for 600 s** (`start()` never
returned, so nothing stops it); six orphans observed after the parent/M1 runs.
Green runs leak nothing. **Bin: thread.**

Result, not finding: at 2b3c499 the readiness line was block-buffered when stdout
is a file (would hang the README's supervisor grep); fixed by HEAD.

## Cleanup

Worktrees wt-a3a-commit, wt-a3a-parent, wt-a3a-head removed (`git worktree remove
--force`, then `prune`); orphan stub processes killed; main checkout `git status
--short` empty.
