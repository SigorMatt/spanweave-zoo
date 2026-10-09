# SPEC.md — spanweave-zoo

The source of truth for *what* this repository does. `CLAUDE.md` is the source
of truth for *how*. A behaviour not written here is not specified, and a
section marked as a later batch's is deliberately empty rather than guessed at.

Status: §1 and §2 are specified (A0); §3 is specified and implemented (A1,
which also wrote the one part of §5 that `CLAUDE.md` §0.6 already required --
see §3.5). §§4-7 are headings naming what the batches after A1 will fill;
nothing in them is implemented today.

---

## 1. What the zoo is, and the three things it is not

The zoo records what real exporters send and hands those recordings to whoever
wants them. It is a tape recorder with a microphone in the right place.

### 1.1 The zoo parses nothing

No module here reads a span, a trace id, an attribute or an OTLP field. The
sink accepts a POST and writes its body; it does not decode protobuf, does not
decompress gzip, does not validate JSON, and does not look at the content type
except to echo it back. Whether a payload is well-formed OTLP is not a question
the zoo asks, because asking it is how a recorder starts preferring the
payloads it understands.

The one exception is the stock OpenTelemetry Collector (§4), which parses
because that is what it is — and its output is kept *beside* the raw bytes,
never instead of them.

### 1.2 The zoo fixes nothing

A capture is what the exporter sent, including everything wrong with it. A body
that no receiver accepts is still a capture; an export that arrives truncated,
mislabelled, double-compressed or empty is still a capture. The zoo never
repairs, re-encodes in place, normalizes, retries on the exporter's behalf, or
drops a body it cannot make sense of.

When the audit (§7) finds that a receiver rejects a capture, that is a
**finding**: a reproduction, consisting of the capture path, the command, the
observed result and the expected result. It is not a fix. Fixes belong to the
repository that owns the defect, in its own series, where they get a commit and
a test of their own.

### 1.3 The zoo improves nothing

The pet projects are not given feedback through their telemetry. Their
instrumentation is stock and their spans are whatever the instrumentor made;
the zoo does not ask for nicer spans, more attributes, a different exporter or
a different encoding. What the implementers were told is in
`EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md`, and those documents improve only
through the report-back the contract's §6 asks for.

### 1.4 What follows from that

- **A capture is immutable.** Bytes as received, headers beside them, a sha256
  of every body in the manifest. `zoo verify` re-hashes the tree and `make
  check` fails on any difference (`CLAUDE.md` §0.6).
- **The zoo is read-only toward the libraries it captures for.** `spanweave`
  and `spanweave_live` are pinned by git sha in `pyproject.toml`'s `audit`
  extra, imported only by §7's module, and never changed from here.
- **No semantics.** The zoo assigns no roles, no severity, no risk, no
  judgement of a capture's quality. It counts bodies and bytes.

---

## 2. The capture layout

One capture is one **run** of one **project**:

```
captures/<project>/<run-id>/
    raw/
        0001.body               the bytes of the first POST, exactly as received
        0001.headers.json       that request's method, path and every header
        0002.body
        0002.headers.json
        ...
    json/
        0001.json               the Collector's JSON re-encoding of 0001.body
        ...
    MANIFEST.json
```

### 2.1 `<project>` and `<run-id>`

`<project>` is the pet project's short id as `ZOO-BRIEFS.md` names it,
lowercased: `z1` … `z6`. `<run-id>` identifies one run within a project and is
chosen by the operator; it must be a single path segment and must not start with
a dot. A run directory is never reused: a second run is a second `<run-id>`.

### 2.2 `raw/NNNN.body`

The body of the `NNNN`-th POST the sink received, byte for byte, *in the
encoding it arrived in*. A gzipped body is stored gzipped. A protobuf body is
stored as protobuf. `NNNN` is a zero-padded four-digit sequence number in
**receipt order**, starting at `0001`, and is the only ordering the capture
carries.

There is no file extension naming a format, because the format is whatever the
request said it was — and that claim lives in the headers file next to it,
where it can be read rather than inferred from a name the zoo chose.

### 2.3 `raw/NNNN.headers.json`

The request that carried `NNNN.body`, as JSON with `sort_keys=True`: its
method, its path, every header as received (names and values unmodified), the
body length in bytes, and the receipt time. Headers are the record of what the
exporter claimed about its own bytes — `Content-Type`, `Content-Encoding`,
`User-Agent` — and are therefore part of the capture, not metadata about it.

A1 (§3.2) writes the first key names; A3 (§5) may fix them.

### 2.4 `json/NNNN.json`

