# Section a3d — cold review of 52c33ba (A3d)

`verify: a path that is not a capture is a refusal, and CI re-hashes a real one`

Reviewer: aux (cold reader). Ports used: 4420 (raw), 4421 (json), 4422 (collector http), 4423 (collector grpc) only.
Worktrees: `$SP/wt-a3d-commit` (52c33ba), `$SP/wt-a3d-parent` (derived parent), both under the scratchpad, both removed at the end.

## 0. Derived parent

```
$ git rev-parse 52c33ba^
01cfb7e3cda70069fa3d8be2e1766556dabc24e5   # "plan: A3c done, and its mutation is caught by only one of its two tests"
```

## 1. Spec / changelog in the same commit — confirmed

- SPEC.md §5.6: the refusal, exit 2, default-root exception, the committed fixture `make verify` reads (SPEC.md +1013..+1030, +1085..+1102 in the diff).
- SPEC.md §7: the exemption is the path `spanweave_zoo/audit.py`.
- CHANGELOG.md: an `## A3d` entry with four bullets matching the four concerns.
- README.md: the verify paragraph, the `make verify` paragraph, operator step 5, and the Provenance sentence.

## 2. Parent run

I copied the commit's `tests/test_cli.py`, `tests/test_gates.py`, `tests/test_readme.py`, `tests/test_fixture_capture.py` and `tests/fixtures/` into the parent worktree, keeping the **parent's** `tests/gates.py` (the code under test).

| test (new in 52c33ba) | parent | kind |
|---|---|---|
| test_cli::test_verify_of_a_named_path_that_is_not_a_capture_refuses | FAIL | assertion `assert 0 == 2` |
| test_cli::test_verify_of_a_named_file_refuses | FAIL | assertion `assert 0 == 2` |
| test_cli::test_verify_of_a_named_directory_holding_no_run_refuses | FAIL | assertion `assert 0 == 2` |
| test_cli::test_verify_with_no_path_tolerates_a_repository_with_no_captures | pass | (guards the default-root exception, so it should pass on the parent) |
| test_gates::test_the_exemption_is_one_path_and_not_a_file_name | FAIL | assertion `AssertionError: spanweave_zoo/sink/audit.py / assert [] == ['no-analyser-imports']` |
| test_fixture_capture::test_make_verify_reads_the_committed_capture | FAIL | assertion (Makefile has no `zoo verify tests/fixtures/capture`) |
| test_fixture_capture (other 5) | pass | data tests over the copied fixture; parent's `zoo verify` already re-hashes a valid run |
| test_readme (3) | pass | drift test, green until something drifts (WORKPLAN §4 says so honestly) |

Totals: test_cli + test_fixture_capture + test_readme with the commit's gates.py gave 4 failed / 46 passed; test_gates with the parent's gates.py gave 1 failed / 30 passed.
**Verdict: the parent run is real, not vacuous.** No collection errors, all failures are assertions, and three of the four concerns are red on the parent. For the README test, I demonstrated red by mutation in §7(d).

Extra, by running: on the parent, `spanweave_zoo/sub/audit.py` containing `import spanweave` passes `make gates` (30 passed). The hole was real.

## 3. Mutations (commit worktree, each reverted)

| # | diff | result |
|---|---|---|
| M1 | `cli.py:200` `if named:` → `if False and named:` | 3 FAILED: test_verify_of_a_named_path_that_is_not_a_capture_refuses, test_verify_of_a_named_file_refuses, test_verify_of_a_named_directory_holding_no_run_refuses (158 passed) |
| M2 | `cli.py` main: `return verify(Path(args.path), named=True)` → `return verify(Path(args.path))` | same 3 FAILED |
| M3 (inverse) | `cli.py` main: `return verify(CAPTURES)` → `return verify(CAPTURES, named=True)` | 1 FAILED: test_verify_with_no_path_tolerates_a_repository_with_no_captures |
| M4 | `gates.py:94` `PurePath(path).as_posix() in EXEMPT_PATHS` → `PurePath(path).name in {PurePath(p).name for p in EXEMPT_PATHS}` (basename match) | 1 FAILED: test_the_exemption_is_one_path_and_not_a_file_name (`assert [] == ['no-analyser-imports']`) |
| M5 | Makefile: delete `uv run zoo verify tests/fixtures/capture` | 1 FAILED: test_make_verify_reads_the_committed_capture |
| M6 | README/contract drift | see §7(d) |
| M7 | one byte of the fixture | see §7(c) |

