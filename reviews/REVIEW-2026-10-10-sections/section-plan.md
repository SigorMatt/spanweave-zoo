## The four `plan:` commits — hygiene

Scope: `0bdab8e`, `01da2fb`, `4122152`, `b913e2b` on branch `zoo` of
`/home/msi/git/spanweave-zoo`, read against `WORKPLAN.md` §0.1 (steps 2, 5, 6,
8), §0.2, §0.6, §1, §2, §3, §4, plus `CLAUDE.md` and `CONTRIBUTING.md`.
Read-only review: no tracked file touched, no test suite run, no port bound.
Where a claim was checkable from git or from the shipped tree I say **verified**;
where it rests on the builder's word I say so.

---

### Form and status discipline

**Finding 1 — all four commits touch `WORKPLAN.md` and nothing else. Verified.**
`git show --stat` for each:

```
0bdab8e   WORKPLAN.md | 25 ++++++++++++++++++++++---   (22 insertions, 3 deletions)
01da2fb   WORKPLAN.md | 28 ++++++++++++++++++++++++++--  (26 insertions, 2 deletions)
4122152   WORKPLAN.md | 32 ++++++++++++++++++++++++++++++--  (30 insertions, 2 deletions)
b913e2b   WORKPLAN.md | 34 ++++++++++++++++++++++++++++++++--  (32 insertions, 2 deletions)
```

§0.1 step 5's "Commit the plan edit together with nothing else" holds on all
four. No bin — this is clean.

**Finding 2 — `b913e2b`'s subject carries two clauses after the batch id, where
§0.1 step 5 allows one.** Bin: `thread`.

The rule: "*Commit the plan edit together with nothing else (`plan: <batch>
done`; **a second clause** after the batch id is allowed when it records
something a reader needs).*" The four subjects:

| commit | subject | clauses after `<batch> done` |
|---|---|---|
| 0bdab8e | `plan: A0 done, and verify refuses captures until A1 replaces it` | 1 |
| 01da2fb | `plan: A1 done, and the tee's two sinks need separate out directories` | 1 |
| 4122152 | `plan: A2 done, and its row's receiver port and exporter name were wrong` | 1 |
| b913e2b | `plan: A3 done, run 1 complete, and the project manifest's timing is open` | **2** |

Three of the four are exactly to form. `b913e2b` reads `A3 done` + `run 1
complete` + `the project manifest's timing is open`. Both extra clauses do
record something a reader needs (the run boundary, and the open question), so
this is drift inside the rule's spirit and outside its letter. It is the only
subject-form deviation in the set. A reader skimming `git log --oneline` is
better served by this subject than by a conforming one, which is an argument
for amending the rule at A6 rather than for faulting the commit.

**Finding 3 — every `done (<sha>)` resolves to the right code commit.
Verified.** `git log -1 --format=%s` on each claimed sha:

```
d33059e  zoo: the repository skeleton
69fb6bd  sink: record every POST's bytes, headers and digest, and parse nothing
8c8299f  collector: the stock Collector re-encodes to JSON beside the raw bytes
9074ecd  manifest: a capture declares what it is, and verify checks both directions
```

Each matches its batch's concern, and each sha was set in the plan commit that
immediately follows that code commit (derived parents: `69fb6bd^ = 0bdab8e`,
`8c8299f^ = 01da2fb`, `9074ecd^ = 4122152`, `d33059e^ = 998f1cd`). No status is
stale: at HEAD, A0–A3 are `done` with the four shas above and nothing claims
`done` without one. No bin.

**Finding 4 — A4's `awaiting A3` is now effectively `todo` per §0.1 step 2, but
§2 gates run 2 on something A4's row does not mention.** Bin: `next batch`.

