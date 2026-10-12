# Section a3b — 810f2db "manifest: written once, at the end, and covering every file in the capture"

Reviewer: aux (cold), 2026-10-10/11. Port block 4400–4409 (used 4400–4407).
Worktrees (absolute, under scratchpad SP): `$SP/wt-a3b-commit` (810f2db), `$SP/wt-a3b-parent`
(derived `git rev-parse 810f2db^` = **957149d**, a `plan:` commit — "plan: A3a done, …"), `$SP/wt-a3b-head`
(040b194, for `.headers.raw`). Real Collector binary copied into each worktree's `collector/` (gitignored).
All captures written under `$SP/a3b-run/captures`, never in the repo.

## 1. Spec + CHANGELOG in the same commit

`git show --stat 810f2db`: SPEC.md (+291/−… across §2, §2.5, §3.5, §4.5, §4.6, §5, §5.3, §5.5, §5.6), CHANGELOG.md
"## A3b — …" entry present, README updated. Behaviour and spec move together. **OK.**
SPEC §5.3 has the four-outcome table (SPEC.md:885-890 at 810f2db).

## 2. Tests red on the derived parent (957149d)

Copied the commit's five changed test files (test_capture, test_collector_real, test_manifest, test_sink, test_tee) verbatim:

`47 failed, 61 passed`. Failure kinds:

| count | kind |
|---|---|
| 26 | `TypeError: label() missing 1 required keyword-only argument: 'project_manifest'` (API — vacuous) |
| 17 | `TypeError: Object of type PosixPath is not JSON serializable` (API — vacuous) |
| 2 | `AttributeError: cli has no attribute 'Progress'` (API — vacuous) |
| 1 | `AttributeError: manifest has no attribute 'FORWARD_JOURNAL_NAME'` (API — vacuous) |
| 1 | **assertion**: `test_sixteen_hundred_bodies_cost_the_same_each` — `per-body cost grew with the run: 1071 us/body … 4578 us/body` (real) |

So the verbatim run is **vacuous except for the cost test**. As the commit body says it did, I then adapted
only `hand_written_capture` to the parent API (label with `project_manifest=<doc>`, `append_body`,
`finish(run, ended_at=…)`), assertions untouched:

| test (test_manifest.py) | parent result |
|---|---|
| test_a_rewritten_content_type_in_headers_json_fails_verify | FAIL `assert 0 == 1` (verify exit 0) — real |
| test_a_kind_the_spec_does_not_name_fails_verify | FAIL `assert 0 == 1` — real |
| test_a_capture_with_no_ended_at_fails_verify_and_says_how_to_remove_it | FAIL `assert 0 == 1` — real |
| test_a_problem_recorded_during_the_run_fails_verify | FAIL `assert 0 == 1` — real |
| test_every_file_in_the_run_directory_has_a_digest | FAIL AttributeError `FILES` (vacuous) |
| stale-hash / unlisted-body / headers-file-without-body (A3 tests) | pass (expected: pre-existing behaviour) |

This reproduces the commit body's "four reassuring passes" claim exactly. The capture-level F4 tests
(`test_a_project_manifest_rewritten_mid_run_lands_as_the_end_of_run_copy`,
`…older_than_the_capture_is_a_problem_and_exits_non_zero`) are red on the parent only by API TypeError — no
assertion-level parent evidence for them; mutation M2/M4 below supply it.

Side effect noted: the parent run's API-crashing capture tests leaked 8 Collector children (4 stub, 4 real)
which I killed (`pytest-5063..5077`, `wt-a3b-parent/collector/otelcol-contrib`). That is the parent's
behaviour under foreign tests, not a defect of 810f2db.

## 3. Mutations (commit worktree; each reverted, `git status` clean after)

Full suite (`tests/`, collector present: 144 tests) per mutation unless noted.

