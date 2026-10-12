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
| `zoo replay` | sends a capture's bodies to another receiver, exactly as captured |
| `zoo verify` | re-hashes a capture against its `MANIFEST.json`, both directions |
| `zoo audit` | runs a capture through `spanweave-live serve`, `spanweave` and `agentgolden`, and writes down what broke |
| `collector/` | the pinned Collector's version, digests and config -- `make collector` fetches the binary |
| `audit/` | one report per audited capture, `<project>-<run-id>.md` |
| `PROBES.md` | the audit's findings, consolidated: each owning repository's next-series probes, with capture and command |
| `SPEC.md` §1-§7 | the non-goals, the layout, the sink, the Collector and the tee, the manifest, the replayer, the audit |

Every command printed in this README is **complete as printed**: no block here
needs a flag the prose introduces later, and the `uv run` prefix is what makes
one typeable in a bare checkout once `uv sync --extra dev` has run (drop the
prefix if you activate `.venv` yourself). `tests/test_readme.py` parses each one
with the real argument parser on every `make check`, so a command that stopped
running would fail the gates rather than wait for a reader to find it.

```bash
uv run zoo sink --port 4318 --out captures/z4/2026-10-09T12-00-00Z/raw
```

Every `POST /v1/traces` becomes `raw/NNNN.body` -- the bytes exactly as
received, **still gzipped if they arrived gzipped** -- beside
`raw/NNNN.headers.raw`, the octets of the request's head as they arrived, and
`raw/NNNN.headers.json`, that same head split on CRLF; it is answered
`200` with an empty body. A POST to any other path is answered `404` and
recorded anyway, under `rejected/`: an
exporter aimed at the wrong endpoint is exactly the kind of fact this
repository exists to hold. The sink never decodes, decompresses or parses, and
its `200` means "recorded", never "understood" (`SPEC.md` §3).

### The tee

```bash
make collector                                   # fetch the pinned binary, sha256 checked
uv run zoo capture --project z4 --run-id 2026-10-09T12-00-00Z \
                   --kind recorded \
                   --project-manifest ../streaming-concierge/MANIFEST.json
```

One run, three listeners: the **raw sink on 4318** -- the port every pet
project was given -- the stock **OpenTelemetry Collector** behind it, and a
**json sink on 4319** where the Collector's JSON re-encoding lands. The raw
sink writes the body to disk and *then* forwards the same bytes, unchanged, to
the Collector, under the head it recorded -- the octets, with only the `Host`
line and the hop-by-hop lines changed, never the stdlib's parse of them: the
record is made first and the convenience second. If the
Collector is down, the capture is still a capture and `MANIFEST.json` says
which bodies never reached it (`SPEC.md` §4).

The capture directory is created **last**: all three listeners accept and the
Collector has logged its own ready line before anything is written, and then
`zoo capture` prints the readiness line -- `zoo capture: the raw bytes are the
record. Ctrl-C to stop.` -- followed by two more: the raw sink's address and
the `raw/` it writes to, and the Collector's version with the `json/` its
re-encoding lands in and the json sink's address. A refusal before that names
the port or the cause, exits 2 and leaves nothing behind, so a capture
directory means a capture was made (`SPEC.md` §4.6).

None of the Collector's own lines reach the terminal. Its stdout and stderr go,
byte for byte, to `collector.log` in the run directory -- the lines from before
readiness included -- which is listed and hashed in `MANIFEST.json` like every
other file (`SPEC.md` §4.2).

The Collector is **stock**, pinned in `collector/VERSION`, with its sha256 in
`collector/SHA256SUMS` and its config checked in at `collector/config.yaml`.
`make collector` downloads exactly that release and refuses to unpack anything
else; the ~100 MB binary is gitignored, because the pin is the record and the
bytes are a download. The archive is kept in `collector/.cache/` so a second
run does not fetch it again -- and re-hashed on every run, so a cached archive
whose digest is not the pin is refused exactly as a bad download is. `zoo capture` refuses to start if the binary reports a
version that is not the pin.