§0.1 step 2: "*A status `awaiting <batch>` is `todo` once that batch is
`done`.*" A3 is `done (9074ecd)`, so A4's row status `awaiting A3` is `todo` and
needed no edit — correct use of the protocol, and the plan rightly left it
alone. A5's `awaiting captures (A4 done and at least one `real` capture
present)` and A6's `awaiting A5` are likewise consistent with §2's order
A4 → A5 → A6.

The inconsistency is one level up. §2 says:

> Run 2 = A4 → A5 → A6 **once at least one `real` capture is in `captures/`**,
> then the scoped review of the close and the PR.

but A4's own row is gated only on A3, and A4 (the replayer) needs no `real`
capture — a recorded one is enough, and `captures/` does not exist in the tree
yet (`ls captures` → no such file or directory). So a builder cold-reading the
file and prompted `Execute WORKPLAN.md run 2` today gets two answers: step 2
says start A4, §2 says wait for a capture. One of the two should move; the
honest fix is for §2 to gate A5 rather than all of run 2. No plan commit
noticed this.

**Finding 5 — §0.1 step 8 ("`git push origin zoo`", written as a run's final
step) and §2 ("Every batch: CI green on the pushed tip before `done`") disagree
on push frequency; the builder had to choose and the plan never records the
choice.** Bin: `thread`.

The builder pushed per batch — verified from `gh run list`, which shows a CI run
per code commit:

```
2026-10-09T21:18:12Z zoo b913e2b success
2026-10-09T21:15:13Z zoo 9074ecd success
2026-10-09T21:13:48Z zoo c965c9b success
2026-10-09T20:51:32Z zoo 8c8299f success
2026-10-09T20:18:40Z zoo 69fb6bd success
2026-10-09T20:02:46Z zoo d33059e success
2026-10-09T20:02:14Z main d33059e success
```

That follows §2 and is the better reading (per-batch CI is what makes "CI green
before `done`" meaningful). But §0.1's numbering puts push *after* step 7's
"Final step of a run", and a cold builder could read it the other way. A
correction belonged in a plan commit under step 5's own logic — a premise the
run showed to be loose.

**Finding 6 — A3's code commit was amended and force-pushed after CI had
already passed on the superseded sha; the plan records nothing.** Bin:
`thread`.

`c965c9b` appears in the CI history above with A3's exact subject, is a real
local object, and has the same parent `4122152` and a byte-identical commit
message as `9074ecd`. The only difference is cosmetic README polish:

```
$ git diff --stat c965c9b 9074ecd
 README.md | 13 ++++++++----- 