- **M1 (the commit's named one)** `_rehashed`: `if name.endswith(HEADERS_SUFFIX): continue` →
  `1 failed, 143 passed`: `FAILED tests/test_manifest.py::test_a_rewritten_content_type_in_headers_json_fails_verify`
  `AssertionError: assert 0 == 1`. **Caught, by exactly one test.**
- **M2** `_project_copy`: `if written < capture_started:` → `if False and …` → `2 failed`:
  `test_capture.py::test_a_project_manifest_older_than_the_capture_is_a_problem_and_exits_non_zero`,
  `test_manifest.py::test_a_project_manifest_older_than_the_capture_is_a_problem_and_not_copied`
  (`assert {'contract_version': …} is None`). Caught.
- **M3** `_incomplete`: `for problem in document.get(PROBLEMS) or []:` → `for problem in []:` → ≥5 failures
  (`…older_…`, `test_a_problem_recorded_during_the_run_fails_verify`, `test_a_journal_line_that_cannot_be_read…`,
  `…that_is_gone_by_the_end…`), all `assert 0 == 1`. Caught.
- **M4** copy at start (F4 regression): in `Capture.start` after `_labelled = True`, snapshot the project manifest to a
  temp file and point `_project_manifest` at it → `1 failed`:
  `test_a_project_manifest_rewritten_mid_run_lands_as_the_end_of_run_copy`
  (`{'model': 'the-previous-runs-model'} != {'model': 'the-recorded-runs-model'}`). Caught.
- **M5** `Progress.__call__`: `except (BrokenPipeError, ValueError)` → `except (ValueError,)` → `1 failed`:
  `test_a_closed_stdout_ends_the_run_and_leaves_the_manifest_complete` (`BrokenPipeError: [Errno 32]`). Caught.
- **M6** quadratic regression: `journal_body` also does `update(run, …_append(d,'shadow',…))` →
  `test_sixteen_hundred_bodies_cost_the_same_each` FAIL `1266 us/body … 7636 us/body`. Caught.

## 4. Clock / randomness / network in spanweave_zoo/

Diff grep (`time.|datetime|random|socket|urllib|http.client|subprocess|os.`): only
`datetime.fromisoformat` (manifest.py `_moment_of`, parses written values, no clock read) and
`os.open/os.dup2/os.close` in `cli.py` `_silence` (cli is the world-touching module). `zoo sink`'s new
`finish(…, ended_at=_system_clock())` goes through the existing seam. **OK.**
(Test-side: `test_sixteen_hundred_bodies_cost_the_same_each` reads `time.perf_counter` — see A3b-5.)

## 5. One concern / message form

`manifest: <one line>`, body names A3b, F4/F7/F9/F10/F12 and SPEC sections. The commit carries five
review items (journal+end-assembly, every-file coverage, verify's three new refusals, project-manifest
timing, flushed/broken-pipe stdout) — broad, but it is exactly the A3b row, so one batch. **OK.**

## 6. make check (commit worktree)

`make check` exit 0: ruff + format + mypy --strict clean; `141 passed, 3 skipped` (the 3 skips are
`tests/test_collector_real.py` — binary absent in a fresh worktree); gates 30 passed; `zoo verify`
"no captures"; `zoo 0.0.1`. With the binary copied in: `tests/test_collector_real.py` 3 passed.

## 7. Specific claims

### (a) project manifest rewritten mid-run lands as the end-of-run copy — CONFIRMED (real binary)

```
pm.json at start: {"started_at": "2026-10-10T00:00:00+00:00", "model": "the-PREVIOUS-run", …}
zoo capture --project z4 --run-id a --kind recorded --project-manifest $R/pm.json --captures $R/captures \
  --port 4400 --json-port 4401 --collector-port 4402 --collector-grpc-port 4403
capture started_at=2026-10-10T11:59:53.600646+00:00
curl POST body.pb → 200
pm.json rewritten: {"started_at": "2026-10-10T11:59:55.817645+00:00", "model": "the-RECORDED-run", …}
manifest mid-run keys: ['bodies', 'collector_version', 'kind', 'sink_version', 'started_at']   (no ended_at, no project_manifest)
kill -INT <python pid>
→ "zoo capture: 2 body/bodies under …/z4/a/, MANIFEST.json written: kind=recorded"
MANIFEST.json: ended_at 12:00:08.929, project_manifest = {"model": "the-RECORDED-run", "started_at": "…11:59:55.817645+00:00", …}, problems absent
zoo verify …/z4/a → exit 0
```

### (b) older / absent / undatable project manifest — CONFIRMED, all four SPEC §5.3 rows

Real binary, ports 4400–4403, one body each, SIGINT:

| case | capture exit | project_manifest | problems | verify |
|---|---|---|---|---|
| older (`started_at` 2026-10-10T00:00Z, unchanged) | 1 | null | "…says it started at 2026-10-10T00:00:00+00:00, before this capture started at 2026-10-10T12:01:16.58…" | 1 |
| gone (rm mid-run) | 1 | null | "…could not be copied when the capture ended … cannot read …" | 1 |
| not JSON any more (`{not json` mid-run) | 1 | null | "…could not be copied … is not a JSON document" | 1 |
| no `started_at` | 1 | kept verbatim | "…carries no started_at this zoo can read…" | 1 |
| naive `started_at` "2026-12-31T23:59:59" | 1 | kept verbatim | same undatable line | 1 |
| control: rewritten mid-run with current UTC | 0 | the new doc | none | 0 |

### (c) every file listed; verify fails on each change — CONFIRMED (one gap, A3b-1)

Run dir vs manifest (capture `a`): `find -type f ! -name MANIFEST.json` = {bodies.jsonl, forwards.jsonl,
json/0001.headers.json, json/0001.json, raw/0001.body, raw/0001.headers.json}; manifest `bodies` = raw/0001.body,
json/0001.json; `files` = the other four; `diff` empty, no duplicates, every sha256 recomputed OK.

Tamper matrix (each on a fresh `cp -a` copy, `zoo verify <run>` at 810f2db):

| change | exit | line |
|---|---|---|
| control | 0 | |
| raw/0001.headers.json Content-Type rewritten | 1 | `raw/0001.headers.json sha256 is 5b75…, MANIFEST.json says f0cb…` |
| json/0001.json one byte | 1 | sha256 mismatch |
| json/0001.headers.json | 1 | sha256 mismatch |
| bodies.jsonl (+ newline) | 1 | sha256 mismatch |
| kind → "bogus" | 1 | `kind is 'bogus', which is neither real nor recorded` |
| **kind recorded → real** | **0** | — (A3b-1) |
| **kind deleted** | **0** | — (A3b-1) |
| extra raw/0002.body / extra notes.txt | 1 | `… is on disk but absent from MANIFEST.json` |
| missing raw/0001.headers.json / raw/0001.body | 1 | `… is listed in MANIFEST.json but missing` |
| files entry dropped | 1 | unlisted |
| no ended_at | 1 | `no ended_at … remove it with rm -rf <run>` |
| problems: ["x"] added | 1 | `records a problem from the run: x` |
| problems → [] / project_manifest.model edited | 0 | (A3b-1) |

`.headers.raw`: at **HEAD 040b194** (real binary, ports 4404–4407) the run dir holds raw/ and json/
`0001.headers.raw`, both in `files`; verify 0; appending one byte to raw/0001.headers.raw → exit 1
`raw/0001.headers.raw sha256 is c2f5…, MANIFEST.json says 7aca…`. At **810f2db** no `.headers.raw` is
written (A3c's), but the walk is name-agnostic: a hand-placed `raw/0001.headers.raw` before `finish` is
listed (`files = ['bodies.jsonl', 'raw/0001.headers.raw']`) and a rewrite of it is reported. So 810f2db
covers it without change, as the WORKPLAN §4 note says.

### (d) per-body cost — CONFIRMED (flat on the commit, growing on the parent)

Same harness on both (`$SP/a3b-perf.py`: `sink.Recorder` alone, N bodies of `b"body %04d"`, mean µs/body
over the whole run, median of 3 fresh runs):

| N | 810f2db µs/body | 957149d µs/body |
|---|---|---|
| 200 | 286 | 676 (691 on a repeat) |
| 800 | 293 | 1,327 (1,783) |
| 1,600 | 295 | 2,247 (2,167) |
| ratio 1600/200 | **1.03** | **3.3** |

The commit moved O(N) work to the end: `finish` costs 21 / 90 / 179 ms at 200 / 800 / 1600 (≈110 µs/body,
also flat), so even including it the commit is ≈391/405/407 µs/body.

The committed test's own measure (first 100 vs last 100 of one 1,600 run), 3× on each:
commit 268→288 (1.07), 270→294 (1.09), 273→288 (1.05) — matches the body's 273→288 (1.05).
Parent: 5430→3424 (0.63), 8506→3622 (0.43), 1808→3670 (2.03), 576→7733 (13.42), 977→3412 (3.49),
720→3531 (4.91), 600→3803 (6.34) — the body's 572→4,258 (7.44) is within that spread but the parent
figure is one sample of a very noisy metric on a shared machine (A3b-5). The whole-run mean shows the
quadratic plainly.

### (e) BrokenPipeError finalizes and exits 0 — CONFIRMED

`( zoo capture … --port 4400 … 2>err; echo zoo-exit=$? ) | head -N`, project manifest dated 2099 (so its
check passes), two POSTs:

| N | zoo exit | stderr | manifest | verify |
|---|---|---|---|---|
| 1 (break on a Collector log line) | 0 | empty | ended_at, 0 bodies | 0 |
| 2 | 0 | empty | ended_at, 0 bodies | 0 |
| 11 (break on first body's line) | 0 | empty | ended_at, 2 bodies, 4 files | 0 |
| 12 | 0 | empty | ended_at, 4 bodies, 6 files | 0 |

With the realistic project manifest (dated before the capture) `| head -1` ends the run at readiness, before
any project can run, so the end-of-run copy is the old one → exit 1 + problem. That is "exits on what the
capture was", not a defect, but an operator should not pipe `zoo capture` to `head` expecting a capture.

## Findings

**A3b-1 — `MANIFEST.json`'s own fields are unsealed; "kind flipped fails verify" holds only for an
out-of-set value.** Proposed bin: **thread.** The row and the commit body say "`kind` flipped fails verify";
the test (`tests/test_manifest.py:351-364`) flips to `"almost-real"`. A flip recorded↔real — the one the
audit would mis-key on — verifies 0, as does deleting `kind` (allowed because `zoo sink` declares none,
manifest.py:759-765), emptying `problems`, or editing `project_manifest`. Inherent while the manifest cannot
hash itself; worth a seal (e.g. the label fields journalled into a hashed file) and honest wording in the row.
Not a Z4 blocker: it needs a hand edit.

**A3b-2 — verify's closing line blames the bytes for problems that are not about bytes.** Proposed bin:
**next batch.** `cli.py:243` (HEAD) prints "A capture is immutable …: these bytes are not the bytes that
were recorded." after `kind is 'bogus'`, `no ended_at`, or a recorded project-manifest problem — e.g. on
capture `older` above, whose bytes are all intact. An operator reading Z4's verify output could think a
capture was tampered with when the project manifest was merely stale. Wording only.

**A3b-3 — the CHANGELOG reports a measurement the commit did not make.** Proposed bin: **next batch**
(doc). CHANGELOG.md:205-207 (still at HEAD:206) says "301 us/body over the first 800, 307 us/body over the
last 800, ratio 1.02"; the commit body, WORKPLAN §4 and the committed test say first/last **100**,
273→288, 1.05. Same file family: `manifest.py:202-208` `write_json` docstring still says "The sink rewrites
`MANIFEST.json` after every POST" (HEAD:213), and the `_LOCKS` comment still describes a per-entry
read-modify-write — both stale after this commit.

**A3b-4 — Collector log echo bypasses `Progress`.** Proposed bin: **thread.** `cli.py:302-308`
(HEAD:345-351) builds `collector.Binary` without `log=progress`, so `ChildLog` echoes through the default
`print` (collector.py:224): Collector lines are not flushed per line (they ride out on the next flushed
zoo line), and after a broken pipe they are printed with no `BrokenPipeError` guard — harmless in every run
above because they buffer and `_silence` redirects fd 1 before the buffer flushes, but a ≥8 KiB burst of
Collector log after the pipe breaks and before the next progress line would raise in the drain thread and
stop draining the Collector's pipe. Not reproduced; reasoning from code.

**A3b-5 — the cost test reads the real clock and its parent figure is one noisy sample.** Proposed bin:
**thread.** `test_sixteen_hundred_bodies_cost_the_same_each` (`tests/test_manifest.py:517-540`) uses
`time.perf_counter` with `BOUND = 2.0`; CONTRIBUTING's bar says a test that reads the real time fails on a
slow machine. On the commit it sat at 1.05–1.09 (safe margin); on the parent the same metric ranged
0.43–13.42 across seven runs, so "7.44" is not a stable number, though the parent's whole-run mean
(676 → 2,247 µs/body) shows the quadratic unambiguously.

**A3b-6 — the contract does not require an offset, and an undatable `started_at` fails every capture.**
Proposed bin: **thread.** EXPORT-CONTRACT.md:32 asks for `"started_at": "<ISO-8601>"`; SPEC §5.3 (and
manifest.py:567-582) treats an offset-less value as undatable → problem, exit 1, verify fails (row "naive"
above). Z4 is unaffected: streaming-concierge writes `datetime.now(timezone.utc).isoformat()`
(`concierge/__main__.py:52`), and its current MANIFEST.json carries `+00:00`. A later pet project writing
local naive time would have every capture fail.

No finding is a Z4 blocker.

## Cleanup

Worktrees removed (`git worktree remove --force` ×3, `worktree prune`); main checkout `git status --short` empty.

## Re-check (second reviewer, 2026-10-11)

Scope: two spot checks by running, plus a bin review. Worktrees `$SP/wt-a3b2-head` (040b194) and
`$SP/wt-a3b2-commit` (810f2db), `uv sync --extra dev`; no Collector, no ports used.

**(i) A3b-1 — CONFIRMED at HEAD 040b194.** Each case on a fresh `cp -a tests/fixtures/capture` copy under
`$SP/a3b2-tamper/<case>/fixture/run`, MANIFEST.json edited with a small JSON script, then `uv run zoo verify <run>`:

| MANIFEST.json edit | exit |
|---|---|
| control | 0 |
| `kind` recorded → real | **0** — and verify prints `kind=real, 2 body/bodies, 0 problem(s)` / "every recorded body still hashes to what was recorded" |
| `kind` deleted | **0** |
| `problems: []` added | **0** |
| `project_manifest.framework` edited | **0** |
| `project_manifest` → `null` (no problems entry) | **0** — the exact F4 "silently fine" shape, reachable by hand edit |
| `forwards[0].status` 200 → 500 | **0** |
| `kind` → real and `project_manifest.mode` → real (consistent lie) | **0** |
| `kind` → "bogus" | 1 (the only label edit caught) |

`project_manifest.mode` disagreeing with `kind` is not a finding: SPEC §5.3 (SPEC.md:944-948 at HEAD) says the zoo
reads no field of it besides the date and leaves a disagreement visible side by side. `--kind` is a required
CLI argument (cli.py:505), so an honest capture cannot get a wrong `kind` silently; the gap is post-hoc edits only.

**(ii) Mutation M1 — CONFIRMED caught.** In 810f2db's `_rehashed` (manifest.py:~677), inserted
`if name.endswith(HEADERS_SUFFIX): continue` before the read → `tests/test_manifest.py`: `1 failed, 29 passed`,
`FAILED tests/test_manifest.py::test_a_rewritten_content_type_in_headers_json_fails_verify`
(`assert cli.verify(tmp_path / "captures") == 1` / `AssertionError: assert 0 == 1`). Reverted (`git checkout`),
`30 passed`.

**Bin review.** Findings list is complete for what the section ran; each of A3b-1..6 carries a bin. One change:

- **A3b-1: thread → next batch (must land before A5).** WORKPLAN §3 (F7/F9/F10/F12 decision) says verify
  "checks `kind`", the A3b row claims "`kind` flipped fails verify", and A5 is gated on "at least one `real`
  capture present" — the audit takes `kind` as the truth about which capture is real. A verify that reports
  `kind=real … every recorded body still hashes` for a relabelled recorded capture (or a `project_manifest: null`
  with no problem) is the "silently fine" outcome §3 rules out, through the one channel verify cannot see. It
  needs a hand edit, so it does not make Z4's capture quietly wrong when taken: not a Z4 blocker on its own.
  Caveat for the maintainer: a seal (label fields written into a hashed file at capture time) changes the
  capture layout and cannot be added to an immutable capture afterwards, so Z4 captures taken before the fix
  stay unsealed (or get retaken). If sealed Z4 captures are wanted, promote to **blocks Z4 capture**.
  The row's wording "`kind` flipped fails verify" should say "an out-of-set `kind` fails verify".
- A3b-2 next batch, A3b-3 next batch, A3b-4 thread, A3b-5 thread, A3b-6 thread: agreed.

Net: still no finding that blocks Z4 under the default reading; A3b-1 is a run-3 pre-A5 fix.
Cleanup: both worktrees removed and pruned; no processes started; main checkout `git status --short` empty.
