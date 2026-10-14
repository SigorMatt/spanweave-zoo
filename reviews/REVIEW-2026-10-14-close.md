# REVIEW 2026-10-14 — series-2 close, `fe9c08f` (parent `1ed70a1`)

Reviewer: aux, cold, read-only (`git show 1ed70a1:WORKPLAN.md` §0.2). Scope: `fe9c08f` only, against
the B8 row (`WORKPLAN.md`@1ed70a1:178), §3, §4, and CLAUDE.md / CONTRIBUTING.md as of `fe9c08f`.
I edited no tracked file and made no commit. One side effect to declare: `git fetch -q` in the six
pet-project checkouts, which updated only their remote-tracking refs, so that "pushed" could be checked.

**Result: 0 blockers, 0 should-fix, 6 notes.** All seven checks pass.

## Checks (evidence)

1. **Reports: one method.** All 12 `audit/*.md` changed in `fe9c08f`. All 12 have byte-identical
   `## Method` sections (one md5 across 12), the same pins (spanweave `fec7da2…`, spanweave-live `cddc694…`,
   agentgolden `aa1847f…`, pinned = installed, 12/12), and exactly one node-table header
   `| Node | Body | Record | Span name | … | Span events |`. No old-layout header (`| Node | Kind |…`) or
   `--timing` policy run is left. `git diff --stat 4b57f18 fe9c08f -- spanweave_zoo pyproject.toml uv.lock` is empty.
   I re-ran `zoo audit` on `captures/z4/2026-10-12-real` (3 findings) and `captures/z6/2026-10-14-recorded` (1)
   into the scratchpad. `diff` against the committed reports differs only on `"code": "listening"`
   and `"code": "completed"`/`"late_arrival"` lines (ports and clock values).
   Extra: with ports and numbers normalised, Z1/Z3/Z4/Z5's `serve` event lines are identical between the
   `1ed70a1` and `fe9c08f` reports (0 differing lines, 8/8 reports). Z2/Z6 diffs touch only
   listening, completed and late_arrival lines. That confirms the CHANGELOG claim.
2. **PROBES.md.** Grouped by owner: `## spanweave-live` (L1–L4), `## spanweave` (S1–S22), `## agentgolden` (0).
   The stated count of 4/22/0 matches the headings. Findings: Z4 3×2 + 1×10 = 16, as stated. The L1 total of 29 bodies
   matches the captures table. A script over the 26 probes shows every one has **Captures**, **Command**, **Observed**
   and **Expected** or **To establish**. The old file (`1ed70a1:PROBES.md`) had the same 26 IDs, none lost.
   Spot checks of moved content: S15 keeps Z1's depth-8 path, and S7 keeps its key lists. No "Seen again" or
   "(B7r)" markers are left. Every `audit/…md` cited exists (all 12), and every `captures/…` cited exists.
   Spot-checked against `audit/z3-2026-10-13-real.md`: S6 (agent 2, chain 26, llm 50 = 25 `generation` + 25
   `ChatCompletion`, tool 24, 102 nodes), S8 (the 18 records it lists, exact) and S10 (9 `generation`
   with model absent). L2's node-table records also match `audit/z4-2026-10-12-real.md:288-291`.
3. **ROADMAP.md.** `git -C ~/git/<p> rev-parse --short HEAD` gives ledger-clerk `4c150cc`,
   fan-out-researcher `5883f9b`, echo-planner `71bc477`, streaming-concierge `553279a`,
   flaky-fetcher `2a3e778`, crew-of-three `78adcaf`. All six equal the rows. Each checkout is clean, on
   `origin/main`, and its HEAD commit is older than its capture's `started_at`. `contract_version` in the
   captures' `project_manifest` is Z1/Z2/Z6 1.3 and Z3/Z5 1.2. Z4 has none, which the row says. The captures
   commits `c24ab69 45305a8 9b0268f 47cb06c f081997 88dbcfd` all exist with the subjects
   `captures: zN real and recorded, <date>`. Checklist step 3 has the never-run-manifest sentence. The
   operating notes have Z6's two (the script departure, and no manifest before the first run).