The stock OpenTelemetry Collector's JSON re-encoding of `raw/NNNN.body`, with
the same `NNNN`, so the two forms of one export are named by one number. It is
a convenience made by a standards-conformant tool and it is kept **beside** the
raw bytes, never instead of them: if the two ever disagree, the raw bytes are
what the exporter sent.

A capture may have no `json/` at all — when the Collector did not run, or could
not read a body. That is a fact about the capture, recorded in the manifest.

### 2.5 `MANIFEST.json`

One file per run, saying what this capture is and what is in it: the project's
own `MANIFEST.json` as the contract (`EXPORT-CONTRACT.md` §1) required the
implementer to write it, the zoo's and the Collector's versions, whether the
run was `recorded` or `real`, when it started and ended, and a sha256 of every
body in `raw/` and every file in `json/`.

Specified in §5, written by A3 -- except the sha256 of every body in `raw/`
and in `rejected/`, which `CLAUDE.md` §0.6 rule 2 puts in the manifest and
which the sink therefore writes as it records (§3.5). `zoo verify` re-hashes
those; a run whose manifest is missing or unreadable is still refused rather
than reported verified.

---

## 3. The sink

`zoo sink` records bytes and nothing else: any `Content-Type`, any
`Content-Encoding`, one file per POST, the same answer to every request, and no
decoding of any kind.

```bash
zoo sink --port 4318 --out captures/z4/2026-10-09T12-00-00Z/raw
```

### 3.1 What `--out` means, and what the sink refuses

`--out` is the `raw/` directory of one run (§2). The sink creates it, and
writes two things beside it, in the **run directory** — `--out`'s parent:
`rejected/` (§3.4) and `MANIFEST.json` (§3.5). Nothing else is created.

`--out` is required; `--port` defaults to `4318` (the OTLP/HTTP port every
brief gave the pet projects) and `--host` to `127.0.0.1`. A recorder holding a
stranger's telemetry listens on the loopback unless an operator says
otherwise.

The sink **refuses to start** — exits non-zero, writing nothing — if `--out`
already contains a `*.body` file. A run directory is never reused (§2.1) and a
capture is never edited (`CLAUDE.md`, "Halt points"), so a sink pointed at an
existing capture must stop rather than renumber into it or overwrite it.

### 3.2 What one POST becomes

A `POST` to `/v1/traces` — that exact path, no other — is recorded as the next
`NNNN` in `--out`:

- **`NNNN.body`**: the request body, byte for byte, *in the encoding it
  arrived in* (§2.2). A gzipped body is written gzipped; a protobuf body is
  written as protobuf. The sink does not decompress, decode, parse, validate,
  re-encode or truncate it, and does not care whether it is well-formed
  anything.
- **`NNNN.headers.json`**: that request, as JSON with `sort_keys=True`:

  ```json
  {
    "bytes": 1234,
    "headers": [["Content-Type", "application/x-protobuf"],
                ["Content-Encoding", "gzip"],
                ["User-Agent", "OTel-OTLP-Exporter-Python/1.37.0"]],
    "method": "POST",
    "path": "/v1/traces",
    "received_at": "2026-10-09T12:00:01.500000+00:00"
  }
  ```

  `headers` is a **list of `[name, value]` pairs in the order received**, with
  names and values exactly as sent, because a header may legally repeat and a
  JSON object would silently keep one of them. `path` is the request target
  verbatim, query string included. `bytes` is the length of `NNNN.body` on
  disk. `received_at` comes from the injected `now` (§3.6) and is the only
  clock the record has. (§2.3: A1 writes these key names; A3 may fix them.)

`NNNN` is a zero-padded four-digit counter in **receipt order**, starting at
`0001`, assigned when the body has been read and under a lock, so two POSTs in
flight are numbered in the order their bodies arrived rather than in the order
two threads happen to finish writing.

### 3.3 The answer

Every recorded POST to `/v1/traces` is answered **`200`** with an **empty body**
and the **request's own `Content-Type` echoed back** (and no `Content-Type` at
all if the request had none — the sink has no content type of its own to
invent). The answer does not depend on the bytes: it is the same for protobuf,
for JSON, for gzip, for a truncated body and for a body no receiver would
accept. The sink is not a receiver and its `200` means "recorded", never
"understood".

### 3.4 Any other path: `404`, and still recorded

A POST to any other path is answered **`404`** — empty body, same echoed
content type — and is **still recorded**, as `NNNN.body` +
`NNNN.headers.json` under `rejected/`, with its own counter starting at `0001`.
The counters are separate so that `raw/NNNN` stays the contiguous sequence
`json/NNNN` is paired with (§2.4).

