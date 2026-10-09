# spanweave-zoo

**A recorder for what real OTLP exporters actually send.**

Small AI agents are built elsewhere, by implementers who know nothing about
what consumes their telemetry, under stock instrumentation
(`EXPORT-CONTRACT.md`, `ZOO-BRIEFS.md`). This repository is the other side of
that: a sink that writes down the bytes each exporter POSTs, a stock
OpenTelemetry Collector that re-encodes those bytes to JSON *beside* them, a
replayer that sends them again exactly as received, and an audit that runs
[`spanweave`](https://github.com/SigorMatt/spanweave) and
[`spanweave-live`](https://github.com/SigorMatt/spanweave-live) over every
capture and writes down what happened.

**The zoo parses nothing, fixes nothing, and improves nothing** (`SPEC.md` §1).
A capture is a record: the bytes as received, the request headers beside them,
a sha256 of every body in `MANIFEST.json`. When a receiver refuses a capture,
that refusal is a finding -- reported against the repository that owns it, in
its own series -- and never something the zoo works around.

## Pre-release: nothing here is frozen

Version `0.0.1`. The CLI, the capture layout and the shape of `MANIFEST.json`
are all unfrozen and will change. The one thing meant to be durable is the
*bytes* of a capture, and `zoo verify` is what makes that checkable.

## What exists today

| | |
|---|---|
| `zoo --help`, `zoo verify` | the entry point, and the capture re-hash |
| `SPEC.md` §1, §2 | the non-goals, and the capture layout on disk |
| `SPEC.md` §§3-7 | headings only: the sink, the Collector, the manifest, the replayer, the audit |

The subcommands those sections name (`sink`, `capture`, `replay`, `audit`) are
not implemented and are not stubbed. `zoo verify` today exits 0 on a tree with
no captures and **fails** on a capture it cannot yet re-hash, rather than
reporting an unchecked capture as verified.

## Running the gates

Tooling is [`uv`](https://docs.astral.sh/uv/). From a checkout:

```bash
uv sync --extra dev        # ruff, mypy, pytest -- and nothing else
make check                 # THE gate: lint, mypy --strict, pytest, the gate, zoo verify
make verify                # re-hash every capture on its own
make install-check         # build the wheel, install it, run `zoo --help` from outside the repo
```

`make check` never installs the `audit` extra, and neither does CI. That extra
pins `spanweave` and `spanweave-live` by git sha and is needed by the audit
alone; everything else in this repository works without them, and a gate
(`tests/gates.py`) fails the build if any module under `spanweave_zoo/` other
than `audit.py` imports either.

## Provenance of the contract and the briefs

`EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root are the documents handed
to the pet projects, byte for byte. They are the record: nothing here reflows
them, re-indents them or fixes them.

```
aeadb64bb5fa31495d63c397200f58a9696a5f47e44d458ec27f035c2ae302b4  EXPORT-CONTRACT.md
c82487fd275d1a0d365ff43134f03ff527e201091a39154f336bd01548095a70  ZOO-BRIEFS.md
```

Both root copies are **contract version 1.1**.

The pilot project **Z4 (`streaming-concierge`) was built against version 1.0**,
which is 1.1 minus the changes the contract lists in its own closing
*"Changes from 1.0"* section -- read that section for the difference rather
than any paraphrase of it, here or elsewhere. So for Z4, and for Z4 only, the
root copy is a later revision than the one its implementer held; its own
`MANIFEST.json` records `1.0`, which is the contract's instruction ("Put the
version you were given in `MANIFEST.json`") and is how a capture stays
readable against what was actually asked for.

For **every project started from now on**, these two files are byte-identical
to the ones handed to the project, and the sha256s above are how that is
checked.

## Layout

```
captures/<project>/<run-id>/raw/NNNN.body          the bytes as received
captures/<project>/<run-id>/raw/NNNN.headers.json  the request, verbatim
captures/<project>/<run-id>/json/NNNN.json         the Collector's re-encoding
captures/<project>/<run-id>/MANIFEST.json          what this capture is, and its hashes
```

`SPEC.md` §2 is the authority on that tree; this is a map of it.

## The contract for working here

`CLAUDE.md` is the operating contract -- the standing rules, and the lines a
change must not cross. `CONTRIBUTING.md` is the bar a batch clears.
`SPEC.md` is what to build. `CHANGELOG.md` is what landed.
