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