### The replayer

```bash
uv run zoo replay captures/z4/2026-10-09T12-00-00Z --to http://127.0.0.1:8080
uv run zoo replay captures/z4/2026-10-09T12-00-00Z --to http://127.0.0.1:8080 --json --timing
```

Sends every body of a capture to another receiver **with its captured head**,
in receipt order, adding nothing (`SPEC.md` §6). `--raw` (the default) sends the
bytes the exporter sent; `--json` sends the Collector's re-encoding of them.
The head is `NNNN.headers.raw` -- the octets, not the parse beside them --
written onto the socket as it arrived with only its `Host` line changed, so a
request the stdlib could not represent goes out as it arrived, never tidied
into one it can. `--timing` sleeps the recorded inter-arrival gaps, so the receiver
sees the pattern the exporter had.

**A send that does not succeed never stops the rest.** Every remaining body
still goes out and the exit status says afterwards: **1** if any answer was not
a 2xx or any body could not be sent, **2** if nothing was sent at all -- a path
that is not a capture, or no body on the side you asked for. A `415` on a
protobuf body is an answer and a finding, not an error, and what it *means* is
the audit's to write down. The last line counts the bodies a receiver answered
as sent, and the rest as not sent: `zoo replay: 1 sent, 1 that did not answer
2xx, 1 not sent`.

### The audit

```bash
uv sync --extra dev --extra audit
uv run zoo audit captures/z4/2026-10-12-real
```

The only subcommand that needs the `audit` extra: `spanweave`, `spanweave-live`
and `agentgolden`, each pinned by git sha in `pyproject.toml` (`SPEC.md` §7).
It refuses a capture that does not verify and a library installed at any
commit but its pin, then replays the capture into a real `spanweave-live
serve` -- the exporter's bytes, then the Collector's JSON -- compares every
graph `serve` wrote with `spanweave.build` of the same records, runs
`spanweave inspect` and `agentgolden`'s signature on each, and writes
`audit/<project>-<run-id>.md`. Every finding in it is a reproduction -- the
capture, the commands, what was observed and what was expected -- and names
the repository that owns it. Nothing is fixed here.

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
uv run zoo verify                                      # every capture under captures/
uv run zoo verify captures/z4/2026-10-09T12-00-00Z     # one run
```

`zoo verify` exits 0 on a tree with no captures -- the default `captures/`,
in a checkout that holds none -- and **2, naming the path**, on a path you
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
tree. It is a capture: it is never edited. It has been regenerated, each time
as a new run through the same tee, when a ratified rule changed what a capture
carries -- the seal, then the request line in `headers.json` (`SPEC.md`
§5.6); the zoo's own captures under `captures/` never are.

## Running a pet project's real run

`z4` (`streaming-concierge`) is the pilot; `<run-id>` is yours to choose, a run
directory is never reused, and a timestamp reads well a month later. The steps
below are numbered in the order they are typed, and each command is complete as
printed -- the list *is* the flow, and there is no shorter form of any of these
that runs. Two terminals: every step is in the zoo's checkout except **4**,
which is in the pet project's.

**1. In the zoo's checkout -- install the tooling.**

```bash
uv sync --extra dev
```

Once per checkout. It installs ruff, mypy and pytest and nothing else; the
`audit` extra is A5's and no part of this flow needs it. Every `uv run` below
depends on this having run.

**2. In the zoo's checkout -- fetch the pinned Collector.**

```bash
make collector
```

Downloads the pinned release and checks its sha256 against the pin
checked in at `collector/SHA256SUMS`; a second run uses the archive cached in
`collector/.cache/`, re-hashed against the same pin, instead of fetching it
again. Once per checkout -- the binary lands in this checkout's `collector/`;
`zoo capture` refuses to start if the binary is missing or is not the pin.

**3. In the zoo's checkout -- start the capture, and leave it running.**

```bash
uv run zoo capture --project z4 --run-id 2026-10-10T09-00-00Z \
                   --kind real \
                   --project-manifest ../streaming-concierge/MANIFEST.json
