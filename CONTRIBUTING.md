# Contributing to spanweave-zoo

Work here lands in **batches**: one batch is one concern and one commit, listed
in `WORKPLAN.md` while a series is open and in `TASKS.md` afterwards. This file
is the bar a batch clears. `CLAUDE.md` is the contract it must not violate;
`SPEC.md` is what to build.

## Before you write code

Read, in order: `CLAUDE.md` (the standing rules, §0.6), the `WORKPLAN.md` row
for your batch and §5, then the `SPEC.md` sections that row names, then only
the source and test files the batch touches.

The standing rules are non-negotiable and a change that violates one is wrong
even if it passes tests. In particular: **the zoo records and never improves**,
**a capture is immutable**, **the sink parses nothing**, and **a finding is a
reproduction, never a fix**.

## The bar

A batch is done when all of this is true:

- [ ] **Spec first.** `SPEC.md` describes the behaviour, edited in the *same*
      commit as the code. A section belonging to a later batch stays an empty
      heading; it is never pre-specified.
- [ ] **A failing test, written before the fix, and confirmed red on the
      parent.** The parent is `<sha>^` **derived** — never a sha a brief
      names, because `plan:` commits interleave and a named sha goes stale.
      Check it out in a worktree created by **absolute path under the
      scratchpad** (`git worktree add /abs/path/under/scratchpad <sha>^`),
      never a relative path and never a path inside the repo: a worktree
      inside the repo is picked up by `ruff`, `mypy` and `pytest`, and the run
      you were trying to read becomes a run of two copies of the suite.
- [ ] **One named mutation, shown caught.** Name a specific wrong
      implementation the new test rejects, make that change, paste the
      failure, revert it. This is required for *every* code commit and not
      only where the parent run is informative: a tests-only batch's derived
      parent is often a `plan:` commit, which makes the parent run vacuous,
      and a mutation is what distinguishes a test that holds the behaviour
      from a test that merely runs.
- [ ] **One concern per commit.** `<area>: <one line>`, with a body naming the
      batch id and the `SPEC.md` sections touched. A drive-by fix noticed on
      the way is a second commit, or a line in `OPEN_QUESTIONS.md`.
- [ ] **A `CHANGELOG.md` entry**, under the batch id.
- [ ] **`make check` green and `make verify` green.** `make install-check` too
      for anything that touches packaging, the CLI or the console script. CI
      runs all three.
- [ ] **CI green on the pushed tip.** The matrix runs interpreters and an
      operating system your machine does not have; a local `make check` is not
      a substitute.
- [ ] **No test whose result depends on what happens to be installed.** The
      `audit` extra is not installed by `make check` or by CI, and a test that
      silently skips when `spanweave` is absent is green everywhere it cannot
      catch anything. Assert the branch you mean, and drive it from the test.
- [ ] **No clock, no randomness, no socket outside an injected seam.** A test
      that reads the real time is a test that fails on a slow machine next
      year.

## Halt points

Some work is a decision, not a patch. Stop, write the options to
`OPEN_QUESTIONS.md` under a heading naming your batch, commit that alone, and
report `awaiting decision` — rather than choosing — if the batch would need a
change in `spanweave` or `spanweave_live`, a runtime dependency, a move of
either pinned sha, parsing a payload outside the Collector, a change to a
capture that already exists, or any rule `SPEC.md` and `CLAUDE.md` do not
already state. `CLAUDE.md`, "Halt points", is the list.

## Captures

A capture is a record and is never edited. Not to redact it, not to fix a
truncated body, not to make a test pass. If a capture must change, it is a new
capture with a new `<run-id>` and a manifest that says what it is
(`SPEC.md` §2).

`EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` are the record too: byte-identical to
what the pet projects were handed, with their sha256s in `README.md`. They are
not reflowed, re-indented or corrected here — a correction is a new contract
version, issued where contracts are issued, and the root copies then move with
their hashes and the README's provenance note in one commit.

## Findings

An audit finding is a **reproduction**: the capture path, the exact command,
the observed result, the expected result, and the repository that owns the
defect. It is never a fix, and never a workaround in the sink or the replayer
that would make the next capture lie. Fixes happen in the owning repository's
own series, where they get a commit and a test.