## 4. Clock / randomness / network in `spanweave_zoo/`

`git show 52c33ba -- spanweave_zoo/ | grep '^+' | grep -E "time\.|datetime|random|socket|urllib|http\.client|subprocess|import "` returns nothing. The only source change is `verify()`'s `named` branch and argparse `default=None`. Clean.

## 5. Commit form

Subject `verify: <one line>`. The body names A3d and SPEC §§5.6, 7. It carries four concerns (refusal, fixture, README digest test, gate path), but all four are what the A3d row bundles, so this is one batch. Acceptable.

## 6. make check / verify / install-check (commit worktree)

```
ruff check: All checks passed!   ruff format --check: ok
mypy --strict spanweave_zoo: Success: no issues found in 7 source files
pytest: 161 passed, 3 skipped in 5.29s
gates: 31 passed
zoo verify            -> no captures under captures/ -- nothing to re-hash
zoo verify tests/fixtures/capture -> 1 capture(s) ... kind=recorded, 2 body/bodies, 0 problem(s) / every recorded body still hashes
install-check: OK -- what ships works
```
Skipped: the 3 `tests/test_collector_real.py` tests (lines 109, 127, 246), because `collector/otelcol-contrib` is absent in a worktree. Their CI leg is A0b's.

## 7. Specific claims

### (a) `zoo verify <not-a-capture>` exits 2 naming the path — CONFIRMED

Run from `$SP/a3d-claimA`, with the commit's `.venv/bin/zoo`:

```
zoo verify ./absent                       -> "zoo verify: absent is not a capture: no MANIFEST.json, no raw/, and no <project>/<run-id> under it. Nothing was checked (SPEC.md section 5.6)."  exit=2
zoo verify afile        (regular file)    -> "... afile is not a capture ..."      exit=2
zoo verify emptydir                       -> "... emptydir is not a capture ..."   exit=2
zoo verify withfiles    (files + subdir/file, no run) -> "... withfiles is not a capture ..." exit=2
zoo verify captures/z4/2026-10-09T12-00-0OZ  (typo'd run id; real run ...00Z beside it) -> "... is not a capture ..." exit=2
zoo verify captures/z4/2026-10-09T12-00-00Z  (the real one)  -> every recorded body still hashes  exit=0
(cwd with empty captures/)   zoo verify   -> "no captures under captures/ -- nothing to re-hash"  exit=0
(cwd with no captures/ at all) zoo verify -> same, exit=0
(cwd with empty captures/)   zoo verify captures   (typed) -> "captures is not a capture"  exit=2
```
For contrast, on the parent `zoo verify ./absent` gives "no captures under absent/ -- nothing to re-hash", exit=0.

The path is printed as the operator typed it (`./absent` is printed as `absent`, because of `Path` normalisation). That is still recognisable.

Edge cases observed (see A3d-2):
```
zoo verify captures/z4      (a project dir holding one intact run)
  captures/z4/2026-10-09T12-00-00Z/json: kind=none declared, 0 body/bodies, 1 problem(s)
  captures/z4/2026-10-09T12-00-00Z/raw:  kind=none declared, 0 body/bodies, 1 problem(s)
  ! .../json: no readable MANIFEST.json ...
  ! .../raw: no readable MANIFEST.json ...
zoo verify: 2 problem(s). A capture is immutable (CLAUDE.md section 0.6): these bytes are not the bytes that were recorded.
exit=1        (identical on the parent)
zoo verify half      (a dir with only json/0001.json, named)   -> "not a capture", exit 2
zoo verify root2     (the same dir as root2/z4/half)          -> "no readable MANIFEST.json", exit 1
```