```

Brings up the raw sink on **4318** -- the port every brief gave the pet
projects -- the Collector behind it, and the json sink the re-encoding lands
in. It prints one line per recorded body as it arrives, flushed as it is
printed -- one for the exporter's body in `raw/` and one for its re-encoding
in `json/`, so a single export prints two. `--kind real` is the declaration
the audit keys off and has no default; `--project-manifest` is the project's
own `MANIFEST.json`, copied into the capture verbatim. Both are **required**, and the path is checked before
anything is recorded.

Wait for the one readiness line -- `zoo capture: the raw bytes are the record.
Ctrl-C to stop.` -- before going on to step 4: until it prints, the capture
directory does not exist and nothing would be recorded (`SPEC.md` §4.6). A
supervisor can wait on it instead of a human watching the terminal:

```bash
uv run zoo capture --project z4 --run-id 2026-10-10T09-00-00Z \
                   --kind real \
                   --project-manifest ../streaming-concierge/MANIFEST.json \
                   > "${TMPDIR:-/tmp}"/zoo-capture-2026-10-10T09-00-00Z.log 2>&1 &
timeout 60 bash -c 'until grep -q "^zoo capture: the raw bytes are the record" "${TMPDIR:-/tmp}"/zoo-capture-2026-10-10T09-00-00Z.log; do sleep 0.1; done'
```

Grep the log rather than the pipe, and anchor it: `recording POST /v1/traces on
http://127.0.0.1:4318` is printed by `zoo sink` as well, so an unanchored match
can be satisfied by the wrong process. The log goes outside the checkout and
outside the run directory, never into either: a file in the run directory is
hashed into the manifest before `zoo capture` prints its last line into it,
and a redirect there would create the directory before readiness. The
operator log is not part of the record, because `collector.log` is.

**4. In the pet project's checkout, in a second terminal -- make its run.**

```bash
make run-real ENDPOINT=http://localhost:4318
```

The project's own command (`EXPORT-CONTRACT.md` §1). The zoo does not run the
project, know its dependencies, or care what it does -- it is a recorder, and
the project knows nothing about it either.

