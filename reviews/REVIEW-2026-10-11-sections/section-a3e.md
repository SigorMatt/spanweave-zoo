## A3e (`89b8dbf`, `9f23d12`) — aux, cold

Worktrees (absolute, under the scratchpad, removed at the end):
`.../scratchpad/a3e/{p0,c1,c2,head}` at `ea7fc51`, `89b8dbf`, `9f23d12`, `3f06815`;
the real `otelcol-contrib` 0.162.0 copied into each `collector/`. Driver:
`.../scratchpad/a3e/drive.py`. It starts `zoo capture` as its own session
(`start_new_session=True`, as `setsid` does) on free non-default ports
(`--port/--json-port/--collector-port/--collector-grpc-port`). It POSTs the
protobuf from `tests/otlp.export_trace_service_request()`, waits for
`json/0001.json`, signals the process group, then reads the exit status,
`MANIFEST.json`, `zoo verify <run>` and whether the Collector PID (the zoo's
`otelcol` child, taken from `ps --ppid`) is still alive.

### Parents, derived

`git rev-parse 89b8dbf^` = `ea7fc511…` (`plan: run-2 review decided`), and
`git rev-parse 9f23d12^` = `89b8dbf…`.

- **89b8dbf on `ea7fc51`**, with `tests/test_{shutdown,collector_real,capture,sink}.py`
  copied in: `9 failed, 68 passed`. The run is **real** for the three tests
  that carry the row:
  - `test_ctrl_c_to_the_process_group_stops_the_capture_and_nothing_else`
    fails at `tests/test_shutdown.py:271`, `assert 1 == 0` (exit status);
  - `test_ctrl_c_to_the_process_group_with_the_real_collector` fails at
    `tests/test_collector_real.py:304`, `assert 1 == 0`;
  - `test_a_forward_under_way_is_answered_before_the_collector_is_stopped`
    fails at `:461`, "the Collector was stopped with a forward still waiting on it".

  The other five failures are **API errors** and say nothing about behaviour:
  `collector.LOG_NAME`, `Binary(stop_wait=)`, `Capture(flush_wait=)` and
  `manifest.tally` are missing, and `test_sink.py:362` fails on the tally
  wording. One of them is the killed-by-hand test (`AttributeError LOG_NAME`
  at `:307`). The behaviour it holds already existed since A3a, so that test
  could not have been red by assertion.
- **9f23d12 on `89b8dbf`**, with `tests/test_sink.py` and `tests/test_shutdown.py`
  copied in: `1 failed, 32 passed`. This is **real** and fails by assertion:
  `test_binding_a_sink_resolves_no_name`, at `tests/test_sink.py:572`,
  `AssertionError: the sink resolved a name: ('127.0.0.1',)`.

### Mutations (in `c2` = 9f23d12, each reverted)

| # | mutation | caught by |
|---|---|---|
| M1 (row's) | `collector.py:343` `start_new_session=True` → `False` (child left in the parent's group) | `test_ctrl_c_to_the_process_group_stops_the_capture_and_nothing_else` (`test_shutdown.py:281`, `assert 1 == 0`, output shows `! collector exited: 0`) **and** `test_ctrl_c_to_the_process_group_with_the_real_collector` (`test_collector_real.py:304`). `2 failed, 9 passed` |
| M2 | `Capture.stop`: the last look moved *after* `running.stop()` | `test_shutdown.py:281` (group SIGINT) and `:375` (`test_a_collector_that_ignores_sigterm_is_killed_and_that_is_not_a_problem`). `2 failed, 5 passed` |
| M3 (9f23d12) | `sink._Server.server_bind`: `self.server_name = socket.getfqdn(str(host))` | `test_binding_a_sink_resolves_no_name`, `test_sink.py:572`. `1 failed, 25 passed` |

**(d) confirmed.** The row's corrected mutation (child left in the parent's
group) fails the group-SIGINT test, with the stand-in and with the real binary.

### `make check`

- `c1` (89b8dbf): exit 0, `305 passed in 10.42s` + gates `31 passed`, verify green.
- `c2` (9f23d12): exit 0, `306 passed in 11.10s` + `31 passed`.

Both runs had the real binary present, so the `needs_collector` tests ran.

### No clock, randomness or network outside a seam

`grep -nE "import (time|random|socket|datetime…)|time\.|datetime\.now|timeout=|\.wait\(|getfqdn"`
over `spanweave_zoo/` at 9f23d12 finds:

- the real `now` and `sleep` in `cli.py:103,115`;
- `socket` only in `collector.py:43`, which is the readiness probe that
  existed before this batch, and in the sink's listener seam.

Both commits add **timed waits** that use the monotonic clock inside the
stdlib and do not go through the `sleep` seam: `sink.py:206`
`Condition.wait_for(timeout=flush_wait)` and `collector.py:252,255`
`process.wait(timeout=stop_wait/kill_wait)`. The last two were already there
as `wait(timeout=10)`. SPEC §4.6 names them as "bounded waits", and every
one of them can be injected (`flush_wait=`, `stop_wait=`), so the tests use
0.2 s and 0.5 s. They read no timestamp into the record. This is not a
violation, but SPEC §4.8 says "no module … sleeps on its own" and these are
sleeps in all but name. **thread.**

