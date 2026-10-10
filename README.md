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
| `zoo sink` | records every POST's bytes and headers, and parses nothing |
| `zoo capture` | the tee: the raw sink, the stock Collector behind it, the json sink |
| `zoo verify` | re-hashes a capture against its `MANIFEST.json`, both directions |
| `collector/` | the pinned Collector's version, digests and config -- `make collector` fetches the binary |
| `SPEC.md` §1-§5 | the non-goals, the layout, the sink, the Collector and the tee, the manifest |
| `SPEC.md` §§6-7 | headings only: the replayer, the audit |

The subcommands those later sections name (`replay`, `audit`) are not
implemented and are not stubbed.

```bash
zoo sink --port 4318 --out captures/z4/2026-10-09T12-00-00Z/raw
```

Every `POST /v1/traces` becomes `raw/NNNN.body` -- the bytes exactly as
received, **still gzipped if they arrived gzipped** -- beside
`raw/NNNN.headers.raw`, the octets of the request's head as they arrived, and
`raw/NNNN.headers.json`, the stdlib's parse of that same head; it is answered
`200` with an empty body. A POST to any other path is answered `404` and
recorded anyway, under `rejected/`: an
exporter aimed at the wrong endpoint is exactly the kind of fact this
repository exists to hold. The sink never decodes, decompresses or parses, and
its `200` means "recorded", never "understood" (`SPEC.md` §3).

### The tee

```bash
make collector                                   # fetch the pinned binary, sha256 checked
zoo capture --project z4 --run-id 2026-10-09T12-00-00Z
```

One run, three listeners: the **raw sink on 4318** -- the port every pet
project was given -- the stock **OpenTelemetry Collector** behind it, and a
**json sink on 4319** where the Collector's JSON re-encoding lands. The raw
sink writes the body to disk and *then* forwards the same bytes, unchanged, to
the Collector: the record is made first and the convenience second. If the
Collector is down, the capture is still a capture and `MANIFEST.json` says
which bodies never reached it (`SPEC.md` §4).

The capture directory is created **last**: all three listeners accept and the
Collector has logged its own ready line before anything is written, and then
`zoo capture` prints one line -- `the raw bytes are the record. Ctrl-C to
stop.` A refusal before that names the port or the cause, exits 2 and leaves
nothing behind, so a capture directory means a capture was made (`SPEC.md`
§4.6).

The Collector is **stock**, pinned in `collector/VERSION`, with its sha256 in
`collector/SHA256SUMS` and its config checked in at `collector/config.yaml`.
`make collector` downloads exactly that release and refuses to unpack anything
else; the ~100 MB binary is gitignored, because the pin is the record and the
bytes are a download. `zoo capture` refuses to start if the binary reports a
version that is not the pin.

### The manifest, and `zoo verify`

Every run directory holds one `MANIFEST.json` saying what the capture is: the
pet project's own `MANIFEST.json` copied **verbatim** (`EXPORT-CONTRACT.md`
§1), the zoo's `sink_version` and the Collector's pinned `collector_version`,
`kind` (`recorded` or `real`), `started_at` / `ended_at`, one `bodies` entry
per recorded body with its `sha256`, `bytes` and the `content_type` /
`content_encoding` the request declared, one `files` entry with a `sha256` for
**every other file in the run directory** — the headers files and the run's
journals included — and one `forwards` entry per attempt to reach the Collector
(`SPEC.md` §5).

Bodies are written down in `bodies.jsonl` as they land, one flushed line each,
and the document is assembled once when the run ends: so recording the
sixteen-hundredth export costs what recording the first did, and `zoo verify`
re-hashes the whole capture rather than the part of it that is bodies. A
capture with no `ended_at` was never completed and does not verify; neither
does one whose manifest records a `problem`.

**`--kind` is required and is never inferred.** A recorded capture and a real
one differ by that declaration alone -- the bytes look the same -- and the
audit reads it as the truth, so the zoo refuses the command rather than
guessing. The project's own manifest is **copied, not merged and not
validated**: no field of it is read, and if its `mode` disagrees with `--kind`,
both declarations sit in the record and a reader can see the disagreement. The
zoo records; improving the record is the one thing it must not do.

```bash
zoo verify                                      # every capture under captures/
zoo verify captures/z4/2026-10-09T12-00-00Z     # one run
```

`zoo verify` exits 0 on a tree with no captures -- the default `captures/`,
which this repository's own is -- and **2, naming the path**, on a path you
typed that is not a capture: an absent directory, a file, or a directory with
no run in it. Nothing was checked, and a typo must not read as a clean bill of
health. Otherwise it checks **both
directions**: every body the manifest lists is on disk with the sha256 and the
length it recorded, **and** every file on disk is one the manifest accounts
for. It fails on a changed byte, a stale digest, a missing body, a **body the
manifest never listed**, and a manifest it cannot read -- rather than reporting
an unchecked capture as verified. The second direction is why it walks the
directory and not only the list: a check that iterated the manifest could never
notice a body nobody recorded.

`make verify` runs it over `captures/` and then over
`tests/fixtures/capture/`, which holds one real capture -- a single OTLP
protobuf body through the real tee, both sides, headers and manifest -- so the
gate re-hashes bytes on every run and in CI rather than reporting an empty
tree. It is a capture: it is never edited and never regenerated.

## Running a pet project's real run

