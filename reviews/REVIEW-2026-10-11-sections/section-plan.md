## 3. Hygiene: the non-code commits of run 2b (`ea7fc51..3f06815`)

Base: `ea7fc51` = `plan: run-2 review decided, run 2b ordered` (parent `040b194`). It touches WORKPLAN.md only (28+/9-),
applies `patches/decisions-zoo-2026-10-11.md` (six §3 rows, §1 rows A3e/A3f/A4a/A0c, §2, the §4 note), is on origin/zoo, and CI
run 38103344694 is green.

| commit | batch | file(s) only | subject | status sha = code commit, on origin | claims |
|---|---|---|---|---|---|
| `0ed7fb3` | A3e | WORKPLAN.md ok | ok (one clause) | `done (89b8dbf, 9f23d12)`; `^` = 9f23d12; both on origin ok | macOS-only failure true; "214 s → 46 s" are **pytest** times, not `make check` (P-3); "ten of ten locally" has no evidence (P-4); mutation row corrected in the same edit ok |
| `d5436a6` | A3f | WORKPLAN.md ok | ok (one clause) | `46b2c15` = `^` ok | true by 46b2c15 and SPEC §2.3; but the `unparsed` rule is a halt point, deferred to review (P-1) |
| `5b401cc` | A4a | WORKPLAN.md ok | ok | `29c9d5c` = `^` ok | consequences match SPEC §6.2/§6.4 at 29c9d5c; N-7 still open, confirmed in cli.py:444 |
| `af667c8` | A0c (questions) | OPEN_QUESTIONS.md ok | ok | n/a | §4 well-formed: conflict (a)/(b), five options with costs, context; missing "where it now lives" (P-7) |
| `a2511f4` | A0c | WORKPLAN.md ok | ok (one clause) | `awaiting decision (af667c8, …)` = `^` ok | true |
| `b012fe5` | A0c | **WORKPLAN.md + OPEN_QUESTIONS.md** (P-5) | ok-ish (`decided`, one clause) | n/a | §3 row amended in place; §1 row **not** amended (P-2); maintainer provenance only in a builder commit (P-6) |
| `3f06815` | A0c + run 2b | WORKPLAN.md ok | ok (one clause) | `c48e093` = `^` ok | true (docs plus N-1; SPEC §4.2 omission flagged); row text still false (P-2); step 7 not run (P-8) |

- **Force-pushes:** none. GitHub activity shows twelve plain `push` events ea7fc51→89b8dbf→…→3f06815, and every `before` is the previous `after`.
- **CI before `done`:** green on every code tip before its plan commit. 9f23d12 finished 16:12:31Z and 0ed7fb3 was committed at 16:12:58Z.
  46b2c15 finished 16:25:30Z and d5436a6 at 16:25:43Z. 29c9d5c finished 16:34:39Z and 5b401cc at 16:34:51Z. c48e093 finished 17:02:59Z and 3f06815 at 17:03:12Z.
  The only red run is 89b8dbf (38153590210), and the next commit fixed it.
- **No batch was dispatched twice in the step-4 sense.** A3e is one batch with two code commits: a CI-only failure, then a fix on top.
  A0c halted, was decided, and re-ran whole, as the halt-point rule says.

### macOS duration facts (check (macos-latest, 3.12))

| sha | run | job total | `make check` step | pytest line |
|---|---|---|---|---|
| 040b194 (pre-A3e) | 38014798470 | 59 s | 46 s | — |
| ea7fc51 (pre-A3e) | 38103344694 | 57 s | 45 s | `294 passed, 3 skipped in 42.58s` |
| 89b8dbf | 38153590210 | **231 s, failure** | 218 s, failure | `4 failed, 297 passed, 4 skipped in 214.53s` |
| 9f23d12 | 38154402116 | 66 s | 51 s | `302 passed, 4 skipped in 46.29s` |
| 0ed7fb3 | 38154524754 | 68 s | 52 s | — |
| 3f06815 | 38158019828 | 73 s | 56 s | — |

On 89b8dbf the other five legs passed: collector 13 s, and ubuntu 3.11, 3.12, 3.13 and 3.14 at 18–19 s. "macOS leg only" is true.

### Findings

- **P-1 (blocks Z4 capture): A3f invented a rule and deferred it instead of halting.** d5436a6 says so: "A rule the decision did not
  spell out, set in SPEC §2.3 and open to the next review": non-`name: value` lines go to `unparsed` (absent when empty), and values
  are trimmed of SP/HTAB. CLAUDE.md "Halt points" says to stop on "a rule or a policy SPEC.md and this file do not already state". A0c
  in the same run did halt, which makes the contrast plain. It blocks Z4 because Z4's sealed captures will carry `headers.json` under
  this rule. A capture cannot be regenerated (halt point) and a seal cannot be added later (decision "the seal"). So the rule has to be
  ratified or changed before the operator captures. The second "still open" item has the same timing: the sink forwards the stdlib's
  parse, so a CR-injected header still reaches the Collector and json/. The maintainer should decide it before Z4 or say it is
  accepted.