### (b) The fixture was made by the real tee — CONFIRMED (bodies and heads reproduced byte-for-byte)

**Hand decode of `raw/0001.body`** (128 bytes, protobuf, stdlib-only decoder at `$SP/a3d_pbdecode.py`, no repo deps):
```
protobuf spans: [{'traceId': '4bf92f3577b34da6a3ce929d0e0e4736', 'spanId': '00f067aa0ba902b7', 'name': 'GET /checkout', 'kind': 2, 'start': 1700000000000000000, 'end': 1700000000500000000}]
json spans:     [{'traceId': '4bf92f3577b34da6a3ce929d0e0e4736', 'spanId': '00f067aa0ba902b7', 'name': 'GET /checkout', 'kind': 2, 'startTimeUnixNano': '1700000000000000000', 'endTimeUnixNano': '1700000000500000000'}]
ids equal: True
```

**Headers.**
- json side (`json/0001.headers.raw`): `User-Agent: OpenTelemetry Collector Contrib/0.162.0 (linux/amd64)`, `Content-Type: application/json`, `Accept-Encoding: gzip`, `Content-Length: 391`, Host on an ephemeral port (37027). This is the otelcol-contrib 0.162.0 `otlp_http` exporter.
- raw side (`raw/0001.headers.raw`): `Host`, `Accept-Encoding: identity`, `Content-Length: 128`, `Content-Type: application/x-protobuf`, and **no User-Agent**. That is the exact signature of Python's `http.client.HTTPConnection.request` (it auto-adds `Host` and `Accept-Encoding: identity`; urllib would add `User-Agent: Python-urllib`). So the raw side is a **hand-built client** (tests/otlp.py's bytes POSTed with http.client), not an OTLP SDK exporter.

**Independent reproduction.** I ran the real tee from the commit worktree with the real Collector copied in, on my port block:
```
zoo capture --project z4 --run-id a3d-repro --kind recorded ... --port 4420 --json-port 4421 --collector-port 4422 --collector-grpc-port 4423
POST otlp.export_trace_service_request() via http.client -> status 200
cmp json/0001.json   vs fixture -> identical (391 bytes, sha256 403f27e1...)
cmp raw/0001.body    vs fixture -> identical (128 bytes, sha256 abb3460e...)
diff json/0001.headers.raw: only "Host: 127.0.0.1:4421" vs "Host: 127.0.0.1:37027"
diff raw/0001.headers.raw:  only "Host: 127.0.0.1:4420" vs "Host: 127.0.0.1:33131"
```

**Is the provenance text truthful?** Yes. `tests/test_fixture_capture.py:1-19` and SPEC §5.6 say "tests/otlp.py's hand-built export into the raw sink, the stock Collector behind it, its JSON re-encoding into the json sink … on a clock the run chose". All of that matches. The timestamps (`09:00:01…09:00:04`) are an injected clock, which the text says. The project manifest's `framework: "none: tests/otlp.py hand-built this export"` is honest. One oddity is in thread A3d-5.

**`.gitattributes` on a fresh clone.** I made `git clone --no-local` clones of 52c33ba under the scratchpad and re-hashed every fixture file against MANIFEST.json (`$SP/a3d_mcheck.py`):

| clone | mismatches | cmp vs worktree |
|---|---|---|
| plain | 0 / 8 | identical |
| `-c core.autocrlf=true` | 0 / 8 | identical |
| `autocrlf=true`, `.gitattributes` removed from worktree **and index** (control) | **4 / 8** (bodies.jsonl, forwards.jsonl, json/0001.headers.json, raw/0001.headers.json) | — |