4. **TASKS.md.** All 24 registry shas (B0…B7-Z6) exist and are ancestors of `fe9c08f`. Their subjects
   match the batches, and every sha equals the `done (…)` in WORKPLAN §1. The B8 entry is "this commit".
   §3 and §4 were checked mechanically: extracted from `1ed70a1:WORKPLAN.md` and from TASKS' series-2
   sections and diffed. The only differences are one added provenance line per section ("…as it stood at
   `1ed70a1`") and a trailing blank line, so the text is verbatim. Every thread the B8 row names is present:
   bare-CR close (TASKS "Threads for series 3"), Qodo's wire-level proxy declined (TASKS "Dispositions"),
   the `PID set at arming:` wording, and the contract 1.4 candidates (×3). There are dispositions for Qodo's
   12, Qodo's summary, and series 1's close-review threads. The decline's quotations match
   `reviews/QODO-SUMMARY-2026-10-12.md:66-75`.
5. **reviews/.** `sha256sum -c SHA256SUMS` gives 27 OK and 0 failed. `find reviews -type f ! -name SHA256SUMS`
   matches the listed set exactly (27) and matches `git ls-files reviews`. The
   `gh api …/issues/comments/6127869987 --jq .body` output with its last byte (`\n`) stripped is byte-equal
   to `QODO-SUMMARY-2026-10-12.md` (`cmp` silent; the file ends `>` without a newline). The author is
   `qodo-code-review[bot]`, 2026-10-12T15:59:29Z.
6. **WORKPLAN mentions** (`git grep -n WORKPLAN fe9c08f`). CLAUDE.md:8-17 is conditional and true, and
   names both git locations. CLAUDE.md:38 says "deleted at the close; `TASKS.md` says where", which is true.
   CONTRIBUTING.md:4,12 are conditional ("while a series is open"). OPEN_QUESTIONS.md:20-25 has a redirect
   note covering §1–§5 → series 1 and §6–§8 → series 2, and the series-2 citations (:312, :395) say "series 2".
   The TASKS.md mentions are historical or verbatim folds. CHANGELOG and reviews/ mentions are history.
   README, tests and SPEC have none. `tests/test_manifest.py:706` now cites `TASKS.md`, B2b, which resolves
   to the folded 2026-10-13 B2b decision.
7. **Hygiene.** `git diff --stat 1ed70a1 fe9c08f -- captures/` is empty. `make verify` is green (12 captures
   and the fixture). Subject `close: series 2 — …`, not `plan:`. `make check` is green: ruff "All checks
   passed", format "32 files already formatted", mypy "no issues in 9 source files", pytest
   497 passed and gates 40 passed. CI run 38495060273 on `fe9c08f` succeeded. `origin/zoo` = `fe9c08f`, and
   no commit follows it.

## Findings

### N-1 (note): the ROADMAP "Audited" cell departs from the row's wording
- **Evidence:** the B8 row asks for `series 2 (<B8 sha>)`. The ROADMAP rows say
  `series 2 (B8; audit code 4b57f18)`. The commit body gives the reason: a commit cannot name its own sha.
- **Assessment:** the reason is sound. The audit's sha is the more useful pin, and B8 names the
  commit through TASKS' registry ("this commit").
- **Suggested fix:** none needed. Optionally, after the merge, a later docs commit can name `fe9c08f`.

### N-2 (note): the ROADMAP Z4 row's probe list omits S15
- **Evidence:** PROBES.md S15 lists **Captures:** "all twelve", and its Observed says "Z4's graphs have
  no `parent` edge (S2)". Every other row that S15 covers lists it (Z1, Z2, Z3, Z5, Z6). The Z4 row lists
  `L1, L2, S1–S5`.
- **Suggested fix:** either add S15 to the Z4 row, or narrow S15's Captures to the ten with `parent`
  edges and keep the Z4 sentence as context.

### N-3 (note): "on no other" in S8 is ambiguous, and S8 omits the inputs
- **Evidence:** PROBES.md S8 says "On the same nine `ChatCompletion` nodes, and on no other, the outputs
  are *absent*". In `audit/z3-2026-10-13-real.md` outputs are also absent on 25 `turn`, 2 `Agent workflow`
  and 1 `echo-planner` node, so "no other" holds only among `llm` nodes. The same nine `ChatCompletion`
  nodes also have inputs absent, and 8 of the nine `generation` nodes have inputs absent (all other
  `generation` and `ChatCompletion` nodes are present/present). S8 does not say either.
- **Suggested fix:** change to "on no other `llm` node". Add the inputs observation, which may bear on
  S8's dropped-attribute *to establish*.

### N-4 (note): the wire-level-proxy decline is under Dispositions, not under Threads
- **Evidence:** the B8 row (3) names "Qodo's wire-level proxy declined" among the "threads for series 3".
  TASKS records it under "Dispositions of the reviews", with its reason and a re-open condition ("a thread
  only if a pet project ever exports something the sink cannot frame"). "Threads for series 3" does not
  mention it.
- **Suggested fix:** optionally add a one-line pointer in "Threads for series 3" to the disposition.
  The content is complete as it stands.

### N-5 (note, outside this commit's scope): the reports' Method step 4 does not name the Body and Record columns
- **Evidence:** all 12 reports' Method item 4 ("one row per node -- span name, kind, status, …") lists
  neither Body nor Record, while the table has both and SPEC.md:2161 lists them. The source string is
  `spanweave_zoo/audit.py:1075-1080`, unchanged since B6c (`4b57f18`).
- **Suggested fix:** register this as a series-3 thread (an audit-code wording fix plus regenerating the
  reports). Do not patch it in the close.

### N-6 (note): this review falsifies TASKS' "no aux review" sentence once it exists
- **Evidence:** TASKS.md (series 2, end of "Dispositions") says: "No other review was taken in this series:
  no aux review file was written under `patches/`, so none is archived beyond the two Qodo comments." That
  is true at `fe9c08f`: `patches/` holds no REVIEW file newer than 2026-10-12. WORKPLAN §2 makes this scoped
  review of the close part of series 2, and README.md:446 says `reviews/` "holds every review a series
  took". Series 1 archived its close review as `reviews/REVIEW-2026-10-12.md`.
- **Suggested fix:** at the maintainer's discretion, either archive this file as
  `reviews/REVIEW-2026-10-14-close.md` (adding it to SHA256SUMS and amending the TASKS sentence) in a docs
  commit before the PR, or leave it untracked and accept the sentence as true at `fe9c08f`. The B8 row
  forbids only a `plan:` commit after the close.