- **P-2 (next batch, plan-only): the A0c §1 row is `done (c48e093)` but still says "the log-to-file variant writes under the run
  directory".** That is the premise OPEN_QUESTIONS §4 showed false and b012fe5 amended in §3. Step 5 says a row shown wrong is
  corrected in the same edit. Neither b012fe5 nor 3f06815 did it (`git show 3f06815:WORKPLAN.md` line 169).
- **P-3 (thread): "macOS `make check` went 214 s → 46 s"** quotes pytest's own times (214.53 s → 46.29 s). The `make check` step was
  218 s → 51 s and the job 231 s → 66 s. 214 s is the failing run (four tests each timing out at PATIENCE = 60 s). 46 s is about the
  pre-A3e baseline: pytest 42.58 s at ea7fc51, and the `make check` step 45–46 s at ea7fc51 and 040b194. The direction and size are
  right; the label is wrong.
- **P-4 (thread): "ten of ten locally"** appears only in the plan line. It is not in 89b8dbf's or 9f23d12's body, and no test loops
  (tests/test_shutdown.py has no repeat or parametrize over 10). The row's "ten of ten runs" is a hand-run claim and the record holds
  no evidence of it. This is the same pattern as the run-2 P-6 ("evidence only here").
- **P-5 (thread): b012fe5 is a `plan:` commit that also edits OPEN_QUESTIONS.md** (15+/2-). Step 5 says the plan edit is committed
  "together with nothing else". The af667c8/a2511f4 pair split the two files correctly; the decision commit did not.
- **P-6 (thread): the maintainer's provenance for option 2 exists only in a builder commit** (same Claude-Session as the builder).
  `patches/decisions-zoo-2026-10-11.md` (04:52) predates the question and does not mention it. Every earlier decision came through a
  `patches/decisions-*.md` file. Probably an in-session instruction, but nothing outside the builder's own commit records it.
  b012fe5 also rewrote a maintainer-signed §3 row in place, with an "Amended…" note, instead of appending a row.
- **P-7 (thread): OPEN_QUESTIONS §4 never got "where the decision now lives".** The file's header requires it, and §1 has
  "Implemented in A3b (810f2db)". After c48e093 the status still reads "resolved … option 2" with no sha or README/SPEC pointer.
- **P-8 (next batch): §0.1 step 7 was not run for run 2b.** patches/ ends at `0022-…` (dated 2026-10-10). There is no 0023+ for the
  twelve commits ea7fc51..3f06815. The step-8 push succeeded and CI is green.
- **P-9 (thread): 89b8dbf stays a red commit in the series** (macOS). "Amended on top" (9f23d12) is what step 8 prescribes, and §4
  records both shas and the reason. Nothing was replaced, so "the replaced sha is recorded" is met in spirit. Bisect on macOS will
  land on it.
- **P-10 (thread): A3e's §4 "readings"** say a Collector exit counts as a problem until SIGTERM, not from SIGINT. That narrows the
  decision's "a Collector exit during that shutdown is not a problem" and is stated in SPEC §4.6. It is a reading a reviewer should
  ratify, but it does not block anything.
- Verified true: A3e mutation correction (child left in the *parent's* group is the mutation; the original row named the fix itself);
  A3f fixture regenerated with bodies byte-identical (no body file in 46b2c15's diff, only heads' Host ports, headers.json,
  MANIFEST.json, collector.log); A4a's six consequences are each in SPEC §6.2/§6.4 at 29c9d5c; N-7 open (`{len(outcomes)} sent`);
  A0c's "docs only except N-1" matches c48e093's body.

## 4. CI conclusion for `3f06815`

Run 38158019828, event `push`, status `completed`, conclusion **success**.

| job | conclusion | started → completed (UTC) | duration |
|---|---|---|---|
| collector | success | 17:03:19 → 17:03:33 | 14 s |
| check (ubuntu-latest, 3.11) | success | 17:03:18 → 17:03:38 | 20 s |
| check (ubuntu-latest, 3.12) | success | 17:03:19 → 17:03:41 | 22 s |
| check (ubuntu-latest, 3.13) | success | 17:03:19 → 17:03:42 | 23 s |
| check (ubuntu-latest, 3.14) | success | 17:03:19 → 17:03:38 | 19 s |
| check (macos-latest, 3.12) | success | 17:03:27 → 17:04:40 | 73 s |