```

(adding the `uv run` prefix to two commands and a `uv run zoo verify
captures/z4/<run-id>` line). Both shas are CI-green, so no CI claim is
compromised and the row's `done (9074ecd)` is the right sha. The note is only
that a branch rewrite between 21:13 and 21:15 UTC left no trace in the plan,
and `patches/0006-*.patch` is the rewritten version. Low stakes; worth a line
in the A6 registry rather than a correction now.

**Finding 7 — step 5's row-correction duty was met in-commit every time.
Verified.** Bin: none.

- `0bdab8e` edits A3's row in the same commit (`make check` runs `zoo verify`
  → "*(already wired in A0; A3 extends it from refusal to manifest
  re-hashing)*") **and** carries the matching §4 line ("*A3's row was
  annotated: `make check` already depends on `verify` as of A0, one batch
  earlier than that row implied.*"). Same commit. ✅
- `01da2fb` makes no row correction; nothing A1 found falsified a row, and the
  §4 notes say why the tensions it did find were resolved inside A1's own row.
  ✅ (vacuously)
- `4122152` edits A2's row (two premises) **and** carries the §4 line
  ("*two row premises were wrong and the row is corrected above*"). Same
  commit. ✅
- `b913e2b` edits A3's row (five → "four typed commands and a `Ctrl-C`")
  **and** carries the §4 line ("*The row's "five commands" is corrected
  above.*"). Same commit. ✅

Nothing was deferred to a later commit. This is the plan's strongest point.

**Verdict:** form and status discipline hold — all four commits are
WORKPLAN-only, all four shas resolve, and every row correction landed with its
§4 line in the same commit; the single form deviation is `b913e2b`'s
two-clause subject, and the two real gaps are protocol self-contradictions
(§0.1 step 8 vs §2 on pushing, §2 vs A4's row on gating) that no plan commit
corrected.

---

### What §4 records, and what it does not

**Finding 8 — A2's §4 note omits the CI claim §0.1 step 8 requires; A0, A1 and
A3's notes all carry it. The fact itself is green.** Bin: `next batch`.

§0.1 step 8: "*A run is not finished until the push succeeds **and the GitHub
checks on the pushed tip are green, or every failing check is explained in the
run report***". The four §4 notes:

- A0: "*skeleton landed on `main`, **CI green on all five legs** (ubuntu
  3.11/3.12/3.13/3.14, macos 3.12)*"
- A1: "*the sink records and parses nothing; **CI green on all five legs**.*"
- A2: "*the stock Collector re-encodes beside the raw. `otelcol-contrib
  0.162.0` pinned … `make check` is green **both ways** — 94 passed with the
  binary, 91 passed + 3 skipped without, verified by moving it aside.*"
  — **no CI claim anywhere in A2's three §4 bullets.**
- A3: "*the capture declares what it is and verify checks both directions. **CI
  green on all five legs**; `make check` green with the binary (121 passed) and
  without (118 + 3 skipped).*"

A2 is the one batch whose plan record omits it. The claim does exist in
`4122152`'s commit *message* body ("*A2 landed the Collector tee (8c8299f) with
CI green on all five legs*"), and the plan's header says "*This file plus git is
the only state*", so a cold reader can recover it — but §4 is where the file
puts the per-batch record, and A2's is the only one that forces the reader into
`git log`. I verified the underlying fact independently: `gh run list` shows
`8c8299f` → `success`, and `.github/workflows/ci.yml` runs both `make check`
and `make install-check` across the five legs, so "green" covers
`install-check` too. The gap is bookkeeping, not an over-claim.

**Finding 9 — the test totals (94/91, 121/118) are not verifiable from git; the
"+3 skipped" half is structurally corroborated.** Bin: `thread`.

I did not run the suites (other agents hold 4317–4320). What rests on the
builder's word:

- "**94 passed with the binary, 91 passed + 3 skipped without**" (A2)
- "**121 passed** … and without (**118 + 3 skipped**)" (A3)

What I could check without running anything:

- `tests/test_collector_real.py:41` defines `needs_collector =
  pytest.mark.skipif(...)` and exactly **three** tests wear it (lines 109, 127,
  233). The "+3 skipped" and the 94−91 = 3 and 121−118 = 3 arithmetic are
  therefore consistent with the tree. Verified.
- Test-function counts rise 32 → 67 → 90 across `69fb6bd`, `8c8299f`,
  `9074ecd`, with `parametrize` in three files. 67 functions expanding to 94
  collected and 90 to 121 is plausible. This is a plausibility check, not
  verification.

Both notes do name what they claim to have run (`make check`, with and without
the binary, "*verified by moving it aside*"), which is what step 8 and
`CONTRIBUTING.md` ask for. Treat the absolute numbers as the builder's word and
re-derive them at A6 when the registry is written.

**Finding 10 — the A1 process admission is accurate and, if anything, harsher
on itself than the facts require. Verified.** Bin: none.

> *2026-10-09 A1 (process, for the cold reader): the batch ran its parent check
> against `d33059e` rather than its own derived parent `0bdab8e` (`69fb6bd^`).
> Neither contains the sink, so both runs are vacuous and the named mutation is
> what carried the bar; no re-run was ordered. §0.2's derived-parent rule is
> unchanged and still binds later batches.*

Verified three ways: `git rev-parse 69fb6bd^` = `0bdab8e`; `git diff --stat
d33059e 0bdab8e` = `WORKPLAN.md | 25 +++---` and nothing else, so the two trees
are **identical for all code** and the wrong parent could not have changed the
result; and `git ls-tree -r --name-only d33059e` shows only `cli.py`,
`__init__.py`, `py.typed` under `spanweave_zoo/` — no `sink.py`. The admission
is true, voluntary, and the kind of thing nobody else would have caught. The
word "vacuous" slightly overstates it (a parent genuinely lacking the
implementation is the informative case §0.2 wants; what is vacuous is a parent
that fails on import), but erring toward self-accusation is not a hygiene
problem.

**Finding 11 — A3's "the parent run was not vacuous for once" is verifiable from
git and checks out. Verified.** Bin: none.

> *The parent run was **not** vacuous for once: on `4122152` an unlisted body on
> disk made `verify` exit **0**, and `verify <run dir>` printed "no captures"
> and exited 0 — both are 1 now.*

Confirmed without running anything. At `4122152`, `spanweave_zoo/manifest.py`
contains no `_unlisted` function (`git show 4122152:spanweave_zoo/manifest.py |
grep _unlisted` → nothing), while at HEAD `manifest.py:415` reads `return found
+ _unlisted(run, document)`. And `4122152`'s `cli.py:_run_directories` lacks the
`return [root]` early path that HEAD's `cli.py:100` has, so a run directory
passed directly fell through to the `glob` and produced the "no captures … exit
0" the note describes. Both claims hold structurally.

**Finding 12 — A3's "the brief required the capture to fail loudly at the
*start*" names a requirement the A3 row does not contain, so a cold reader
cannot check it.** Bin: `thread`.

The §4 note opens: "*The brief required the capture to fail loudly at the
*start* if the project's `MANIFEST.json` is missing…*". A3's row says only
"*the project's own `MANIFEST.json` (copied from a path the operator passes)*"
— silent on timing and on failing loudly. The requirement therefore came from
the dispatch brief, which lives in a discarded sub-agent context and not in the
repo. The substance is fine (the requirement *was* met — `README.md:154` says
"*Both are checked **before** anything is recorded*" and `SPEC.md` §5.3 makes
the refusal a start-of-capture one), but "the brief required" is an
unauditable citation in a file whose whole purpose is cold resumption. §5
(Origins) is where such a premise would be citable.

**Finding 13 — nothing in any plan edit licenses the zoo to fix a finding in
another repo; invariant 7 is intact. Verified by reading all four diffs.** Bin:
none.

The two "defects found and fixed" are the zoo's own code and are correctly
scoped:

- A2: "*`SIGINT` did **not** stop a capture (the main thread parked in an
  untimed `Event.wait` …), leaving the Collector holding its port. Handlers are
  installed and the wait polls (SPEC §4.6).*"
- A3: "*the sink's "already holds a body" refusal globbed `*` + suffix, and the
  json sink's suffix is `.json`, so `0001.headers.json` counted as a body…*"

Both are `spanweave_zoo/` bugs — the repo that owns the defect fixing it in its
own series, which is exactly what `CLAUDE.md` rule 7 prescribes. No §4 line
touches `spanweave` or `spanweave_live`, no pinned sha moved (plan commits touch
only `WORKPLAN.md`), A5's row still reads "**Findings are never fixed here**",
and §3's standing decision still reads "*the receiver's answer to raw protobuf
(expected: 415 today) is the audit's first finding, not something the zoo works
around*". No relaxation.

**Finding 14 — the A3 note's "SPEC §1.1 was amended" is a real widening of an
invariant's text, and it is declared rather than smuggled. Verified.** Bin:
`thread` (for the reviewer of A3's code, not for the plan).

The plan says: "*A1's missing `content_type`/`content_encoding` are carried
across by `manifest.finish()` from each body's own `headers.json`, so the sink
still inspects nothing; **SPEC §1.1 was amended** in the same commit to say so
rather than leave the two texts contradicting.*" I read the amendment
(`git show 9074ecd -- SPEC.md`). It converts one exception into a named list:

> *Two things are not that, and are named here rather than discovered as
> exceptions: … two documents that are not payloads are read as documents: the
> capture's own `MANIFEST.json`, which the zoo wrote, and the pet project's
> `MANIFEST.json`, which the zoo copies into it verbatim and reads no field of
> (§5).*

and adds "*That is a copy of what the exporter claimed, not an inspection of
what it sent, and no byte of a body is read to do it.*" This does not relax
`CLAUDE.md` rule 3 ("the sink parses nothing") — it reads a header the sink
itself recorded verbatim, not a payload — and the amendment says out loud that
A1 and A3 had contradicted each other. Flagged only so the code reviewer knows
an invariant's prose moved in A3; the plan's account of it is honest.

**Verdict:** §4 hides nothing material — every claim I could check from git
(the shas, the wrong-parent admission, the non-vacuous A3 parent, A2's CI, the
3 collector-gated skips, the SPEC §1.1 amendment) came back true — but A2's
note omits the CI line step 8 requires, the four passed/skipped totals are the
builder's word, and one note cites a "brief" a cold reader cannot read.

---

### The open decision (b913e2b)

**Finding 15 — A3 met `CLAUDE.md`'s halt condition by the §4 note's own words,
yet is marked `done` rather than `awaiting decision`, and no
`OPEN_QUESTIONS.md` exists.** Bin: `next batch`.

The note (`WORKPLAN.md` §4, 2026-10-10):

> *2026-10-10 **A3 — open for the maintainer, and it affects the Z4
> handover.** The brief required the capture to fail loudly at the *start* if
> the project's `MANIFEST.json` is missing, but `EXPORT-CONTRACT.md` has the
> project write its manifest *during* its run. So `zoo capture` copies the
> manifest the project's **previous** run left behind, and SPEC §5.3 and the
> README say that plainly rather than implying it belongs to the recorded run.
> Taking the copy at the **end** instead would make the manifest
> contemporaneous with the bytes; **that is a spec decision, not a patch, and
> it is unresolved.** Z4's first real run will carry a manifest from its
> recorded run unless this is decided first.*

Set that against the protocol it is subject to. §0.3's batch brief: "*If
completing the batch would require … a rule or a policy the spec does not
already state — stop, write the options to OPEN_QUESTIONS.md under a heading
"<ID>: …", commit that alone, and report `awaiting decision`.*" `CLAUDE.md`,
Halt points, lists the same trigger. §0.1 step 6: "*Stop when: … a batch ends
`awaiting decision`*".

The note's own sentence — "*that is a spec decision, not a patch*" — is the
halt trigger quoted back. By the letter of the protocol A3 should have reported
`awaiting decision`, the run should have stopped before A3 shipped, and
`OPEN_QUESTIONS.md` should exist. It does not: `ls OPEN_QUESTIONS.md` → no such
file.

What saves it from being a status that papers over a halt is that the batch did
not *need* the decision to finish. The brief's actual requirement (refuse at the
start if the manifest is missing) was implemented; `SPEC.md` §5.3 states the
consequence in plain words rather than hiding it —

> *(A practical consequence, because operators hit it: the project writes its
> manifest when it runs, so the file the capture copies is the one the
> project's own run left behind. The zoo takes what is there when the capture
> starts and makes no claim that it was written by the run it recorded; what it
> does claim — the pin, the digests, the two timestamps, the declaration — it
> writes itself.)*

— and `README.md:172` repeats it for the operator. So the shipped behaviour is
documented, defensible and not silently chosen; the open question is whether a
*better* behaviour (copy at the end) should replace it. That is a refinement
question, not a blocker for A3's acceptance criteria, and `done` is a fair
reading. **My judgement: a defensible but non-conforming use of the protocol.**
The protocol has only two gears — `done` and `awaiting decision` (run stops) —
and this case wanted a third: shipped, documented, and open. The builder
invented that third gear in §4 prose instead of in the status column, which is
the right instinct expressed in the wrong place.

**Finding 16 — §3 (Decisions log) should not gain an entry for this, but the
plan has no registry for *open* questions and two are now adrift in §4 prose.**
Bin: `next batch`.

§3 is a log of decisions with a `By` column (its one row is `| 2026-10-09 |
series | … | maintainer |`). No maintainer has decided the manifest timing, so
a §3 row would be a fabrication — the plan is right to leave §3 alone. But that
leaves two unresolved maintainer questions living only as §4 bullets:

1. A0: "*no `LICENSE` and no `license` field in `pyproject.toml`. … Awaiting
   the maintainer; it blocks nothing in run 1 and should land before the A6
   PR.*" Still true at HEAD: `ls LICENSE` → no such file, and `grep license
   pyproject.toml` → nothing.
2. A3: the manifest timing, above.

§0.3 and `CLAUDE.md` both name `OPEN_QUESTIONS.md` as the home for exactly
this, and neither question is in it because it does not exist. A6's row folds
"§3 and §4" into `TASKS.md`, so the questions are not *lost* — but they are
carried as narrative inside a file the protocol deletes, retrievable only by
someone who reads all twelve §4 bullets. One `OPEN_QUESTIONS.md` with two
headings would cost one commit and make both auditable.

**Finding 17 — the open decision does not block A4, but it does block the Z4
real capture, which is how §2 defines the start of run 2.** Bin: `blocks run 2`
(as §2 scopes run 2); `thread` for A4 alone.

The chain, stated plainly:

- **A4 (the replayer) is unaffected.** Its row concerns bodies, captured
  headers, receipt order and `--timing` through an injected `sleep`. Nothing in
  it reads `project_manifest`. A4 can be built today against a recorded
  capture.
- **The Z4 real run is affected.** The note says so: "*Z4's first real run will
  carry a manifest from its recorded run unless this is decided first.*" And a
  capture is immutable — `CLAUDE.md` rule 2 and `CONTRIBUTING.md`, "Captures":
  "*A capture is a record and is never edited. Not to redact it, not to fix a
  truncated body, not to make a test pass.*" So if the maintainer later prefers
  the end-of-run copy, the already-taken Z4 capture cannot be corrected; it can
  only be superseded by a second real run with a new `<run-id>`. The decision is
  cheap now and expensive after the pilot runs.
- **A5 gates on that capture** ("*awaiting captures (A4 done and at least one
  `real` capture present)*"), and §2 gates all of run 2 on it.

**So: it blocks run 2 as §2 defines it, and it blocks the Z4 handover, but it
does not block writing A4.** The practical recommendation is to decide before
Z4 is asked to make its real run, not before A4 is dispatched — and to fix §2's
gating (Finding 4) so the two readings stop disagreeing.

**Verdict:** `done` on a batch carrying an unresolved spec question is a
defensible stretch of a two-gear protocol rather than a concealed halt — the
behaviour is shipped, specced and documented honestly — but the question needs
an `OPEN_QUESTIONS.md` home and a maintainer answer before Z4's real run, which
is the gate §2 puts in front of run 2.

---

### Claim: the three row corrections are stated truthfully

> The row corrections the builder made — ports **4320**, exporter **otlp_http**,
> and **"four commands"** — are stated truthfully in §4.

**Two of the three are true and honestly framed. The third is numerically
correct, but its stated justification is false about the artifact it cites and
it kindly mislabels a tightening as a correction of an error.**

#### (a) Port 4320 — true, verified, and the prose says the row was wrong

The §4 line (`4122152`):

> *2026-10-09 A2: **two row premises were wrong and the row is corrected
> above.** (1) "`otlp` receiver on 4317/4318" collides with the raw sink, which
> A1 put on 4318; the config's endpoints are now `${env:NAME:-default}` whose
> defaults are exactly 4317/4318/4319 and `zoo capture` moves the Collector's
> HTTP receiver to 4320 (SPEC §4.2 says why).*

Row text before (`git show 4122152`):

> *…`otlp` receiver on 4317/4318, `otlphttp` exporter with `encoding: json`…*

Row text after:

> *…`otlp` receiver on 4317/4318 **by default, overridable** (4318 is the raw
> sink's own port, so `zoo capture` moves the Collector's HTTP receiver to
> 4320), …*

Checked against the tree at HEAD. `collector/config.yaml` alone does **not**
put the receiver on 4320 — line 28 is
`endpoint: ${env:ZOO_COLLECTOR_OTLP_HTTP:-127.0.0.1:4318}`, and line 26 is the
gRPC default `…:-127.0.0.1:4317`. The 4320 comes from the capture path:
`spanweave_zoo/capture.py:49` `DEFAULT_COLLECTOR_PORT = 4320` →
`spanweave_zoo/cli.py:356` (`--collector-port`, that default) →
`cli.py:229` `http_port=args.collector_port` →
`spanweave_zoo/collector.py:178` `ENV_HTTP: f"{self.host}:{self.http_port}"`,
with `ENV_HTTP = "ZOO_COLLECTOR_OTLP_HTTP"` at `collector.py:41`, injected into
the child's environment at `collector.py:186`. **Verified: config + capture code
do put the Collector's HTTP receiver on 4320, and the config standing alone
defaults to 4318 — which is exactly the distinction the corrected row draws.**
`SPEC.md:554` (`| --collector-port | 4320 |`) and `capture.py:11` agree.

The prose names the error, attributes it ("which A1 put there"), and cites
where the reasoning lives. Honest. **Verdict: true and truthfully stated.**

#### (b) Exporter `otlp_http` — true, verified against the shipped binary

The §4 line (`4122152`):

> *(2) `otlphttp` is a deprecated alias at 0.162.0; the config uses
> `otlp_http`, the same component.*

Row before: "*`otlphttp` exporter with `encoding: json`*". Row after:
"*`otlp_http` exporter (`otlphttp` is a deprecated alias at 0.162.0, same
component)*".

`collector/config.yaml:41` is `otlp_http:`, and the pipeline at line 65 is
`exporters: [otlp_http]`. I confirmed the component name from the pinned binary
itself (`./otelcol-contrib components`, a read-only subcommand that binds no
port):

```
    - name: otlp_http
      module: go.opentelemetry.io/collector/exporter/otlphttpexporter v0.162.0