`git check-attr text` gives `unset` for the fixture files. So `-text` is load-bearing and works. What it actually protects, though, is the **LF** files. The CRLF heads came through unharmed even in the control, because git does not convert a file that already contains CRLF (see A3d-4). (A first control attempt that removed only the worktree copy of `.gitattributes` showed 0 mismatches, because git falls back to the index copy. I redid it as above.)

### (c) CI's `make verify` reads it — CONFIRMED

`gh run list --branch zoo`: run **38011882707** (52c33ba, CI, success) and run **38014798470** (040b194, CI, success, plus the `collector` leg).

The 52c33ba log has the same lines on all 5 check legs (ubuntu 3.11/3.12/3.13/3.14, macos 3.12):
```
check (ubuntu-latest, 3.14)	Run make check	uv run zoo verify
check (ubuntu-latest, 3.14)	Run make check	zoo verify: no captures under captures/ -- nothing to re-hash
check (ubuntu-latest, 3.14)	Run make check	uv run zoo verify tests/fixtures/capture
check (ubuntu-latest, 3.14)	Run make check	zoo verify: 1 capture(s) under tests/fixtures/capture/:
check (ubuntu-latest, 3.14)	Run make check	  tests/fixtures/capture: kind=recorded, 2 body/bodies, 0 problem(s)
check (ubuntu-latest, 3.14)	Run make check	zoo verify: every recorded body still hashes to what was recorded
check (macos-latest, 3.12)	Run make check	zoo verify: 1 capture(s) under tests/fixtures/capture/:
check (macos-latest, 3.12)	Run make check	  tests/fixtures/capture: kind=recorded, 2 body/bodies, 0 problem(s)
```
The 040b194 log has the same lines on all 5 check legs (the step label is shown as "UNKNOWN STEP" by `gh`).

**Mutation, one byte** (`raw/0001.body[0x60] ^= 0x01`):
```
  ! tests/fixtures/capture: raw/0001.body sha256 is dfc479a2..., MANIFEST.json says abb3460e...
make: *** [Makefile:43: verify] Error 1      -> make verify exit=2
```
Also, a head file truncated to 0 bytes (I meant to convert CRLF to LF, but my one-liner truncated the file; it is still a valid mutation): `raw/0001.headers.raw sha256 is e3b0c442..., MANIFEST.json says 82d0ca28...`, `make verify` exit 2. With the fixture directory moved away: `zoo verify: tests/fixtures/capture is not a capture … Nothing was checked`, `Error 2`. That confirms the SPEC sentence "a fixture that went missing makes make verify exit 2". All reverted; worktree `git status` clean.

### (d) The README contract-sha test goes red on drift — CONFIRMED

```
clean:                              3 passed
+1 byte to EXPORT-CONTRACT.md:      FAILED test_each_printed_digest_is_the_digest_of_the_file_on_disk
                                    E AssertionError: EXPORT-CONTRACT.md and the sha256 the README prints for it have drifted. ...
+1 byte to ZOO-BRIEFS.md:           FAILED test_each_printed_digest_is_the_digest_of_the_file_on_disk
                                    E AssertionError: ZOO-BRIEFS.md and the sha256 the README prints for it have drifted. ...
one hex char of the README digest:  FAILED test_each_printed_digest_is_the_digest_of_the_file_on_disk
```
All reverted.

### (e) The import gate exempts `spanweave_zoo/audit.py` by path — CONFIRMED

Real files in the commit worktree, `make gates`:
```
spanweave_zoo/sub/audit.py: "import spanweave"  -> FAILED test_the_package_imports_neither_analyser
   E AssertionError: spanweave_zoo/sub/audit.py:1: [no-analyser-imports] imports 'spanweave'; only spanweave_zoo/audit.py may consume ...
spanweave_zoo/audit.py: "import spanweave / from spanweave_live import serve" -> 31 passed
spanweave_zoo/audit_helpers.py: "import spanweave" -> FAILED (as before)
parent 01cfb7e, spanweave_zoo/sub/audit.py -> 30 passed (the hole)
```
`check_package` passes `file.relative_to(PACKAGE_ROOT.parent)` (gates.py:127), so the path is repo-relative. The gate's tests cover both sides: `test_gate_exempts_the_audit_module` (positive, `spanweave_zoo/audit.py`, 10 parametrised import forms) and `test_the_exemption_is_one_path_and_not_a_file_name` (negative: `spanweave_zoo/sink/audit.py`, `spanweave_zoo/replay/audit.py`, `tests/audit.py`, `audit.py`). Both use `check_source` with string paths. The package-level form is covered by `test_the_package_imports_neither_analyser`, which I drove with real files above.

