# OPEN_QUESTIONS.md

The register of questions this repository could not answer for itself, and of
how each was answered. `CLAUDE.md` ("Halt points") says a batch that would have
to invent a rule or a policy `SPEC.md` and `CLAUDE.md` do not already state
**stops**, writes the options here under a heading naming the batch, commits
that alone, and reports `awaiting decision`. This is the file that makes that
reportable instead of a note in a commit message.

An answered question is **kept here with its answer**, not deleted: the reason
a capture is shaped the way it is has to outlive the batch that shaped it, and
"why is the manifest copied at the end?" is a question a reader of a capture
will ask long after the plan that settled it is gone. `SPEC.md` is where the
resulting behaviour is normative; this file is why it is that and not the other
thing.

Each entry says what was asked, what the options were, what was decided, who
decided it, and where the decision now lives.

A citation of `WORKPLAN.md` below is to series 1's plan, which was deleted at
that series' close: its §3 (decisions log) and §4 (resume notes) are folded
verbatim into `TASKS.md`, and the whole file as it last stood is
`git show 22be077:WORKPLAN.md`.

---

## 1. When is the pet project's `MANIFEST.json` copied into the capture?

**Status: resolved, 2026-10-10, by the maintainer. Implemented in A3b
(`810f2db`); normative in `SPEC.md` §5.3.**

**Asked by** A3, which shipped the start-of-run copy and recorded the question
rather than deciding it (`WORKPLAN.md` §4, 2026-10-10; review finding F4).

**Why it was a question.** `EXPORT-CONTRACT.md` §1 has the pet project write
its own `MANIFEST.json` *while it runs*. A capture that copies that document
when `zoo capture` starts therefore copies whatever the project's **previous**
run left behind — verified empirically, not inferred: a source manifest edited
mid-capture landed byte-identical to its pre-edit version. A capture is
immutable, so a real run taken under the start-of-run copy bakes in a manifest
that does not describe it, permanently. Which document belongs in the record is
not a detail of the implementation; it is what the capture *claims*, so it was
a spec question and not a patch.

**The options that were weighed.**

1. **Copy at the start.** The path is checked while nothing is on disk, so a
   typo is refused early — but the document is the predecessor run's, and the
   record quietly misdescribes itself.
2. **Copy at the end, after `Ctrl-C`.** The document is contemporaneous with
   the bytes. The cost is that a project which wrote no manifest, or wrote a
   stale one, is only discovered at the end of the run.
3. **Copy at both ends and keep both.** Lossless, and it makes every reader
   decide which of two documents is the capture's — the ambiguity moves rather
   than going away.

**The decision.** Option 2. The project's `MANIFEST.json` is copied **at the
end** of the capture, after `Ctrl-C`, so the copy is the one the recorded run
wrote. The `--project-manifest` **path** is still checked at the start, so a
typo is refused while nothing is on disk. If the document is absent at the end,
or its `started_at` predates the capture's own, the capture is finalized with
`project_manifest: null` and a `problems` entry naming why, `zoo capture` exits
non-zero, and `zoo verify` fails on any capture carrying `problems`. **A
capture is never silently fine** — this is the rule the whole entry turns on,
and it is why the honest refusal was preferred to the convenient early check.

**What it cost the plan.** A3's status stayed `done` because what it shipped was
right, but the batch should have ended `awaiting decision` with this entry
(review finding F14). That is the reason this file exists, and the reason the
rule is now a decision in its own right rather than a habit.

---

## 2. Under what licence is the zoo published?

**Status: resolved, 2026-10-10, by the maintainer. Implemented in A0a:
`LICENSE` and `pyproject.toml`'s `license` / `license-files`.**

**Asked by** A0, which shipped no `LICENSE` and no `license` field and declined
to invent one (`WORKPLAN.md` §4, 2026-10-09; review thread T5). Until A0a the
built wheel carried no licence at all, which is a question a stranger meets
before any of this repository's claims about bytes.

**The options.** MIT, as both sibling repositories (`spanweave`,
`spanweave-live`) already are; Apache-2.0, for its patent grant; or no licence,
which is "all rights reserved" and makes a public capture-and-reproduction
repository useless to the people it is for.

