# SPEC.md — spanweave-zoo

The source of truth for *what* this repository does. `CLAUDE.md` is the source
of truth for *how*. A behaviour not written here is not specified, and a
section marked as a later batch's is deliberately empty rather than guessed at.

Status: §1 and §2 are specified (A0). §§3-7 are headings naming what the
batches after A0 will fill; nothing in them is implemented today.

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

A3 (§5) fixes the key names; A1 (§3) writes the first ones.

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

Specified in §5, written by A3. Until then `zoo verify` refuses a capture
rather than reporting it verified.

---

## 3. The sink — A1

`zoo sink`: records bytes and nothing else. Any `Content-Type`, any
`Content-Encoding`, one file per POST, the same answer to every request, and no
decoding of any kind. Not specified yet.

## 4. The Collector — A2

`collector/config.yaml` and `zoo capture`: the stock OpenTelemetry Collector at
a pinned version, re-encoding each body to JSON beside the raw bytes, fed by a
byte-identical forward from the raw sink. Not specified yet.

## 5. The manifest, and verification — A3

`MANIFEST.json`'s fields, and `zoo verify`: re-hash everything under
`captures/`, and exit non-zero on any difference and on any body without a
manifest entry. Not specified yet; §2.5 is its sketch.

## 6. The replayer — A4

`zoo replay`: re-send each body with its captured headers in receipt order,
adding nothing. Not specified yet.

## 7. The audit — A5

`zoo audit`: every capture through `spanweave_live serve` and `spanweave.build`,
with every divergence written up as a reproduction naming the repository that
owns it. The one module that may import either library (`tests/gates.py`). Not
specified yet.
