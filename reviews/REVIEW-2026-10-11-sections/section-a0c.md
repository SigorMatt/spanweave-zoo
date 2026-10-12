## A0c — `c48e093` (docs: the README's operator flow says what a rehearsed run actually does)

Derived parent: `git rev-parse c48e093^` = `b012fe5` (`plan: A0c decided ...`).
Worktrees (absolute, scratchpad): `a0c/head` @ c48e093, `a0c/parent` @ b012fe5, `a0c/mut` @ c48e093. All removed at the end.

Touched: CHANGELOG.md (+26), Makefile (comment), README.md, SPEC.md (§2 tree +3), `spanweave_zoo/cli.py` (verify closing line), `tests/test_manifest.py` (+43).

### Gates

| check | result |
|---|---|
| SPEC in same commit | yes for the tree (§2: `json/0001.headers.raw`, `.headers.json`, `collector.log`). SPEC states no wording for verify's failing closing line (grep `problem(s)`, `bytes that were recorded` in SPEC.c48: only §5.6 prose at SPEC.md:1260), so N-1 needs no spec text. §4.2 not touched (see b). |
| CHANGELOG in same commit | yes, `## A0c`, says "Docs only, except the `zoo verify` closing-line wording (review N-1)". |
| new test on derived parent (test file copied over) | **real**: `4 failed` — every param (`_record_a_problem`, `_declare_an_unnamed_kind`, `_drop_ended_at`, `_break_the_seal`) fails at `assert "bytes that were recorded" not in out` (tests/test_manifest.py:451). |
| mutation: restore the old line (`git show c48e093^:spanweave_zoo/cli.py > spanweave_zoo/cli.py`) | **caught**, 4 failed. A second mutant (neutral line minus `-- not verified.`) is caught too, 4 failed, by the `out.splitlines()[-1]` assertion. |
| `make check` in `a0c/head` | rc 0: ruff/mypy clean, `332 passed, 4 skipped` (the 4 are the real-Collector tests; no binary in the worktree), gates `31 passed`, `zoo verify` green on the fixture. |
| one concern | see (a). |

### (a) Did the cli.py string (N-1) belong in A0c?

The A0c row (WORKPLAN.md:169) says "Docs only; say so in the body." The §4 note of 2026-10-11 (WORKPLAN.md:521-529), which re-dispatched A0c after the decision, lists "N-1's verify wording" among the side findings A0c "re-runs in full" with. The prior review §5.1 (REVIEW-2026-10-10-run2.md:392-393) asked for N-1 to be folded into the operator-flow work "because the operator meets both in the same flow".

Verdict: **it belonged by dispatch, and the concern is coherent** (what the operator reads while running the flow), but the row was never amended. §0.1 step 5 says a wrong criterion "has an owner, and it is this step": the plan edit that added N-1 to A0c's scope (b012fe5) should have changed "Docs only" to "Docs only, except N-1's verify closing line". The commit body is honest about the exception ("Docs only, except ..."), and the change is the right shape for a code change (red-first test, mutation caught, no spec text owed). Not a split-the-commit finding; a plan-hygiene one.

Same row, same staleness: WORKPLAN.md:169 still reads "the log-to-file variant writes **under the run directory**", the premise OPEN_QUESTIONS.md §4 showed false and the decision amended in §3 (WORKPLAN.md:200) but not in §1. Bin both: **next batch** (a `plan:` edit).

### (b) SPEC §4.2's list of terminal lines

SPEC.md @ c48e093, §4.2, lines 550-552:

> 550 (§5.6). Nothing of it is echoed: the operator's terminal shows the zoo's own
> 551 lines — the readiness line, one line per recorded body, the summary — and no
> 552 Collector line.

What `zoo capture` actually prints, in order:

| line | code |
|---|---|
| `zoo capture: the raw bytes are the record. Ctrl-C to stop.` | `spanweave_zoo/capture.py:326` (`READY_LINE`, :74) |
| `zoo capture: recording POST /v1/traces on http://127.0.0.1:4318 -> captures/.../raw/` | `spanweave_zoo/capture.py:327-330` |
| `zoo capture: collector 0.162.0 re-encoding to JSON into .../json/, via http://127.0.0.1:4319` | `spanweave_zoo/capture.py:331-334` |
| `  raw/0001.body  6884 bytes  sha256:<12>` (per body, per side) | `spanweave_zoo/capture.py:481` |
| `  ! ... NOT forwarded` / `forwarded, collector said N` | `spanweave_zoo/capture.py:487`, `:489` |
| `\nzoo capture: stopping` | `spanweave_zoo/cli.py:390` |
| summary `zoo capture: N body/bodies in raw/, M in json/, under ..., MANIFEST.json written: kind=...` | `spanweave_zoo/capture.py:468-469` |