```

and `./otelcol-contrib --version` → `otelcol-contrib version 0.162.0`, matching
`collector/VERSION`. **Verified: `otlp_http` is the canonical name of the
`otlphttpexporter` component at the pinned version.** The narrower sub-claim —
that `otlphttp` is specifically a *deprecated alias* the Collector *warns*
about — is not shown by `components`, which lists canonical names only; it
appears to be the case and rests on the builder's word plus the config comment
at `config.yaml:38-40`. The material claim (the row's spelling was wrong, the
config must say `otlp_http`) is verified.

The prose again says plainly that the row was wrong. **Verdict: true and
truthfully stated.**

#### (c) "Four commands" — the count is right; the justification is not

The §4 line (`b913e2b`) is one clause: "*The row's "five commands" is corrected
above.*" The correction itself lives in the row, and it carries the
justification:

Row text **before** (`git show b913e2b`):

> *`README.md` §"Running a pet project's real run": **the five commands an
> operator types.***

Row text **after**:

> *`README.md` §"Running a pet project's real run": the commands an operator
> types — **four typed commands and a `Ctrl-C`**, in two terminals (the row
> said "five", **which holds only by counting the keystroke**).*

And `b913e2b`'s commit message body:

> *The row's "five commands" is corrected to four and a Ctrl-C, **which is what
> the README now says.***

**I counted the README as shipped (`README.md:107–187`). Five fenced blocks, of
which four are typed shell commands and one is a keystroke:**

1. `make collector` (bash)
2. `uv run zoo capture --project z4 --run-id 2026-10-10T09-00-00Z --kind real --project-manifest ../streaming-concierge/MANIFEST.json` (bash)
3. `make run-real ENDPOINT=http://localhost:4318` (bash)
4. `Ctrl-C` (an unlabelled block, not bash)
5. `make verify` (bash)