`make run-real` reads the model's key from the environment of **this**
terminal (`EXPORT-CONTRACT.md` §4): for z4 that is `OPENAI_API_KEY`, with
`OPENAI_BASE_URL` honoured if set (z4's own README). Export it here before
typing the command. Without it `make run-real` exits 2 before it exports
anything -- and the capture in the first terminal has then spent its run id on
a run that recorded nothing, because a run directory is never reused.

**5. Back in the first terminal, once the project's run has exited -- end the
capture.**

```
Ctrl-C
```

A keystroke rather than a command, and the only one in the flow. It stops the
raw sink, lets the Collector flush its last batch, stops the json sink,
copies the project's `MANIFEST.json`, completes the capture's own and prints
what it recorded, counted by side -- `zoo capture: 1 body/bodies in raw/, 1 in
json/, under captures/z4/2026-10-10T09-00-00Z/, MANIFEST.json written:
kind=real` for one export. The Collector runs in a session of its own, so the
terminal's Ctrl-C reaches the zoo and not the Collector, and the zoo stops it:
it prints `zoo capture: stopping`, then the summary, and a clean run exits
**0** and leaves no Collector running. `SIGTERM` does the same, so a
supervisor can end a run, and so does `SIGHUP` -- the terminal closed or the
ssh session dropped -- so losing the first terminal still completes the
capture and stops its Collector. `SPEC.md` §4.2 lists every line `zoo
capture` prints. The exit status is non-zero if any body
failed to reach the Collector, if the Collector exited during the run, or if
the project's own `MANIFEST.json` could not be copied -- the capture is intact
either way and the manifest says what happened.

The project's `make run` rewrites its own `MANIFEST.json` in its checkout
every time (`EXPORT-CONTRACT.md` §1), so step 4 leaves that file modified
there. The capture already holds the copy it took; the operator does not
commit the pet project's checkout.

**6. In the zoo's checkout -- re-hash what was recorded.**

```bash
make verify
```

Re-hashes every capture under `captures/`, and the committed one under
`tests/fixtures/capture/`, against its manifest. After a clean run it is
green with the new capture present, and so is `make check`, which depends on
it -- so from then on every run of the gates re-checks this capture's bytes.
For just this run:

```bash
uv run zoo verify captures/z4/2026-10-10T09-00-00Z
```

which exits 2 if that path is not a capture.

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

A **recorded** run is the same steps with `--kind recorded` at step 3 and the
project's `make run-recorded` at step 4. Nothing else changes -- which is why
`kind` is a declaration and not something the zoo works out for itself.

## Running the gates

Tooling is [`uv`](https://docs.astral.sh/uv/). From a checkout:

```bash
uv sync --extra dev        # ruff, mypy, pytest -- and nothing else
make check                 # THE gate: lint, mypy --strict, pytest, the gate, zoo verify
make verify                # re-hash every capture on its own
make install-check         # build the wheel, install it, run `zoo --help` from outside the repo
make collector             # fetch the pinned Collector (not a prerequisite of anything)
make collector-check       # the Collector tests ran, and not one of them skipped
make audit-check           # install the audit extra; the audit tests ran, none skipped
```

`make check` is green **with and without** `collector/otelcol-contrib` on
disk. The tests that run the real Collector -- a protobuf export through the
tee, asserted to come back as JSON with the same span ids -- are skipped when
the binary is absent, which is how they behave on CI's five `check` legs: none
of them downloads 100 MB. They skip loudly rather than passing quietly
(`SPEC.md` §4.9).

A skip is honest and it is not enough: pytest exits `0` when every selected
test skips, so a green tick on those five legs says nothing either way. A
**sixth CI leg, `collector`**, runs `make collector` (the archive cached by the
sha256 that pins it) and then `make collector-check`, which runs exactly those
tests and **fails if any of them skipped** -- so the claim is proved on a
machine that is not the maintainer's.

`make check` never installs the `audit` extra, and neither do CI's `check`
legs. That extra pins `spanweave`, `spanweave-live` and `agentgolden` by git
sha and is needed by the audit alone; everything else in this repository works
without them, and a gate (`tests/gates.py`) fails the build if any module
under `spanweave_zoo/` other than `audit.py` imports any of the three. The
audit's own tests skip without the extra, so a **seventh CI leg, `audit`**,
installs it and runs `make audit-check`, which fails if any of them skipped.

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
captures/<project>/<run-id>/raw/NNNN.headers.json  that head, split on CRLF
captures/<project>/<run-id>/json/NNNN.json         the Collector's re-encoding
captures/<project>/<run-id>/json/NNNN.headers.raw  the head the Collector sent it with
captures/<project>/<run-id>/json/NNNN.headers.json that head, split on CRLF
captures/<project>/<run-id>/rejected/NNNN.body     a POST aimed at another path
captures/<project>/<run-id>/bodies.jsonl           each body as it was recorded
captures/<project>/<run-id>/forwards.jsonl         each forward as it completed
captures/<project>/<run-id>/collector.log          the Collector's own output, verbatim
captures/<project>/<run-id>/MANIFEST.json          what this capture is, its hashes, its seal
```

`SPEC.md` §2 is the authority on that tree; this is a map of it.

## The contract for working here

`CLAUDE.md` is the operating contract -- the standing rules, and the lines a
change must not cross. `CONTRIBUTING.md` is the bar a batch clears.
`SPEC.md` is what to build. `CHANGELOG.md` is what landed.
`OPEN_QUESTIONS.md` is the register of what was asked and how it was answered,
including what is still open. `TASKS.md` is the registry between series: each
batch and the commit that closed it, the decisions log, and the threads the next
series inherits. `reviews/` holds every review a series took, byte for byte,
with `reviews/SHA256SUMS`.

MIT licensed (`LICENSE`), as are `spanweave` and `spanweave-live`.