### (a) SIGINT to the process group, real Collector, 10 runs

The driver signals with `os.killpg(pid, SIGINT)`, which is the same as
`kill -INT -<pgid>` on a zoo started under its own session.

| tree | exit 0 | `problems` absent | `verify` 0 | Collector left | `collector.log` listed |
|---|---|---|---|---|---|
| `9f23d12` | 10/10 | 10/10 | 10/10 | 0/10 | 10/10 |
| `3f06815` (HEAD) | 10/10 clean (`SUMMARY groupint 10 / 10 clean`) | | | | |
| `ea7fc51` (89b8dbf's parent) | **0/10**: every run `exit 1`, `problems: ["collector exited: 0"]`, `verify 1` | | | 0/10 left | n/a |

A sample line at 9f23d12:
`{"post": 200, "exit": 0, "problems": null, "verify": 0, "collectors": [3023306], "left_running": [], "collector_log_listed": true}`.
On the parent, 10 of 10 fail, so Z-1 was deterministic here and not load-dependent.

### (b) The Collector killed by hand (at HEAD, 3 runs each, then a group SIGINT)

- `kill -9 <collector>`: `exit 1`, `problems: ["collector exited: -9"]`, `verify 1`, 3/3.
- `kill -TERM <collector>`: `exit 1`, `problems: ["collector exited: 0"]`, `verify 1`, 3/3.

**Confirmed.**

### (c) `collector.log`

- It is in the run directory and listed in `files` with its sha256. At HEAD:
  `{'bytes': 2863, 'file': 'collector.log', 'sha256': '01be94c7…'}`.
  Its last signal line is `"signal": "terminated"`, never `"interrupt"`.
- Flipping one byte (byte 10) makes verify fail, at 9f23d12 and at HEAD alike:
  `! …: collector.log sha256 is 90aa0b96…, MANIFEST.json says 01be94c7…`, exit 1.
- **The A3f seal covers it at HEAD.** I flipped the byte and also rewrote that
  entry's `sha256` to match the changed file. Verify still fails:
  `MANIFEST.json's seal is '9121a51f…', its contents seal to '83f983d0…': the manifest was changed after the run sealed it`,
  exit 1.

**Confirmed.**

### (e) The "214 s → 46 s" claim (`WORKPLAN.md` §4, A3e line)

These are the `check (macos-latest, 3.12)` job, its `make check` step and the
pytest summary line, with `check (ubuntu-latest, 3.12)` for comparison:

| commit | run | macOS job (id) | started → completed | job | `make check` step | pytest line | concl. | ubuntu-3.12 job |
|---|---|---|---|---|---|---|---|---|
| `040b194` | 38014798470 | — | 01:51:51 → 01:52:50Z | 59 s | — | — | success | 17 s, success |
| `ea7fc51` | 38103344694 | 114363637814 | 01:53:37 → 01:54:34Z | 57 s | 45 s | `294 passed, 3 skipped in 42.58s` | success | 17 s (step 7 s), success |
| `89b8dbf` | 38153590210 | 114511891223 | 15:59:52 → 16:03:43Z | 231 s | 218 s | `4 failed, 297 passed, 4 skipped in 214.53s` | **failure** | 19 s (step 11 s), success |
| `9f23d12` | 38154402116 | 114514270878 | 16:11:25 → 16:12:31Z | 66 s | 51 s | `302 passed, 4 skipped in 46.29s` | success | 20 s (step 9 s), success |
| `0ed7fb3` | 38154524754 | — | 16:13:12 → 16:14:20Z | 68 s | | | success | 20 s |
| `46b2c15` | 38155308779 | — | 16:24:22 → 16:25:30Z | 68 s | | | success | 22 s |
| `3f06815` | 38158019828 | — | 17:03:27 → 17:04:40Z | 73 s | | | success | 22 s |

- The 214 s is the pytest time of **89b8dbf's failing macOS job**. Its four
  `test_shutdown` failures each sat out `PATIENCE = 60 s` or the readiness
  wait (`never printed 'zoo capture: the raw bytes are the record…'`,
  `CollectorRefused: the Collector did not report ready`).
- "214 → 46" therefore compares a failing run with a passing one. It is not a
  slow suite made fast.
- Before A3e the macOS pytest time was **42.58 s** (`ea7fc51`), and 9f23d12
  brought it back to 46.29 s, with about 8 more tests.
- What the CI data supports is narrower: 9f23d12 is what turned the macOS leg
  green. The runner's behaviour is consistent with the getfqdn cause, but CI
  did not show it directly. The commit message says the cause was reproduced
  only on Linux, by making `getfqdn` slow on purpose.
- There was no rerun of 89b8dbf: one run per sha.

**Bin: thread.** Change the §4 wording to "macOS red (4 tests hit the 60 s
wait, 214 s) → green, 46 s against a 43 s baseline". The plan is the builder's file.

### (f) Is 9f23d12 one concern, and why is it not its own batch?