So §4.2's enumeration **omits the two port lines and `zoo capture: stopping`** (and the `!` forward lines). Mitigation: §4.6 says of the port lines "The lines after it name the ports and the directories of the run that is now up" (SPEC.md:732-733), so §4.2 is incomplete rather than contradicted. `stopping` appears **nowhere** in SPEC.md or README.md (`grep -n stopping SPEC.md README.md`: no output).

The builder flagged this itself: WORKPLAN.md §4, A0c (c48e093) line: "For the scoped review: SPEC §4.2's list of terminal lines omits the two lines after readiness and `zoo capture: stopping`." Confirmed as stated. Bin: **next batch** (SPEC wording; it changes no byte of a capture and no operator action).

### (c) Does anything check that the redirect and the grep name the same file?

No. `tests/test_readme.py` checks the readiness line text and the anchored pattern (`test_the_readme_waits_on_the_line_the_code_actually_prints`, :206-227), parses each `zoo` command up to the first shell operator (`argv_of`, :87-94 — so the redirect target is discarded before anything looks at it), and lists `timeout` in `KNOWN_PROGRAMS` (:57) without checking it. Mutations in `a0c/mut`, README.md only, each then `uv run pytest -q tests/test_readme.py`:

| mutant | result |
|---|---|
| grep's file → `zoo-capture-WRONG.log` (line 235 only) | `92 passed` |
| redirect and grep both → `zoo-capture-1999-01-01T00-00-00Z.log` (≠ `--run-id 2026-10-10T09-00-00Z`) | `92 passed` |
| `timeout 30` → `timeout 0`, `sleep 0.1` → `true` | `92 passed` |
| step 6 verify path's run-id → `...09-00-01Z` (≠ step 3's `--run-id`) | `92 passed` |

So redirect-vs-grep agreement, redirect-run-id vs `--run-id` agreement and the step-3/step-6 run-id agreement are all unchecked; **N-9 is still true**, and the comment at test_readme.py:51-56 ("each of these is checked below") still overstates for `timeout`. As printed today all four agree (read by eye: README.md:211, 231, 234, 235, 267, 294 all say `2026-10-10T09-00-00Z`). Bin: **next batch** (N-9, unchanged; as printed the README is correct, so it does not block).

### (d) The seven differences of §1.5, against the lead's rehearsal at 3f06815

| # | §1.5 difference | README @ c48e093 | true? |
|---|---|---|---|
| 1 | Ctrl-C → exit 1, `collector exited: 0` | step 5 (README.md:268-271): Collector in its own session, "a clean run exits **0** and leaves no Collector running" | yes (lead: exit 0, no Collector left) |
| 2 | gates red after a run | step 6 (README.md:288-290): green with the new capture present, and `make check` too | yes (lead: make verify/check green, 336 + 31) |
| 3 | "prints one line", Collector lines in terminal | README.md:82-92: readiness line "followed by two more", none of the Collector's lines reach the terminal, they go to `collector.log` | yes |
| 4 | per-side count, `2 body/bodies` | README.md:218-220 "one for ... `raw/` and one for ... `json/`, so a single export prints two"; summary README.md:266-268 | yes |
| 5 | step 2 digest wording, cache | README.md:202-206: checked against `collector/SHA256SUMS`, cache in `collector/.cache/` re-hashed (matches `collector/fetch.py:13-24`) | yes |
| 6 | supervisor log in the checkout | README.md:234-235 `"${TMPDIR:-/tmp}"/zoo-capture-<run-id>.log`, README.md:240-244 | yes |
| 7 | pet's `MANIFEST.json` modified | README.md:276-279 | yes (documented, as decided) |

Character for character: the readiness line in README (225-226, 82-83, flattened) equals `capture.READY_LINE` and is test-held. The summary README quotes — `zoo capture: 1 body/bodies in raw/, 1 in json/, under captures/z4/2026-10-10T09-00-00Z/, MANIFEST.json written: kind=real` — matches the lead's `zoo capture: 1 body/bodies in raw/, 1 in json/, under captures/z4/<id>/, MANIFEST.json written: kind=recorded` in every character except the run-id and the `kind` value, which are the example's own (format from `capture.py:468-469`). README does not quote the two port lines, the per-body lines or `stopping`, so there is nothing else to mismatch. Not test-held: the summary string (a drift of `manifest.tally` would leave README stale with everything green). Thread.