### (f) cli.py's docstring says what the code does — CONFIRMED

`cli.py:24-42` at 52c33ba lists three statuses:
- **1** for checked-and-failed: digest/length, missing, unlisted, unreadable manifest, no `ended_at`, unnamed `kind`, `problems`. This matches `manifest.problems`, manifest.py:751-770. An absent `kind` is deliberately not a problem, for `zoo sink` captures, and "a `kind` the spec does not name" is worded to fit.
- **2** for "not a capture": matches `verify()`'s `named` branch, cli.py:198-208.
- **0** for all-hash, or the default root empty: matches.

The F1 text ("cli.py:24-29 documents the opposite of what the code does") is fixed. The "Three subcommands today" list was true at 52c33ba (A4 adds replay later).

## 8. Findings

**A3d-1 — A terminal Ctrl-C reaches the Collector child too, and every operator capture ends with `problems: ["collector exited: 0"]`, so `make verify` fails on it.** Bin: **blocks Z4 capture**. Owner: the capture/Collector launch (A3a/A2 code, not A3d's diff). I found it while reproducing (b).
- `collector.py:273` starts `otelcol-contrib` with `subprocess.Popen(...)` and no `start_new_session`/`process_group`, so the Collector shares zoo's process group.
- A tty Ctrl-C sends SIGINT to the whole foreground group. README step 4 tells the operator to press **Ctrl-C**, under `uv run`, which keeps the same group.
- The Collector shuts down in about 1 ms. zoo notices on its next 200 ms hop or in `stop()`. Then `check_collector()` (capture.py, `stop()`: "Asked before it is stopped") records the exit as a problem.
- Reproduced on my port block by simulating Ctrl-C with `kill -INT -- -<pgid>`: **7/7** runs (r1, r3, r4, t1–t4) printed `MANIFEST.json written: kind=recorded, PROBLEM: collector exited: 0`.
- `zoo verify` on r1 printed `MANIFEST.json records a problem from the run: collector exited: 0`, exit=1.
- SIGINT to the zoo pid alone gave no Collector problem (r5, h6–h11).
- `collector.py`/`capture.py` are unchanged between 52c33ba and 040b194, so the tip has the same behaviour.
- The test only does `signal.raise_signal(SIGINT)` in-process (`tests/test_capture.py:505`) and never signals a group that holds a real child, so nothing catches this.
- The json body still landed in r1, because the Collector flushes on its own SIGINT. The capture bytes are fine, but the manifest says the run failed, and `make check` goes red as soon as the operator commits it.
- Possible fixes, for the builder to decide: launch the Collector in its own session/process group; and/or do not record an exit as a problem once a stop has been requested. That second option is a §4.6 decision.

**A3d-2 — `zoo verify captures/<project>` treats `raw/` and `json/` as runs and tells the operator that intact bytes are "not the bytes that were recorded".** Bin: **next batch**.
- `_run_directories` (`cli.py:174-185`) globs `*/*` under any non-run directory. Named at project depth, it returns `<run>/raw` and `<run>/json` and reports "no readable MANIFEST.json", exit 1, over an intact capture. It never checks the actual run. Reproduced at 52c33ba and on the parent (it predates A3d), and `_run_directories` is unchanged at 040b194.
- Related: a half-capture named directly says "not a capture … Nothing was checked" and exits 2, while the same directory found from a root says "no readable MANIFEST.json" and exits 1. That inconsistency was F1's second clause. Both are non-zero now, so it is no longer a silent pass.
- The failure summary "these bytes are not the bytes that were recorded" (`cli.py:232-236`) is printed for *any* problem, including no `ended_at`, a recorded `problems` entry, or no manifest. For A3d-1's capture it falsely accuses the bytes.
- This is non-zero (safe direction) but untrue, and it sits squarely in A3d's "refuses what it did not check" remit. The README only tells the operator to use `make verify` or `captures/z4/<run-id>`, so it does not block Z4.

**A3d-3 — `zoo capture` hung once after a double SIGINT. `threading.Event.set()` in a signal handler can self-deadlock.** Bin: **thread**.
- My first tee run was under `timeout 60`, and `pkill -INT -f` hit both `timeout` and zoo, so zoo got SIGINT more than once. It then never printed "stopping".
- State afterwards: main thread in `futex_do_wait`, the two serve threads in `poll`, the Collector `<defunct>` (never reaped), MANIFEST.json still the provisional one with no `ended_at`. A further SIGINT did nothing, and it needed `kill -9`.
- I did not reproduce it in 10 further attempts (40-signal bursts at 3–18 ms spacing; four `timeout`-wrapped runs).
- Plausible mechanism: `Event` is `Condition(Lock())`, with a non-reentrant lock. If the handler runs `request_stop()` → `Event.set()` while the main thread is inside `Event.wait(poll_interval)` holding that lock (after the timed wait reacquires it), `set()` blocks forever on the same thread. `capture.py:305-312` says setting an event is the safe thing to do in a handler, but it is not strictly safe. ptrace is blocked here (yama), so I could not get a stack. The faulthandler-instrumented runs never hung.
- The failure is visible and recoverable (no `ended_at`, so verify fails), so this is a thread. A signal-safe alternative is a flag variable or `signal.set_wakeup_fd`.

**A3d-4 — `.gitattributes`' stated reason is the wrong file class, and the two contract documents are not covered.** Bin: **thread**.
- `.gitattributes:1-7`, CHANGELOG A3d and WORKPLAN §4 say `-text` keeps the CRLF heads intact. In an `autocrlf=true` clone without the attribute, the heads survive, because git leaves CRLF-bearing files alone. The four **LF** files (bodies.jsonl, forwards.jsonl, both headers.json) are the ones that change. The attribute is right; only the reason is misnamed.
- Separately, `EXPORT-CONTRACT.md`/`ZOO-BRIEFS.md`, also "the record, byte for byte", are not `-text`. In the `autocrlf=true` clone they hash to `bc7336ab…`/`fc813390…` instead of README's `aeadb64b…`/`c82487fd…`, so `tests/test_readme.py` fails on such a clone. CI has no Windows leg, so this does not bite today.

**A3d-5 — The fixture's chosen clock is internally inconsistent, and the project-manifest check is strict at second precision.** Bin: **thread**.
- The fixture's `project_manifest.started_at` is `09:00:30`, 26 s **after** the capture's `ended_at` `09:00:04`. The §5.3 check only rejects "older than the capture", so this passes. A3d is never regenerated, so it stays, but the audit (A5) should not read these timestamps as ordering evidence.
- My harness also found that a project manifest written with second-precision `started_at` in the same second as the capture's microsecond `started_at` is rejected as "an earlier run's document" (r2). That is low risk for Z4, because the operator starts the app after the capture is up.

**A3d-6 — The `Makefile:22` comment still says "except audit.py".** The gate is now path-based (`spanweave_zoo/audit.py`). One word. Bin: **thread**.

## 9. Cleanup

Worktrees `$SP/wt-a3d-commit` and `$SP/wt-a3d-parent` were removed with `worktree remove --force` and `worktree prune`. The scratch clones, the tee captures and the copied Collector binary went with them or were deleted. No processes are left on 4420–4429. `git -C /home/msi/git/spanweave-zoo status --short` is empty.