**One concern: yes.** The change is a sink bind that does no name lookup,
plus the matching stand-in fix, SPEC §3.7, a CHANGELOG line under A3e, and
one test. The area prefix `sink:` is honest.

It is a defect that has been latent since the sink's first batch:
`HTTPServer.server_bind` calls `getfqdn`. A3e's new subprocess tests exposed
it. Filing it under A3e matches §0.1:

- step 4 says that when a batch fails verification, the **same batch** is
  dispatched again with the failure appended;
- step 8 says that a red pushed tip is not a finished run, and that an amended
  batch is a new commit on top, never a force-push.

Both shas sit in the row, and §4 records the reason.

One slip against step 8's letter: §4 says "New commit on top". Step 8 wants
"the replaced sha … recorded with the reason". 89b8dbf is not replaced. It
stays on `zoo` as a commit that is **red on macOS**, so a bisect over `zoo`
can land on it. §4 does name it as the failing one, which is enough.

My view: that is correct. A separate batch row would have bought nothing but
a second dispatch. Next time, though, the A3e row's "done" should say that
89b8dbf alone is red on macOS. **Bin: thread.**

### (g) Shutdown order: SPEC §4.6 against the code

- **The order is kept** (`capture.py` `stop()`, HEAD `:386-401`):
  1. raw stops;
  2. `raw.settle(flush_wait=10.0)`, and a timeout is said aloud;
  3. `check_collector()` (the last look), then `running.stop()`: SIGTERM,
     `wait(10)`, SIGKILL, `wait(10)`, and a SIGKILL is said aloud;
  4. json stops and settles;
  5. `_finish`.
- **An exit before SIGTERM is still a problem**, including one during the
  flush wait. The last look comes after `settle`, which matches §4's reading.
  M2 shows the tests hold the placement.
- **Double Ctrl-C** (two group SIGINTs 50 ms apart, real Collector): 3/3 exit
  0, no problems, verify 0, nothing left running. The handler stays installed
  through `stop()` (`cli.py:391-394` restores it only afterwards), so the
  second SIGINT only calls `request_stop()` again.
- **SIGTERM to the zoo PID**: 3/3 clean, the same as SIGINT.
- **SIGKILL to the zoo**: the Collector was left running (`left_running: [3024630]`)
  and the run is unsealed, so verify fails. This is stated in SPEC §4.6.
  **Confirmed as stated.**
- **SIGHUP to the process group**, which is what a terminal closing or an ssh
  drop sends. This is **not stated** in SPEC. `STOP_SIGNALS = (SIGINT, SIGTERM)`
  (`cli.py:79`), so the zoo dies of SIGHUP (exit -1) without stopping its
  Collector. The Collector, now in its own session, never sees the HUP:
  **still alive 8 s later** (`SETTLE=8`, `left_running: [3024732]`). The run
  directory has no `ended_at` and no seal, and verify fails.
  - This is new with A3e. Before, the Collector shared the group and died with it.
  - It is loud, not silent: the next `zoo capture` refuses on the held port
    with exit 2 and the port named.
  - It still breaks SPEC §4.6's own sentence, "a run that cannot be stopped
    … is a Collector left holding 4320".

  **Bin: next batch.** Either add SIGHUP to `STOP_SIGNALS`, or state it next
  to the SIGKILL sentence. Until then the operator note for Z4 is not to close
  the capture's terminal.
- **Ctrl-C during the readiness wait** (a group SIGINT 0.25 s after start):
  the Collector child is stopped (`3025210 gone`) and no directory is created,
  as SPEC says. The zoo then ends with a **`KeyboardInterrupt` traceback and
  exit -2**, not a one-line refusal. Cosmetic. **Bin: thread.**
- **A window between the last look and `stop()`'s `poll()`** (`collector.py:249`):
  a Collector that dies in the microseconds between them is never recorded.
  That cannot be told apart from "looked at one last time". **thread** (no action).
- **An uncaught `TimeoutExpired` after SIGKILL** (`collector.py:255`): a child
  that ignores SIGKILL for 10 s (D-state) raises out of the `finally`, and the
  manifest is never finished. This is an extreme edge. **thread.**

### Bins

| finding | bin |
|---|---|
| SIGHUP (terminal closed) kills the zoo and leaves the Collector running; not stated in SPEC §4.6 | **next batch** |
| §4 "214 s → 46 s" compares 89b8dbf's failing macOS job with 9f23d12's passing one (baseline 42.58 s at `ea7fc51`) | thread |
| 89b8dbf stays red on macOS on `zoo` (bisect hazard); not "replaced", so step 8's wording does not quite fit | thread |
| Timed waits (`settle`, `process.wait`) sit outside the `sleep` seam; they can be injected, but SPEC §4.8's "sleeps on its own" sentence is loose | thread |
| Ctrl-C during readiness ends with a traceback and exit -2 | thread |
| `TimeoutExpired` after SIGKILL is not caught | thread |

Nothing here **blocks the Z4 capture**: (a), (b), (c) and (d) hold with the
real binary.

Cleanup: no `otelcol-contrib` and no `spanweave_zoo.cli` left from this review
(checked with `ps -eo pid,pgid,args | grep a3e` → none). The worktrees are
removed and pruned.
