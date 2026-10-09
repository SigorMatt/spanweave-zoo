# CLAUDE.md — operating contract

This file governs how Claude Code works in this repo. Read it at the start of
every session, in full. `SPEC.md` is the source of truth for *what* to build;
this file is the source of truth for *how*, and for the lines that must never
be crossed. A cold session should be able to work here from this file alone.

While a series is open there is also a `WORKPLAN.md` — the orchestrator's
execution state: which batch is next and what it must contain. **It is edited
only by the orchestrator**, and a sub-agent executing a batch never edits it.
It exists only for the life of a series and is deleted at the close, with §3
(the decisions log) folded into `TASKS.md`, which is the registry **between**
series: one line per batch with the commit that closed it.

## What this project is

A **recorder**. Pet projects — small, ordinary AI agents built elsewhere by
implementers who know nothing of what consumes their telemetry — run under
stock instrumentation and export over OTLP. This repository writes down what
they send: a sink that stores each POST's bytes and headers, a stock
OpenTelemetry Collector that re-encodes those bytes to JSON beside them, a
replayer that sends them again exactly as received, and an audit that runs
[`spanweave`](https://github.com/SigorMatt/spanweave) and
[`spanweave-live`](https://github.com/SigorMatt/spanweave-live) over every
capture and writes down what happened.

It is not an analyzer, not a receiver, not a service, not a test suite for
someone else's library. `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` are what the
implementers were handed, kept here byte for byte as the record
(`README.md`, "Provenance").

## 0.6 Standing rules — non-negotiable

These are `WORKPLAN.md` §0.6, which is where they were first written, repeated
here because they are the contract and a session must not have to read the plan
to find them. A change that violates one is wrong even if it passes tests.

1. **The zoo captures what exporters send and never improves it.**
   (`SPEC.md` §1.)

2. **A capture is immutable**: bytes as received, with the request headers
   beside them and a sha256 of each body in the manifest. `zoo verify`
   re-hashes every capture and `make check` fails if any differs.

3. **The sink parses nothing** and answers every POST the same way.

4. **The Collector is the stock OpenTelemetry Collector** at a pinned version
   with a checked-in config, and its JSON re-encoding is kept *beside* the raw
   bytes, never instead of them.

5. **The replayer re-sends bytes and headers as captured and adds nothing.**

6. **Nothing under `spanweave_zoo/` imports `spanweave` or `spanweave_live`
   except the audit module**, and a gate holds that (`tests/gates.py`).

7. **An audit finding is a reproduction** — a capture, a command, an observed
   and an expected result — **never a fix**: fixes belong to the repo that owns
   the defect, in its own series.

8. **`spanweave` and `spanweave-live` are pinned by git sha** in
   `pyproject.toml` and used only by the audit batch; the sink, the Collector
   config and the replayer import neither.

## Architecture invariants

- **One seam between the world and the record.** The clock, sleeping and
  sockets are injected: a `now`, a `sleep`, a listener factory, named by the
  spec section that introduces them. No module under `spanweave_zoo/` reads the
  clock, draws a random number or binds a socket outside such a seam, so every
  test runs on a fake clock and a captured timestamp is a value a test chose.
- **Honest refusal beats a reassuring pass.** A command that cannot check what
  it was asked to check exits non-zero and says what is missing. `zoo verify`
  on a capture it cannot yet re-hash fails; it does not report the capture as
  verified.
- **Nothing is frozen.** Pre-release, and the version number and the
  `Development Status :: 3 - Alpha` classifier are where a tool reads that. The
  CLI, the capture layout and `MANIFEST.json` all still move. The *bytes* of a
  capture do not.
- **Zero runtime dependencies.** The sink is `http.server`, the manifest is
  `json`, the hashes are `hashlib`. The `audit` extra is the only dependency
  declaration, and it is A5's alone. Adding a runtime dependency is a halt
  point.

## Working agreement

- **Spec-first.** If the behaviour isn't in `SPEC.md`, update `SPEC.md` in the
  same commit as the code. A section belonging to a later batch stays an empty
  heading rather than a guess.
- **One batch, one commit, one concern.** `<area>: <one line>`, with a body
  naming the batch id and the `SPEC.md` sections touched.
- **Failing test first.** Write it, and confirm it red on the derived parent
  (`<sha>^`) in a worktree created by **absolute path under the scratchpad** —
  never relative, never inside the repo. Then name one mutation the test
  catches and show it caught. `CONTRIBUTING.md` is the full bar.
- **Degenerate captures matter as much as clean ones.** A body no receiver
  accepts, a truncated export, a missing `json/`, two POSTs in flight: each
  needs a test proving the zoo records it honestly rather than tidying it.
- **A finding names its owner.** Never fix another repository's defect from
  here, and never work around it in a way that makes the capture lie.

## Coding conventions

- Python 3.11+, fully type-annotated. `ruff` + `mypy --strict` clean. `pytest`.
- Tooling is `uv`. The `Makefile` is the source of truth for the gates.
- Serialization uses stdlib `json` with `sort_keys=True`.
- No `pickle`, `yaml.load`, `eval`, `exec` — trace payloads are untrusted
  input, and this repository's whole business is holding bytes it does not
  trust.
- Public surface is the `zoo` CLI. Everything under `spanweave_zoo/` other than
  `cli.py`'s entry point is internal and may be refactored freely.

## Halt points

Stop, write the options to `OPEN_QUESTIONS.md` under a heading naming the
batch, commit that alone, and report `awaiting decision` — rather than
deciding — when completing a batch would require:

- a change in `spanweave` or `spanweave_live`;
- a runtime dependency, or a change to either pinned sha;
- parsing a payload anywhere outside the Collector;
- editing, repairing or regenerating a capture that already exists;
- a rule or a policy `SPEC.md` and this file do not already state.

## Definition of done (per change)

- [ ] `SPEC.md` reflects the behaviour, in this commit.
- [ ] A test that was red on the derived parent, plus one mutation shown caught.
- [ ] At least one degenerate case covered.
- [ ] `make check` green, `make verify` green, `make install-check` green.
- [ ] `CHANGELOG.md` entry.
- [ ] CI green on the pushed tip — the matrix runs interpreters this machine
      does not have, so a local `make check` is not a substitute.