**Five commands, in two terminals.** `z4` (`streaming-concierge`) is the pilot;
`<run-id>` is yours to choose, a run directory is never reused, and a timestamp
reads well a month later.

In the zoo's checkout, after `uv sync --extra dev` once (the `uv run` prefix
is what makes these typeable from a bare checkout; drop it if `.venv` is
activated):

```bash
make collector
```

```bash
uv run zoo capture --project z4 --run-id 2026-10-10T09-00-00Z \
                   --kind real \
                   --project-manifest ../streaming-concierge/MANIFEST.json
```

In the pet project's checkout, in a second terminal, once the capture says it
is recording:

```bash
make run-real ENDPOINT=http://localhost:4318
```

Back in the first terminal, once the project's run has exited:

```
Ctrl-C
```

```bash
make verify
```

That is the whole flow. What each command is for:

1. **`make collector`** downloads the pinned Collector and checks its sha256
   against the release's own digest. Once per machine; `zoo capture` refuses to
   start if the binary is missing or is not the pin.
2. **`zoo capture`** brings up the raw sink on **4318** -- the port every brief
   gave the pet projects -- the Collector behind it, and the json sink the
   re-encoding lands in. It prints one line per recorded body as it arrives.
   `--kind real` is the declaration the audit keys off and has no default;
   `--project-manifest` is the project's own `MANIFEST.json`, copied into the
   capture verbatim. Both are checked **before** anything is recorded.
3. **`make run-real ENDPOINT=...`** is the project's own command
   (`EXPORT-CONTRACT.md` §1). The zoo does not run the project, know its
   dependencies, or care what it does -- it is a recorder, and the project
   knows nothing about it either.
4. **Ctrl-C** ends the capture: it stops the raw sink, lets the Collector flush
   its last batch, stops the json sink, completes `MANIFEST.json` and prints
   what it recorded. `SIGTERM` does the same, so a supervisor can end a run.
   The exit status is non-zero if any body failed to reach the Collector, if the
   Collector exited during the run, or if the project's own `MANIFEST.json`
   could not be copied -- the capture is intact either way and the manifest
   says what happened.
5. **`make verify`** re-hashes every capture under `captures/`, and the
   committed one under `tests/fixtures/capture/`, against its manifest. `make
   check` depends on it, so from now on every run of the gates re-checks this
   capture's bytes. `uv run zoo verify captures/z4/<run-id>` re-hashes just
   this one, and exits 2 if that path is not a capture.

Two things to know before you start, both of which are refusals rather than
surprises:

- **The project's `MANIFEST.json` must exist when the capture starts, and the
  copy is taken when it ends.** The contract has the project write it *while it
  runs* (`EXPORT-CONTRACT.md` §1), so the path is checked at the start -- a
  typo is refused while nothing is on disk -- and the document is copied after
  Ctrl-C, which is when the file is the recorded run's rather than its
  predecessor's. If the project's own run did not write one, or wrote one dated
  before the capture started, the capture carries none, says why in `problems`,
  exits non-zero and does not verify (`SPEC.md` §5.3).
- **A run directory is never reused.** A second attempt is a second
  `--run-id`; pointing a capture at a directory that already holds part of one
  is refused by name, because the fix for a half-recorded run is another run,
  never an edited capture.

A **recorded** run is the same five commands with `--kind recorded` and the
project's `make run-recorded`. Nothing else changes -- which is exactly why
`kind` is a declaration and not something the zoo works out for itself.

## Running the gates

Tooling is [`uv`](https://docs.astral.sh/uv/). From a checkout:

```bash
uv sync --extra dev        # ruff, mypy, pytest -- and nothing else
make check                 # THE gate: lint, mypy --strict, pytest, the gate, zoo verify
make verify                # re-hash every capture on its own
make install-check         # build the wheel, install it, run `zoo --help` from outside the repo
make collector             # fetch the pinned Collector (not a prerequisite of anything)
```

`make check` is green **with and without** `collector/otelcol-contrib` on
disk. The one test that runs the real Collector -- a protobuf export through
the tee, asserted to come back as JSON with the same span ids -- is skipped
when the binary is absent, which is how it behaves in CI: nothing in CI
downloads 100 MB. It skips loudly rather than passing quietly (`SPEC.md` §4.9).

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
checked -- recomputed from the files on disk by `tests/test_readme.py` on every
`make check`, so a digest printed here and a document edited cannot drift apart
quietly.

## Layout

```
captures/<project>/<run-id>/raw/NNNN.body          the bytes as received
captures/<project>/<run-id>/raw/NNNN.headers.raw   the head, octet for octet
captures/<project>/<run-id>/raw/NNNN.headers.json  the parse of that head
captures/<project>/<run-id>/json/NNNN.json         the Collector's re-encoding
captures/<project>/<run-id>/rejected/NNNN.body     a POST aimed at another path
captures/<project>/<run-id>/bodies.jsonl           each body as it was recorded
captures/<project>/<run-id>/forwards.jsonl         each forward as it completed
captures/<project>/<run-id>/MANIFEST.json          what this capture is, and its hashes
```

`SPEC.md` §2 is the authority on that tree; this is a map of it.

## The contract for working here

`CLAUDE.md` is the operating contract -- the standing rules, and the lines a
change must not cross. `CONTRIBUTING.md` is the bar a batch clears.
`SPEC.md` is what to build. `CHANGELOG.md` is what landed.