**My count: four typed commands and a `Ctrl-C`, in two terminals.** The row's
new number is factually right about the README's content.

But the README's own prose does not say that. `README.md:109`:

> ***Five commands, in two terminals.** `z4` (`streaming-concierge`) is the
> pilot; `<run-id>` is yours to choose…*

and `README.md:184`:

> *A **recorded** run is the same **five commands** with `--kind recorded` and
> the project's `make run-recorded`.*

and the explanatory list at `README.md:146–167` is numbered **1–5** with
"**4. Ctrl-C**" as an item among the commands. The A3 code commit `9074ecd` is
what *added* that section — `git show 9074ecd -- README.md` shows
`+**Five commands, in two terminals.**` and `+A **recorded** run is the same
five commands` as new lines.

So two things are wrong here, in increasing order of seriousness:

**Finding 18 — `b913e2b`'s commit message states as fact something the README
contradicts.** Bin: `next batch`.

"*…corrected to four and a Ctrl-C, which is what the README now says*" is
false. The README says "Five commands, in two terminals" twice and numbers
Ctrl-C as command 4 of 5. The correction edited the *plan* to disagree with the
*artifact*, then asserted agreement. Before `b913e2b`, row and README both said
five and agreed; after it, the row says four-plus-a-keystroke and the README
says five. The plan is now the only place that holds the stricter count, and it
claims the README backs it. The fix is one line in the README (or reverting the
row), and it is cheap — but a cold reader who trusts the commit message and
opens the README finds the opposite.

