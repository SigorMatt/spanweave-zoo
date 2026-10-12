# Section a0b — 222825f "ci: a sixth leg fetches the stock Collector and fails if its tests skip"

Reviewer: aux (cold), 2026-10-10. Port block 4440-4449 (no port of mine was bound; only the
test suite's ephemeral ports were used). Network: `gh` only, plus the offline fetch checks below
(proxied to a dead port so a download could not happen).

Worktrees (absolute, under the scratchpad, removed at the end):
- `$SP/wt-a0b-commit` at 222825f
- `$SP/wt-a0b-parent` at `git rev-parse 222825f^` = **8cb6d7d** (`plan: A0a done ...`, a plan commit)

## 1. Spec + changelog in the same commit

`git show --stat 222825f`: SPEC.md (+47: §4.1 archive cache paragraph, §4.9 "A skip is honest,
and it is not enough" with marker / guard / sixth leg), CHANGELOG.md (`## A0b — CI proves the
Collector claim`), README.md, Makefile, ci.yml, pyproject.toml (marker registration),
collector/fetch.py, tests/collector_check.py (new), tests/test_collector_ci.py (new, 16 tests),
tests/test_collector_real.py (decorator). Behaviour and spec land together. **Confirmed.**

## 2. Parent run (8cb6d7d)

| what was copied into the parent | result | failure kind |
|---|---|---|
| `tests/test_collector_ci.py` only | 1 collection error | ImportError `tests.collector_check` — **vacuous** |
| + `tests/collector_check.py` | **8 failed, 8 passed** | real: AttributeError `fetch.cached` missing (3), TypeError `main()` takes 0 args (1), `--print-pin` unknown (1), ci.yml has no `collector` job (1), Makefile has no `collector-check` (1), marker selects nothing / pytest exit 5 (1) |
| + `tests/test_collector_real.py` | 8 failed, 8 passed | same 8; `test_the_marker_selects_exactly_those_tests` now fails on the parent's unregistered-marker warning line (`tests/test_collector_real.py:64: PytestUnknownMarkWarning`), i.e. on the missing `pyproject.toml` registration |

The 8 that pass on the parent are the 6 guard-`verdict()` tests (+1 parametrized) and
`test_every_test_that_needs_the_collector_carries_the_marker` — they test the new helper itself
(they need it copied in to run at all) or, for the AST test, pass because the parent's skipif
variable was already called `needs_collector`. Those are covered by mutation M1/M3 below instead.
Matches the commit body ("Eight of the sixteen new tests are red on 8cb6d7d ... all sixteen error
there without `tests/collector_check.py`"). **Confirmed.**

## 3. Mutations (commit worktree, each reverted)

- **M3 (the commit's own)** `tests/test_collector_real.py`:
  `-    return pytest.mark.needs_collector(skip(test))` / `+    return skip(test)`
  - guard: `collected 264 items / 264 deselected / 0 selected` →
    `collector-check: FAILED (pytest exit 5).` `! no test carries the `needs_collector` marker, so this ran nothing at all` — exit 1.
  - `FAILED tests/test_collector_ci.py::test_the_marker_selects_exactly_those_tests` (`assert 5 == 0`, `no tests collected (264 deselected)`); 1 failed, 15 passed.
  - Not caught by `test_every_test_that_needs_the_collector_carries_the_marker` (it checks the
    decorator's *name* in the AST, which is unchanged). The body claims the guard and the marker
    test catch it — **true**.
- **M1** `tests/collector_check.py`: `NOT_PASSED = ("skipped", "failure", "error")` → `("failure", "error")`
  → FAILED `test_the_guard_fails_when_a_marked_test_skipped` (`assert [] == ['skipped: te...back_as_json']`),
  `test_the_guard_fails_when_every_marked_test_skipped` (`assert [] == ['skipped', 'skipped']`),
  `test_the_guard_reports_every_outcome_it_read`; 3 failed, 13 passed.
- **M2** `collector/fetch.py` `cached()`: insert `return True` after the `is_file()` check (trust the
  file name, skip the re-hash) → FAILED `test_a_cached_archive_whose_digest_is_not_the_pin_is_refused`
  (`Failed: DID NOT RAISE SystemExit`); 1 failed, 15 passed.

## 4. Clock / randomness / network in `spanweave_zoo/`

The diff touches nothing under `spanweave_zoo/`. `subprocess`/`tempfile` are in
`tests/collector_check.py` (test tooling); `urllib` stays in `collector/fetch.py`, outside the
package (pre-existing, and the only network code). **Clean.**

## 5. One concern, message form

`ci: <one line>`; body names A0b, SPEC §4.1 and §4.9. The archive cache in `fetch.py` is part of
the row's own wording ("`make collector` with the release archive cached by its sha256"), so one
concern. **Confirmed.**

## 6. `make check` (commit worktree)

- without the binary: ruff `All checks passed!`, mypy `Success: no issues found in 7 source files`,
  pytest **261 passed, 3 skipped**, gates 31 passed, `zoo verify` (none under captures/, and the
  fixture capture re-hashes), `zoo 0.0.1` — exit 0.
- with `collector/otelcol-contrib` copied in: **264 passed**, gates 31 passed — exit 0.
- `make install-check`: `install-check: OK -- what ships works`.

## 7. Specific claims

### (a) CI logs: the @needs_collector tests ran, not skipped; durations

`gh run list --branch zoo` / `gh run view <id> --json jobs`. Job durations from startedAt/completedAt:

| run | head | collector job | duration | cache | check legs |
|---|---|---|---|---|---|
| 38013503089 | 7dc4cb6, branch **claude/a0b-trial** | 114098604314 | 01:31:29→01:31:44 = **15 s** | `Cache not found` (cold) | ubuntu 17–18 s, macOS 58 s |
| 38013640820 | **222825f** (zoo) | 114099036557 | 01:33:38→01:33:56 = **18 s** | `Cache not found` (cold), `Cache saved with key: otelcol-otelcol-contrib_0.162.0_linux_amd64.tar.gz-fcc0637...fcc3` | ubuntu 15–18 s, macOS 65 s |
| 38013819446 | 5006d7d (plan) | 114099594386 | 01:36:23→01:36:39 = 16 s | `Cache restored from key: otelcol-...fcc3` | |
| 38014662495 | **0c1e538** | 114102167785 | 01:49:36→01:49:51 = **15 s** | `Cache restored from key: otelcol-...fcc3`, `cached .../collector/.cache/otelcol-contrib_0.162.0_linux_amd64.tar.gz` | |
| 38014798470 | **040b194** (tip) | 114102581362 | 01:51:43→01:51:56 = **13 s** | `Cache restored from key: otelcol-...fcc3`, `cached ...` | |

Quoted from 222825f's job log (`gh run view 38013640820 --log --job 114099036557`):
```
01:33:44.5101191Z Cache not found for input keys: otelcol-otelcol-contrib_0.162.0_linux_amd64.tar.gz-fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3
01:33:48.6984493Z   fetching https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.162.0/otelcol-contrib_0.162.0_linux_amd64.tar.gz
01:33:48.6985450Z   sha256 fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3 matches collector/SHA256SUMS
01:33:49.5085644Z collecting ... collected 264 items / 261 deselected / 3 selected
01:33:49.5967274Z tests/test_collector_real.py::test_the_binary_on_disk_is_the_pinned_version PASSED [ 33%]
01:33:50.2162692Z tests/test_collector_real.py::test_a_protobuf_export_through_the_tee_comes_back_as_json_with_the_same_ids PASSED [ 66%]
01:33:50.2357944Z tests/test_collector_real.py::test_the_collector_refuses_rather_than_hangs_when_it_cannot_listen PASSED [100%]
01:33:50.2359455Z ====================== 3 passed, 261 deselected in 1.03s =======================
01:33:50.2687797Z collector-check: OK -- 3 tests ran against the real Collector, none skipped
```
0c1e538 (38014662495) and 040b194 (38014798470): the same three `PASSED` lines,
`3 passed, 294 deselected in 1.12s` / `in 1.09s`, and
`collector-check: OK -- 3 tests ran against the real Collector, none skipped`, preceded by
`Cache restored from key: otelcol-otelcol-contrib_0.162.0_linux_amd64.tar.gz-fcc0637...fcc3` and
`  cached /home/runner/work/spanweave-zoo/spanweave-zoo/collector/.cache/otelcol-contrib_0.162.0_linux_amd64.tar.gz`.
The digest in the key equals `collector/SHA256SUMS:14`.

Comparison with WORKPLAN §4: "18 s" (zoo's run) = 38013640820, **confirmed**; "15 s" (trial run
38013503089) **confirmed**, and the run exists on branch `claude/a0b-trial`, head 7dc4cb6.
`git diff 7dc4cb6 222825f` = CHANGELOG.md only (`Wall clock: DURATION_PLACEHOLDER.` → the 15 s
sentence); every code/CI file is identical, so "identical content" holds for what ran.
Sub-claims: "4 s the 112MB fetch" — cold `make collector` step 01:33:44.53→01:33:48.70 = 4.2 s
(trial 3.5 s), confirmed; "1.6 s the three tests" — guard step 48.72→50.27 = 1.5 s wall, pytest's
own 1.03 s, fair.

Observation (not a finding): the cache saves almost no time. On the tip (warm), the
`actions/cache` restore ran 01:51:48.76→~01:51:50.28 (1.5 s, "Received 110976190 ... 104.1 MBs/sec")
and `make collector` still took 01:51:50.29→01:51:52.94 = 2.65 s (re-hash + extract) — ~4.2 s,
the same as the cold download. What the cache buys is not depending on github.com releases on
every push, not speed. §4's "the first run on any branch pays a cold 4 s fetch" is true but
implies a saving that is not there.

Job name: the GitHub check run is named **`collector`**, not `collector (ubuntu-latest)` (see the
job table above; there is no matrix on this job, so no suffix). See A0b-1.

### (b) The guard reads junit-xml, not the exit code — run for real

All in `$SP/wt-a0b-commit`, `uv run python -m tests.collector_check` (or `make collector-check`):

| case | how produced | pytest | guard |
|---|---|---|---|
| (i) every test skips | binary absent | `3 skipped, 261 deselected` **exit 0** | `collector-check: FAILED (pytest exit 0).` three `! skipped: ...` lines; make exit 2 |
| (ii) nothing selected | M3 (marker dropped, skipif kept) | `264 deselected`, exit 5 | `FAILED (pytest exit 5)`, `! no test carries the `needs_collector` marker, so this ran nothing at all`, exit 1 |
| (iii) one of three skips | `@pytest.mark.skip(reason="planted: one of three skips")` inserted at tests/test_collector_real.py:264 | `2 passed, 1 skipped, 261 deselected` **exit 0** | `FAILED (pytest exit 0).` `! skipped: tests.test_collector_real::test_the_collector_refuses_rather_than_hangs_when_it_cannot_listen`, exit 1 |
| (iv) all ran | binary copied in | `3 passed, 261 deselected in 0.97s` | `collector-check: OK -- 3 tests ran against the real Collector, none skipped`, exit 0 |

Cases (i) and (iii) are the proof that the exit code would have been the wrong question: pytest
exits 0 and the guard fails. **Confirmed.**

### (c) The archive cache is keyed by sha256; a wrong-digest cached archive is refused

`fetch.py --print-pin` → `asset=otelcol-contrib_0.162.0_linux_amd64.tar.gz`,
`sha256=fcc0637...fcc3` (= SHA256SUMS:14; ci.yml key `otelcol-${asset}-${sha256}`).
Copied the main checkout's `collector/.cache/otelcol-contrib_0.162.0_linux_amd64.tar.gz` into the
worktree; `https_proxy`/`HTTPS_PROXY`/`http_proxy` set to `http://127.0.0.1:9` so any download is
refused (`unshare -rn` is not permitted on this host):
- control, cache removed: `collector: cannot fetch https://github.com/... <urlopen error [Errno 111] Connection refused>`, exit 1 — the run really is offline; no `.part` left behind.
- good cache: `  cached .../collector/.cache/otelcol-contrib_0.162.0_linux_amd64.tar.gz`, `  sha256 fcc0637... matches collector/SHA256SUMS`, `ready`, exit 0; extracted binary sha256 `2425bdf5...a064` = the main checkout's.
- last byte flipped (archive now `7f917500...fd67`), binary removed first:
  ```
  collector: REFUSING to unpack otelcol-contrib_0.162.0_linux_amd64.tar.gz.
    expected sha256 fcc063749f730f8c21fe29f2d340ff174f5f1c5885bd3156fb6c985a3036fcc3  (collector/SHA256SUMS)
    cached          7f917500c8cff2a87986df99b05b561632790603274da4d9c3f436520e8afd67
  ...
  Delete .../collector/.cache/otelcol-contrib_0.162.0_linux_amd64.tar.gz and run `make collector` again to fetch them.
  ```
  exit 1; nothing extracted (`collector/` has no `otelcol-contrib`); the cached file is left in place.
- truncated to 1000 bytes: same `REFUSING`, exit 1.

**Confirmed.**

### (d) ci.yml: check legs, independence, cache key, permissions, pins

- The five `check` legs run `make check` (→ `uv run pytest`) with no binary: tip run 38014798470,
  `check (ubuntu-latest, 3.12)`: `294 passed, 3 skipped in 5.64s`; `check (macos-latest, 3.12)`:
  `294 passed, 3 skipped in 42.65s`. The skip is visible as a **count** only: `make test` has no
  `-rs`, so the reason line ("collector/otelcol-contrib is absent ...") never appears on those legs
  (A0b-2). Unchanged by this commit apart from wording.
- `collector:` has no `needs:` and no job `needs:` it — it gates nothing else and nothing gates
  it; it can only add a red tick. It does not run `make check`, so it is not a seventh copy of the
  suite. `make collector-check` is not a prerequisite of `check` (Makefile `check: lint types test gates verify`, asserted by `test_make_has_the_target_ci_runs`).
- Cache: `path: collector/.cache`, `key: otelcol-<asset>-<sha256>` from `--print-pin`, no
  `restore-keys` (exact match only, so a VERSION/SHA256SUMS bump is a miss). Saved only on a miss
  after a green job (actions/cache default), and fetch.py only ever renames a digest-verified
  `.part` into the cache, so a poisoned entry is not a realistic state; if one did occur, the
  refusal's remedy ("Delete ... and run `make collector` again") is not available on a runner — the
  entry would need `gh cache delete`. Thread-level at most; not filed.
- Permissions: no `permissions:` block in the workflow (unchanged); the repository default is
  `{"default_workflow_permissions":"read"}` (`gh api .../actions/permissions/workflow`), so the
  token is read-only. Fine.
- Pins: `actions/checkout@v6`, `astral-sh/setup-uv@v8.1.0` (uv `0.11.25`), `actions/cache@v4` —
  tags, not SHAs, the same convention as the existing `check` job. Consistent; not filed.

**Confirmed**, with A0b-1 / A0b-2 as small notes.

### (e) The trial branch and its caches are deleted

- `git ls-remote origin`: `HEAD`, `refs/heads/main` (d33059e), `refs/heads/zoo` (040b194) — no
  `claude/a0b-trial`. `gh api repos/{owner}/{repo}/branches` → `main`, `zoo`.
- `gh cache list`: 7 entries, refs only `refs/heads/zoo` and `refs/heads/main`; the one otelcol
  entry is `refs/heads/zoo`, created 01:33:52Z (by 222825f's run). No cache on the trial ref.
- Run 38013503089 is still listed under `claude/a0b-trial` (runs are not deleted with a branch —
  expected). The local clone still holds commit 7dc4cb6 as an unreachable object (no local branch
  names it); harmless.

**Confirmed.**

## Findings

- **A0b-1 — the job is named `collector`, the docs call it `collector (ubuntu-latest)`.** SPEC.md:825,
  CHANGELOG.md:14, WORKPLAN §1 row and §4, and the commit subject/body all name the sixth leg
  `collector (ubuntu-latest)`. The workflow defines `collector:` with `runs-on: ubuntu-latest` and no
  `name:` or matrix (ci.yml, the `collector` job), so GitHub's check run is `collector`
  (`gh run view 38014798470 --json jobs`). Harmless today, but anyone adding a required status check
  by the documented name would wait forever. One-line fix: `name: collector (ubuntu-latest)` on the
  job, or correct the docs. Bin: **next batch** (trivial).
- **A0b-2 — "skips loudly" on the `check` legs is a count, not a reason.** SPEC.md:808 and
  tests/test_collector_real.py's docstring say the tests "skip loudly"; on the five legs the only
  trace is `294 passed, 3 skipped` because `make test` is a bare `uv run pytest` (Makefile:17-18)
  with no `-rs`. The sixth leg now makes the skip harmless, so this is wording, not a defect.
  Bin: **thread**.
- (not filed) The archive cache costs about what it saves (warm restore 1.5 s + re-hash/extract
  2.65 s ≈ cold 4.2 s download); its value is independence from github.com releases. §4's "pays a
  cold 4 s fetch" is accurate but suggests a speed-up that the logs do not show.

Nothing here blocks the Z4 capture.

## Cleanup

`git worktree remove --force` both worktrees, `git worktree prune`; main checkout
`git status --short` empty (see final reply).