**The decision.** MIT, declared exactly as the siblings declare it — an SPDX
expression plus the file — and the `LICENSE` file is byte-identical to theirs,
holder included. Three repositories that are read together should not differ on
this, and the difference would be the only thing a reader would have to check.

---

## 3. A project manifest that is present but has no readable `started_at`

**Status: open as a preference, not as a defect. A3b (`810f2db`) chose one
behaviour as a corollary of §1 and recorded that the maintainer may prefer
another (`WORKPLAN.md` §4, 2026-10-10).**

**The case.** §1's decision covers the project manifest being absent and being
dated before the capture. It does not cover a document that is present and
parseable but whose `started_at` cannot be read at all — missing, or not a
timestamp.

**What happens today.** The document is kept **and** a `problems` entry is
recorded, so the capture fails `zoo verify` rather than passing with a manifest
nobody can date (`SPEC.md` §5.3's four-outcome table). That follows from "a
capture is never silently fine" plus losslessness: the bytes the project wrote
are part of the record even when they cannot be checked.

**The alternatives, if the maintainer prefers one.**

1. **`project_manifest: null` plus the problem**, as for an absent document —
   consistent with §1's second branch, at the cost of discarding bytes the
   project did write.
2. **Keep the document and record no problem** — the capture verifies, and the
   undatable manifest is left for a reader to notice. Cheapest, and the one
   option that lets a capture be quietly wrong.

Nothing is blocked on this: a capture that hits the case fails loudly either
way, and the only difference is whether its bytes are kept. It is registered so
that the choice is a decision rather than an accident of the batch that met it
first.

---

## 4. A0c: the log-to-file variant and the run directory

**Status: resolved, 2026-10-11, by the maintainer: option 2. Asked by A0c
(2026-10-11), which stopped rather than write a README sentence the code
makes false.**

**The conflict.** The decision of 2026-10-11, "the run's record"
(`WORKPLAN.md` §3), says: *"The README's optional log-to-file variant writes
under the run directory, never into the checkout."* The README's variant
(step 3, `> capture.log 2>&1 &` plus the anchored `grep`) cannot be pointed
under the run directory without breaking two things the spec already states.
This was established by a rehearsal in a scratch clone, not inferred:

- **(a) The log breaks `zoo verify`.** The manifest lists and hashes every file
  in the run directory except `MANIFEST.json` (`SPEC.md` §2.5, §5.6), so a
  `capture.log` sitting there is walked, hashed and sealed like any other file.
  But `zoo capture` prints its summary line — into that same log, through the
  shell's redirect — *after* the manifest is assembled. The file then no longer
  matches its own entry. Observed: `zoo verify` fails with
  `capture.log sha256 is efea…, MANIFEST.json says 4758…`, rc 1, on a capture
  that is otherwise sound. A clean run that fails verification is exactly the
  "capture silently fine / silently broken" ambiguity §1 above was decided
  against.
- **(b) The log creates the capture before it is ready.** A redirect into
  `captures/<project>/<run-id>/capture.log` makes the shell create that run
  directory before `zoo capture` has even started. README step 3 says that
  until the readiness line prints "the capture directory does not exist", and
  `SPEC.md` §4.6 says a capture exists on disk only once it is ready and that a
  refusal to start writes nothing. With the variant as the decision words it,
  both become false: a refused start leaves a run directory holding a log.

Only a code change can make the decision's wording true. A0c is docs only, so
it stops here.

**The options, each with its cost.**

1. **`zoo capture --log <name>`.** The zoo itself opens the operator log
   inside the run directory *after* readiness (so nothing exists before
   ready, and a refusal still writes nothing), and finalizes it — summary line
   included — *before* the manifest is assembled, so its hash is the file's
   last state. The decision's wording becomes true as written. Cost: code, a
   `SPEC.md` change (§4.6's options and output, §5.5's write order), tests
   red-first, and a new batch; the readiness wait in the README would then grep
   a file that does not exist until ready, so the supervisor snippet changes
   too (it must wait for the file before grepping it). Pre-readiness output
   (a refusal's message) still has to go somewhere — stderr to the terminal.
2. **The log goes outside the checkout** (`"$TMPDIR"/capture.log`, or under
   `~`). Docs only; A0c can finish with it. Cost: the decision's wording is
   amended ("…writes outside the checkout and outside the run directory"), and
   the operator log is not part of the record — which is arguably correct,
   since `collector.log` already is, and the operator log is only the
   readiness line, the per-body lines and the summary, all of which the
   manifest and the journals restate.
3. **Exclude the operator log from the manifest by name.** Small code change
   in the walk and in `zoo verify`. Cost: it weakens "every file in the run
   directory except itself" (§2.5, §5.6) into a list of exceptions, it leaves
   (b) untouched (the redirect still creates the directory before ready), and
   a file name becomes something `zoo verify` trusts without hashing. Of the
   options it is the one that makes the record say less than it holds.
4. **Drop the variant from the README.** Docs only. Cost: a supervisor (the
   README's stated reason for the variant) loses its documented way to wait for
   readiness, and the decision's sentence is retired rather than satisfied.
5. **A git-ignored directory in the checkout** (e.g. `logs/capture.log`, plus
   a `.gitignore` line). Docs and one ignore line, no code. Cost: it is still
   "into the checkout", so it contradicts the decision's wording the same way
   option 2 amends it, and `.gitignore` gains an entry whose only job is an
   operator convenience. Its gain over 2 is that the log is findable beside
   the capture it describes.

A log written *beside* the run directory (`captures/<project>/<run-id>.log`)
was considered and not offered: `captures/` is committed by design
(`.gitignore`), so the log would enter the record without being sealed, and
whether `zoo verify`'s walk of `captures/` tolerates a stray file there was not
tested.

**Context for the decision, not options.** A0c's row lists seven differences.
The rehearsal showed the other six are closable by documentation alone, and
none of them is blocked by this question:

1. Ctrl-C — made true by A3e.
2. `make verify` / `make check` green after a clean run.
3. The Collector's lines out of the terminal (A3e; now `collector.log`).
4. The body count — `N body/bodies in raw/, M in json/`, as A3e prints it.
5. The digest wording in step 2.
6. The note that a pet project's `make run` rewrites its own `MANIFEST.json`,
   which the operator does not commit from the pet's checkout.

Side findings the rehearsal turned up, all docs, none of them deciding
anything:

- `README.md`'s Layout and the `SPEC.md` §2 tree list neither `collector.log`
  nor `json/NNNN.headers.*`, both of which a real capture contains.
- The `Makefile` comment on `collector` says the sha256 is checked against
  "the release's own digest"; it is checked against the pin in
  `collector/SHA256SUMS`.
- README step 2 says `make collector` is "once per machine"; the binary lands
  in `collector/` of the checkout, so it is once per checkout.
- Review N-1: `zoo verify`'s message wording.

**The decision.** Option 2. The README's log-to-file variant writes outside
the checkout and outside the run directory, to
`"${TMPDIR:-/tmp}"/zoo-capture-<run-id>.log`, and the README says in one
sentence that the operator log is not part of the record, because
`collector.log` is. The 2026-10-11 decision "the run's record"
(`WORKPLAN.md` §3) is amended to say so. Nothing in the code changes for
this: neither (a) nor (b) can arise when the log is not in the run
directory. A0c re-runs in full with the six differences above, this one as
decided, and the side findings.

---

## 5. A5: `agentgolden` is not a pinned dependency

**Status: resolved, 2026-10-12, by the maintainer: option 1. Implemented in A5
(`f60f69c`, `701fc80`); normative in `SPEC.md` §7 and `CLAUDE.md` rules 6
and 8. Asked by A5 (2026-10-12), which stopped before writing any code: the
row's step 5 needs a dependency the repository does not declare.**

**The conflict.** A5's row (`WORKPLAN.md` §1) has step 5 compute
"`agentgolden`'s `Signature` on each graph as a smoke, no rules evaluated".
`pyproject.toml`'s `audit` extra pins exactly two packages by git sha —
`spanweave@fec7da27` and `spanweave-live@cddc694b` — and nothing else;
`agentgolden` appears in no file of this repository but the row, and no
decision in `WORKPLAN.md` §3 adds it. `CLAUDE.md` §0.6 rule 8 and "Halt
points" make the dependency set and its pins a maintainer's call, so the batch
does not add a third pin on its own.

**Facts gathered, so the decision need not re-gather them.**

- `agentgolden` exists at `https://github.com/SigorMatt/agentgolden`;
  `origin/main` is `aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` (0.1.0).
  `agentgolden.signature.Signature` and `agentgolden.signature.signature(graph)`
  exist at that sha.
- Its only runtime dependency is `spanweave>=0.9.1,<1.0`. The pinned
  `spanweave@fec7da27` is version 0.9.1, so the range admits the pin and
  the resolver would not pull a second spanweave.
- The `Cap(0)`-at-end completion policy the row names **is** expressible
  without a change anywhere: `spanweave-live serve --requests N` stops after N
  requests, and the end of input then runs `Run.finish()`, which replaces the
  completion with `Cap(0)` and ticks once (`spanweave_live/cli.py` at
  `cddc694b`, `SPEC.md` §8.5 there). That part of the row is not a question.
- Nothing else in the row was found to need a rule the spec lacks, as far as
  the batch read before stopping. SPEC §7 is an empty heading today, which is
  expected: A5 writes it.

**The options, each with its cost.**

1. **Pin `agentgolden` by git sha in the `audit` extra**, beside the two
   existing pins (`agentgolden @ git+https://github.com/SigorMatt/agentgolden@aa1847f2…`),
   relock, and let the audit module import it (it is already the one module
   the import gate exempts). Step 5 runs as written. Cost: a third pinned
   repository whose sha must be recorded with every finding; the gate in
   `tests/gates.py` names only `spanweave` and `spanweave_live`, so whether
   `agentgolden` joins the gated names (and its import is likewise confined to
   `audit.py`) is part of the decision.
2. **Drop step 5 from A5** (or move it to A6 / the next series as a probe).
   Steps 1–4 run unchanged. Cost: the row's smoke of a consumer on a
   stranger's graph is not taken this series; `PROBES.md` would carry it as an
   unrun probe.
3. **Run `agentgolden` out of process from a separate environment** (e.g. its
   own checkout's venv) over the graphs the audit writes, and record its
   output. Cost: the reproduction then depends on an environment `pyproject.toml`
   does not describe, which is the floating-dependency problem the `audit`
   extra's pinning exists to prevent; not recommended.

**The decision (2026-10-12, maintainer).** Option 1. `agentgolden` is pinned
at `aa1847f2a2ad51a95b98ab3e180bc5d211e6b138` in the `audit` extra and
relocked; the import gate's analyser names become `spanweave`,
`spanweave_live`, `agentgolden`, all confined to `spanweave_zoo/audit.py`;
the audit report's header records the three shas. Step 5 runs as written and
reports a raise as a finding naming its owner. Option 3 is rejected for the
reason the batch gave; option 2 would leave the one consumer smoke of the
series untaken for the cost of a line in `pyproject.toml`. Applied in
WORKPLAN.md §3 by the same commit.

## 6. B1: `zoo capture` does not pick the Collector's port, so there is nothing to pick again

**Status: open, 2026-10-12. Asked by B1, which stopped before writing any
code or test: the row's premise does not hold of the code, and each way of
making it hold is a rule `SPEC.md` does not state.**

**The conflict.** B1's row (`WORKPLAN.md` §1, series 2) says "`zoo capture`
picks the Collector's port, writes it into the config and launches the child",
and asks that a bind failure make it "pick again, up to N". `TASKS.md`
registers the thread the same way ("taken between the zoo's pick and the
Collector's bind"). But `zoo capture` picks nothing: the Collector's receiver
port is `--collector-port`, default `4320` (`SPEC.md` §4.6's option table),
handed unchanged to the child through `ZOO_COLLECTOR_OTLP_HTTP`
(`collector.Binary.environment`) **and**, before the launch, to the forward
(`cli.run_capture` builds `forward.HttpForward(args.host, args.collector_port)`).
The pick in the failing run was the **test harness's**: `ZooCapture` in
`tests/test_shutdown.py` calls `free_port()` (bind port 0, read it, close) for
all four ports and passes them on the command line.

**Facts gathered, so the decision need not re-gather them.**

- The CI failure (`gh run view 38273980263 --attempt 1 --log-failed`, PR run
  at `e50a56e`): `zoo capture: refusing to start: the Collector exited with 1
  before it reported ready on 127.0.0.1:43383`, the stand-in's own log ending
  `OSError: [Errno 98] Address already in use`. So it was the Collector's port,
  as registered; the refusal was the one §4.6 specifies for a held port.
- `SPEC.md` §4.6 makes a held Collector port a refusal, and
  `tests/test_capture.py::test_a_foreign_listener_on_the_collector_port_is_refused_and_writes_nothing`
  holds that for an operator-named port. A retry that moved off an
  operator-named port would turn that refusal into a success on a port the
  operator did not choose.
- `SPEC.md` §4.2: "The app's port is the one thing the zoo does not move" —
  read as permission, the Collector's port is internal and movable; read
  narrowly, it says nothing about it.
- The same harness picks the raw and json sink ports the same way, and the
  `zoo capture` subprocess binds them only after interpreter start-up, so the
  window is at least as wide for them; a retry on the Collector's port alone
  does not close the harness's race. The two readiness lines after the ready
  line already print the raw and json ports (§4.2), so a harness could pass
  `0` for those and read them back.
- Binding a probe socket to pick a port is a socket outside an injected seam
  unless a seam is added (`CLAUDE.md`, "One seam"); the forward would have to
  learn the port after the launch (e.g. from the `Running` handle) rather than
  from `args`.
- The real Collector's bind failure reads `bind: address already in use`; the
  stand-in's reads `OSError: [Errno 98] Address already in use`. "A log that
  shows the bind failure" needs a stated marker either way.

**The options, each with its cost.**

1. **`--collector-port 0` means the zoo picks**, through a new `pick` seam
   (§4.8), and only a picked port is retried: on a Collector that exits before
   ready with an address-in-use line in its log, pick again, up to N (say 5),
   and the refusal after N names every port tried. An operator-named port held
   stays the refusal it is today; the default stays `4320`. The forward takes
   the port the launcher ended on. `ZooCapture` passes `--collector-port 0`.
   Cost: a new CLI meaning and a new seam; the sink ports' harness race is
   left (or fixed in the same batch by passing `0` and reading the printed
   ports — a second concern).
2. **The zoo always picks the Collector's port** (default becomes "picked"),
   on §4.2's reading that only the app's port is fixed, with the same retry;
   `--collector-port` given explicitly disables the retry. Cost: a default
   behaviour change in §4.6's table, `--help` and the README; an operator can
   no longer predict the port without reading the ready lines.
3. **Retry on any port, explicit or not**, picking a new one after a bind
   failure. Cost: contradicts §4.6's held-port refusal and the foreign-listener
   test; the operator's choice is overridden silently. Not recommended.
4. **No product change: the race is the harness's, and is fixed there.** The
   harness lets the subprocess choose (raw and json sinks at `0`, read back
   from the printed lines) and, for the Collector port, retries the whole
   `ZooCapture` start when the refusal names an address in use, bounded.
   Cost: the maintainer's 2026-10-12 decision ("the retry is bounded and every
   port tried is named") then describes the harness, not `zoo capture`, and
   §4.6 does not change.

**The decision (2026-10-12, maintainer).** Option 4. `zoo capture` is
unchanged: it names its ports and a held one is §4.6's refusal. The harness
stops picking for the two sinks (`0`, read back from the ready lines; `0`
made acceptable for them if it is not) and retries its own start, bounded,
when the refusal names an address in use. The series-1 thread and the
2026-10-12 decision log entry are corrected to say "harness". Options 1–3
are declined: each adds a product rule for a race only the test suite runs.

## 7. B4a: the audit already refuses such a manifest, and §7.2 says a refusal writes no report

**Status: open, 2026-10-13. Asked by B4a, which stopped before writing any
code or test: the row's audit outcome contradicts `SPEC.md` §7.2, and each way
of reconciling them is a rule the spec does not state.**

**The conflict.** B4a's row (`WORKPLAN.md` §1, series 2) asks that "a manifest
with an absolute entry and one with `..` make ... `zoo audit` write an
incomplete report naming the entry". But such a manifest does not verify: B4
(`99edcbd`) made `manifest.problems` -- through `_outside`, the function the
row names as the shared check -- report an absolute, non-normalized or
symlinked-out `file` entry as a problem. And `audit.audit()` calls
`manifest.problems(run)` **first**, before any step reads a file, and refuses
on any problem, exactly as §7.2 specifies: "the run does not verify (§5.6)"
is a refusal, "exit **2**, no report written". So an incomplete report (exit
1, §7.5) for this manifest would mean the audit *not* refusing a run that does
not verify -- a change to §7.2's rule, not an application of B4's.

**Facts gathered, so the decision need not re-gather them.** Observed at
`a3daaf8` on copies of `tests/fixtures/capture` with `bodies[0].file` edited
(scratchpad, never a real capture):

- absolute entry (`/…/outside.body`): `zoo audit` exits 2, no report, and the
  refusal line's first problem is `bodies[0] is '/…/outside.body', an
  absolute path, outside the run directory (SPEC.md section 5.4)`. Nothing is
  read: the check precedes step 1.
- `..` entry (`raw/../../../outside.body`): `zoo audit` exits 2 the same way,
  naming `bodies[0] is 'raw/../../../outside.body', not a normalized relative
  path ...`.
- `zoo replay --raw`, absolute entry: exit 2, but only **by accident** -- the
  entry does not start with `raw/`, so `planned` filtered it out and the
  refusal reads "holds no body under raw/", not naming the entry.
- `zoo replay --raw`, `..` entry: the entry passes the `raw/` prefix filter and
  **is read** (`run / "raw/../../../outside.body"` is opened; here it did not
  exist, so "not sent", exit 1). This is the defect the row is about, and it is
  the replayer's alone: the replayer never calls `verify`.
- The audit's own reads (`serve` → `replay.planned`/`replay.replay`, and
  `_request` in step 3) all take their names from `replay.planned`, so a check
  in `planned` covers them too -- but behind the verify refusal that path is
  unreachable through `zoo audit`.

**The options, each with its cost.**

1. **The audit keeps §7.2; the row's audit clause reads "refuses, naming the
   entry".** `replay.planned` checks every `bodies` entry with `_outside`
   (made public in `manifest`, one function for every reader) and raises
   `ReplayRefused` naming the first bad entry, before anything is read or sent
   -- so `zoo replay` exits 2 naming it, and the audit's `serve` inherits the
   same check (defence in depth, rendered "step N not run" if ever reached).
   The audit test asserts what is true today: exit 2, no report, the refusal
   naming the entry. §5.4's "the rule exists for `zoo verify`" becomes "for
   every reader of the manifest (`verify`, `replay`, `audit`)". Cost: the
   row's "incomplete report" is corrected rather than delivered; the audit
   half of the batch adds a test, not a behaviour.
2. **A path-confinement problem is not a refusal for the audit.** The audit
   refuses on every verify problem except an entry outside the run, which
   instead makes the steps reading it "not run" and writes an incomplete
   report (exit 1). Cost: an exception in §7.2, whose reason ("an audit of
   bytes that are not the bytes recorded would be a reproduction of nothing")
   applies to this case as much as any; a report would exist for a capture
   `zoo verify` fails.
3. **The audit never refuses on verify; every verify problem becomes an
   incomplete report.** Cost: §7.2 and §7.5 both change; `make check`'s
   "an unverified capture is not audited" guarantee goes; larger than the row.

**A smaller question inside option 1.** Should `zoo replay --raw` refuse on a
bad entry under `json/` (the side it is not sending)? (a) Yes -- any bad
`bodies` entry makes the manifest one this cannot replay honestly, as it makes
it one `verify` fails; (b) no -- only the entries it would read. (a) is the
simpler rule and the one `verify` already follows.

**Recommended:** option 1, with (a). It is B4's rule applied to the one reader
that lacks it, and it leaves §7.2's refusal, which already names the entry and
reads nothing, standing.

**The decision (2026-10-13, maintainer).** Option 1. The audit keeps §7.2 and
its test asserts the refusal names the entry; `zoo replay` gets B4's check on
both sides of the manifest, and refuses before sending. Options 2 and 3 are
declined: an incomplete report for a manifest `verify` rejects would have the
audit read what `verify` would not, and every verify failure as an
incomplete report would make the audit a second `verify` with a worse
answer.