Consistency of step 3: "the one readiness line" is still true (there is one readiness line; the two after it are not readiness lines and the anchored grep is not satisfied by them). But step 3 itself (README.md:216-228) says only "It prints one line per recorded body" and "Wait for the one readiness line"; the two port lines are mentioned only in the tee section (README.md:82-86), and `^C` / `zoo capture: stopping` before the summary are mentioned nowhere. An operator reading step 3/5 alone sees three lines where the step promises one, and an unannounced `stopping`. Not wrong, incomplete. Bin: **thread** (or fold into the §4.2 SPEC fix, next batch).

Stale rationale (pre-existing, kept by this commit): README.md:238-240 "anchor it: `recording POST /v1/traces on http://127.0.0.1:4318` is printed by `zoo sink` as well, so an unanchored match can be satisfied by the wrong process." The grep's pattern is the readiness line, which `zoo sink` never prints (`SINK_BANNER` is `zoo sink: it parses nothing. Ctrl-C to stop.`, cli.py:94); and `recording POST ... 4318` is now printed by `zoo capture` too (capture.py:328). The sentence justifies the anchor with a line the pattern does not contain. Harmless to the flow. Bin: **thread**.

### (e) Layout / SPEC §2 tree

Both list `bodies.jsonl` and `forwards.jsonl` — README Layout (README.md:390-391 @ c48e093) and SPEC §2 tree (SPEC.md:112-113) — and now `collector.log` and `json/NNNN.headers.{raw,json}`. Against the lead's capture (bodies.jsonl, collector.log, forwards.jsonl, json/0001.headers.json, json/0001.headers.raw, json/0001.json, MANIFEST.json, raw/0001.body, raw/0001.headers.json, raw/0001.headers.raw): every file is in both trees. Layout additionally lists `rejected/NNNN.body` (absent from a clean run, correct). **No finding.**

### (f) Step 3 `--project-manifest ../streaming-concierge/MANIFEST.json --kind real`, step 4 `make run-real`

- Parses (`test_every_zoo_command_the_readme_prints_parses_as_printed`); `run-real` is in EXPORT-CONTRACT.md:21 and `~/git/streaming-concierge/Makefile:34`; `ENDPOINT=` is honoured (`Makefile:1,8`).
- `../streaming-concierge` assumes the pet checkout is a **sibling** of the zoo checkout (true for the lead's `~/git/` layout); the README never says so. Thread.
- `make run-real` requires `OPENAI_API_KEY` in the **second** terminal (`streaming-concierge/Makefile:25`, exits 2 "OPENAI_API_KEY is not set") and the README's step 4 does not say so. Failure mode: the pet exits 2 before exporting or writing its manifest; Ctrl-C then finalizes a capture with 0 bodies, a pre-capture `MANIFEST.json` → `problems`, non-zero exit, verify fails, and the run-id is spent (README.md:310-313). Loud and recoverable, so not blocking, but it is exactly the Z4 `real` capture the operator does next. Bin: **next batch** (one README sentence); operator note for Z4: export the key in terminal 2 first.

### Findings, binned

| id | finding | bin |
|---|---|---|
| A0c-1 | Row WORKPLAN.md:169 says "Docs only" and "under the run directory"; neither was amended when the §4 note added N-1 and §3 was amended to option 2 | next batch (`plan:` edit) |
| A0c-2 | SPEC §4.2:550-552 omits the two port lines, `zoo capture: stopping` and the `!` forward lines; `stopping` is in neither SPEC nor README (builder-flagged) | next batch |
| A0c-3 | Nothing checks redirect file = grep file, redirect run-id = `--run-id`, step 6 run-id, or `timeout`; four README-only mutants all `92 passed` (N-9 still open) | next batch |
| A0c-4 | `make run-real` needs `OPENAI_API_KEY`; README step 4 silent | next batch (operator: set it before Z4 real) |
| A0c-5 | Step 3/5 don't mention the two port lines or `stopping`; summary string not test-held | thread |
| A0c-6 | README.md:238-240 anchor rationale names a line the pattern does not contain | thread |
| A0c-7 | `../streaming-concierge` sibling-checkout assumption unstated | thread |

Nothing here **blocks the Z4 capture**: the README as printed is correct for the flow the lead rehearsed.