**Finding 19 — "which holds only by counting the keystroke" is a kind
description of the row, not an accurate one; the row was not wrong in the sense
step 5 means.** Bin: `thread`.

Step 5's duty is for a row whose "*acceptance number or premise was shown
wrong by the batch*". Compare the two texts:

- Row, before: "*the five commands an operator types*"
- §4/row, after: "*the row said "five", which holds only by counting the
  keystroke*"

"Holds only by counting the keystroke" concedes that the row *does* hold on one
reading — and that reading is the one the README itself adopts, in the same
commit, in bold, twice. So this is not a wrong acceptance number corrected; it
is a loose phrase ("commands an operator types", where one of the five is a
keystroke rather than a command) tightened into a precise one. Calling that a
correction is generous to the pedantic reading and harsh on the original. The
*inverse* of the usual sin: not a plain error dressed as a nuance, but a
nuance dressed as a plain error — and the dressing-up produced a real
plan/README divergence that did not exist before.

It is also already stale inside the plan. `4122152`'s A2 note still reads
"*A3's **five-command** README section must be exercised the same way*". At
HEAD the file therefore carries three texts and two numbers: §4's A2 note says
*five-command*, A3's row says *four typed commands and a `Ctrl-C`*, and the
README says *Five commands*. §4 is append-only history, so the A2 note is not
itself a fault — but a reader resolving "how many commands" from the plan gets
no single answer.

**Verdict on the claim:** two-thirds true. The **4320** and **otlp_http**
corrections are verified against the shipped tree and the pinned binary, and
their §4 prose says outright that the row was wrong and why — these are model
step-5 entries. The **"four commands"** correction states a count I verified by
hand, but its stated warrant is false (the README as shipped says "Five
commands" twice and numbers Ctrl-C among them), and "holds only by counting the
keystroke" mislabels a tightening of loose wording as a corrected error. The
claim as put to me — that all three are stated truthfully in §4 — **does not
hold for the third.**