An exporter aimed at the wrong path is exactly the kind of fact this repository
exists to hold, and a `404` that threw the bytes away would lose it. The path
is the one thing the sink looks at, because it must choose a directory;
`headers.json` records what it saw.

Methods other than `POST` are answered `501` by `http.server` and are not
recorded: there is no body to record, and the sink invents nothing.

### 3.5 The digest, and `zoo verify`

`CLAUDE.md` §0.6 rule 2 puts **a sha256 of each body in the manifest**, so the
sink writes `MANIFEST.json` in the run directory as it goes, appending one
entry per body and rewriting the file atomically:

```json
{"bodies": [{"bytes": 1234, "file": "raw/0001.body", "sha256": "9f86d0..."},
            {"bytes": 17, "file": "rejected/0001.body", "sha256": "2c2616..."}]}
```

`file` is the body's path relative to the run directory, so a rejected body is
distinguishable from an accepted one; entries are in the order the bodies were
recorded. **This is the whole of what A1 writes**: everything else `MANIFEST.json`
carries — the project's own manifest, `sink_version`, `collector_version`,
`kind`, `started_at`/`ended_at`, the `json/` hashes — is §5's, added by A3 to
this same file and these same entries. There is exactly one home for a digest.

`zoo verify` therefore stops refusing (§5) and re-hashes: for every run
directory under `captures/`, it reads `MANIFEST.json`, re-reads every listed
body, and exits non-zero if a digest differs, a length differs, a listed body
is missing, or the manifest is absent or unreadable. A run with a manifest it
cannot read is still a refusal, not a pass.

### 3.6 The seams

The sink is the one thing here that touches the world, so every point where it
does is injected and named here (`CLAUDE.md`, "Architecture invariants"):

| Seam | What it is | Why |
|---|---|---|
| `now` | returns the receipt time as the record will carry it | no module under `spanweave_zoo/` reads the clock; `cli.py` passes the one real clock, and a test passes a clock whose values it chose |
| the listener | the server is constructed by a factory a caller calls | a test binds `127.0.0.1` on port `0`, so the suite never collides with a port in use and never races a fixed one |
| `before_record` | called with the body bytes once the body is read, before `NNNN` is assigned | a test can hold two POSTs in flight at a chosen point and make receipt order observable **without sleeping** — a sleep in a concurrency test is a race with a slow machine |
| `after_record` | called with the manifest entry once the body is on disk | the same, from the other side; `cli.py` also uses it to print one line per recorded body |

The sink never reads the clock, never sleeps, never binds a socket and never
draws a random number outside these.

### 3.7 What the sink never does

It never decodes, decompresses, parses or validates a body; never edits or
renumbers an existing capture; never drops a body it cannot make sense of;
never varies its answer by content; and never imports `spanweave` or
`spanweave_live` (`tests/gates.py`). A body that is empty, truncated,
mislabelled, double-compressed or not OTLP at all is recorded like any other,
because the zoo records what exporters send and never improves it (§1).

A POST that carries no `Content-Length` — or one whose `Content-Length` is not
a number — is recorded as a **zero-byte** body with its headers beside it, and
answered like any other. The sink reads the framing it was given and does not
guess one it was not: decoding a `Transfer-Encoding` is decoding. What it could
see is what the capture says it saw, and the header that said so is in the
record.

## 4. The Collector — A2

`collector/config.yaml` and `zoo capture`: the stock OpenTelemetry Collector at
a pinned version, re-encoding each body to JSON beside the raw bytes, fed by a
byte-identical forward from the raw sink. Not specified yet.

## 5. The manifest, and verification — A3

`MANIFEST.json`'s fields, and `zoo verify`: re-hash everything under
`captures/`, and exit non-zero on any difference and on any body without a
manifest entry. Not specified yet; §2.5 is its sketch.

A1 wrote the part of this that `CLAUDE.md` §0.6 rule 2 already mandated and no
more: the `bodies` entries' `file`, `sha256` and `bytes` (§3.5), and a `zoo
verify` that re-hashes them. Still A3's, and still unspecified here: every
other field of `MANIFEST.json`, the `content_type` / `content_encoding` of each
entry, the `json/` hashes, and **failing on a body present on disk but absent
from the manifest** — which today's `verify` does not check.

## 6. The replayer — A4

`zoo replay`: re-send each body with its captured headers in receipt order,
adding nothing. Not specified yet.

## 7. The audit — A5

`zoo audit`: every capture through `spanweave_live serve` and `spanweave.build`,
with every divergence written up as a reproduction naming the repository that
owns it. The one module that may import either library (`tests/gates.py`). Not
specified yet.
