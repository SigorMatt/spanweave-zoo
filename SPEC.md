# SPEC.md — spanweave-zoo

The source of truth for *what* this repository does. `CLAUDE.md` is the source
of truth for *how*. A behaviour not written here is not specified, and a
section marked as a later batch's is deliberately empty rather than guessed at.

Status: §1 and §2 are specified (A0); §3 is specified and implemented (A1,
which also wrote the one part of §5 that `CLAUDE.md` §0.6 already required --
see §3.5); §4 is specified and implemented (A2: the Collector, the tee and
`zoo capture`, which also writes the two manifest fields its own behaviour
needs -- see §4.5); §5 is specified and implemented (A3: the whole of
`MANIFEST.json` and a `zoo verify` that checks the capture in both
directions; A3a: a capture exists only once it is ready; A3b: the manifest is
assembled once, at the end, from the run's journals, and covers every file in
the capture; A3c: the octets of each request's head are the record, with the
stdlib's parse beside them -- see §2.3). §§6-7 are headings naming what the batches after A3 will fill;
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

Two things are not that, and are named here rather than discovered as
exceptions:

- the stock OpenTelemetry Collector (§4) parses, because that is what it is —
  and its output is kept *beside* the raw bytes, never instead of them;
- two documents that are not payloads are read as documents: the capture's own
  `MANIFEST.json`, which the zoo wrote, and the pet project's `MANIFEST.json`,
  which the zoo copies into it verbatim and reads no field of (§5).

The sentence above about the content type is about the **sink**, and stays
exactly true of it: the sink echoes a content type and decides nothing from
it. When a run ends, the manifest writer copies each body's `Content-Type` and
`Content-Encoding` **across from the record it already made** — the body's own
`NNNN.headers.json`, where the request put them verbatim (§5). That is a copy
of what the exporter claimed, not an inspection of what it sent, and no byte
of a body is read to do it. (A1 left those two fields out for exactly the
reason this paragraph now resolves; A3's row required them, and this is the
amendment that makes both texts say the same thing.)

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
        0001.headers.raw        that request's head, octet for octet
        0001.headers.json       the stdlib's parse of that same head
        0002.body
        0002.headers.raw
        0002.headers.json
        ...
    json/
        0001.json               the Collector's JSON re-encoding of 0001.body
        ...
    bodies.jsonl                one line per recorded body, written as it lands
    forwards.jsonl              one line per attempted forward to the Collector
    MANIFEST.json
```

`bodies.jsonl` and `forwards.jsonl` are the run's own notes, written as the run
goes and flushed line by line (§3.5). `MANIFEST.json` is assembled from them
when the run ends (§5.5), and lists a sha256 for **every** file above except
itself — the journals and both headers files included (§5.6).

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

### 2.3 `raw/NNNN.headers.raw` and `raw/NNNN.headers.json`

Headers are the record of what the exporter claimed about its own bytes —
`Content-Type`, `Content-Encoding`, `User-Agent` — and are therefore part of
the capture, not metadata about it. Two files hold them, and which is which
matters:

- **`NNNN.headers.raw` is the unmodified record.** The request line and the
  header block as the octets arrived — CRLFs intact, in the order sent, up to
  and including the blank line that ends them. Nothing is decoded, reordered,
  folded, case-normalized or dropped. This is the file a reader believes.
- **`NNNN.headers.json` is a parse of those same octets**, written for
  convenience: Python's `http.server` already parsed the head to route the
  request, and this is what it got. It is kept *beside* the octets, never
  instead of them, on the same rule as §2.4's `json/`: if the two disagree,
  the octets are what arrived.

The parse loses things, which is why the octets are kept. A **bare CR inside a
header value** is the case this file was added for: HTTP forbids it, real
clients emit it, and `email`'s header parser splits the line on it — so the
value arrives truncated and every header after the split is absent from the
parse altogether. A recorder whose record was the parse would hold what Python
can represent rather than what the exporter sent, which is the one thing this
repository exists not to do (§1). The parse is not wrong to be a parse; it is
only not the record.

`NNNN.headers.json` is JSON with `sort_keys=True`: the method, the path, every
header the parse produced (names and values unmodified), the body length in
bytes, and the receipt time. A1 (§3.2) wrote these key names and A3 kept them.
The manifest carries two of these values across — `Content-Type` and
`Content-Encoding` — so that a reader of one `bodies` entry knows what the
request claimed (§5.4); it reads them from the parse because they are the
values the sink echoed, and the octets remain the record of everything the
request said, repeats included.

Both files have a digest of their own in the manifest (§5.6), so `zoo verify`
would refuse a capture whose head octets had been tidied.

### 2.4 `json/NNNN.json`

The stock OpenTelemetry Collector's JSON re-encoding of `raw/NNNN.body`, with
the same `NNNN`, so the two forms of one export are named by one number. It is
a convenience made by a standards-conformant tool and it is kept **beside** the
raw bytes, never instead of them: if the two ever disagree, the raw bytes are
what the exporter sent.

The shared `NNNN` is a convenience and not a promise: `json/NNNN.json` is the
NNNN-th POST the *Collector* made, and a batch processor may coalesce or split.
§4.7 says what that means and why nothing is renumbered to hide it.

A capture may have no `json/` at all — when the Collector did not run, or could
not read a body. That is a fact about the capture, recorded in the manifest.

### 2.5 `MANIFEST.json`

One file per run, saying what this capture is and what is in it: the project's
own `MANIFEST.json` as the contract (`EXPORT-CONTRACT.md` §1) required the
implementer to write it, the zoo's and the Collector's versions, whether the
run was `recorded` or `real`, when it started and ended, and a sha256 of
**every file in the run directory except itself**.

Specified in §5, which lists every field and when each is written. The sha256
of every body is written as the body is recorded, because `CLAUDE.md` §0.6
rule 2 puts it in the manifest and there is nothing to re-hash against without
it (§3.5) — into `bodies.jsonl`, a line at a time, flushed. The document
itself is assembled **once**, when `zoo capture` stops, from those lines and
from a walk of the directory (§5.5). `zoo verify` re-hashes every file it
lists and also refuses a file the manifest does not list; a run whose manifest
is missing or unreadable, or which has no `ended_at`, is refused rather than
reported verified.

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

`zoo capture` is the one caller that does not want the directory made up
front: under it a capture exists on disk only once the whole tee is ready
(§4.6), so its two recorders create what they write into when they write it.
Either way a recorder makes its own directory; what differs is *when* one
appears, and nothing else.

`--out` is required; `--port` defaults to `4318` (the OTLP/HTTP port every
brief gave the pet projects) and `--host` to `127.0.0.1`. A recorder holding a
stranger's telemetry listens on the loopback unless an operator says
otherwise.

The sink **refuses to start** — exits non-zero, writing nothing — if `--out`
already contains a body **or** a headers file of either kind — `.headers.raw`
or `.headers.json` (§2.3) — from an earlier capture. A run directory is never
reused (§2.1) and a capture is never edited
(`CLAUDE.md`, "Halt points"), so a sink pointed at an existing capture must
stop rather than renumber into it or overwrite it — and half a capture is still
a capture to refuse, because renumbering into it would overwrite the half that
is there.

The refusal counts bodies and headers files **separately**, and says which it
found; a request leaves two headers files, so the headers count is per file and
not per request. The json sink's bodies are `json/NNNN.json` (§4.5), so a glob
for its suffix also matches `NNNN.headers.json`: counting the two together
reported "2 body file(s), starting 0001.headers.json" for one recorded export,
which is a true refusal told wrong. A refusal an operator cannot read is most
of the way to no refusal.

### 3.2 What one POST becomes

A `POST` to `/v1/traces` — that exact path, no other — is recorded as the next
`NNNN` in `--out`:

- **`NNNN.body`**: the request body, byte for byte, *in the encoding it
  arrived in* (§2.2). A gzipped body is written gzipped; a protobuf body is
  written as protobuf. The sink does not decompress, decode, parse, validate,
  re-encode or truncate it, and does not care whether it is well-formed
  anything.
- **`NNNN.headers.raw`**: the octets of that request's head, as they arrived
  — the request line, then every header line, CRLFs intact, up to and
  including the blank line that ends the block (§2.3). It is written from the
  bytes as they are read off the socket, before anything parses them, and the
  body is not in it. This is the unmodified record of the request; the file
  below is a parse of it.
- **`NNNN.headers.json`**: that same request as the stdlib parsed it, as JSON
  with `sort_keys=True`:

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
  clock the record has. (§2.3: A1 wrote these key names and A3 kept them;
  §5.4 carries two of these values into the manifest and changes nothing here.)
  A head the parse cannot represent — a bare CR in a value — is in
  `NNNN.headers.raw` and not here, and §2.3 says which of the two a reader
  believes.

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
`NNNN.headers.raw` + `NNNN.headers.json` under `rejected/`, with its own
counter starting at `0001`.
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
sink writes the digest down as the body lands — into the run's **journal**,
`bodies.jsonl`, one JSON object per line with `sort_keys=True`, appended and
flushed:

```jsonl
{"bytes": 1234, "file": "raw/0001.body", "sha256": "9f86d0..."}
{"bytes": 17, "file": "rejected/0001.body", "sha256": "2c2616..."}
```

`file` is the body's path relative to the run directory, so a rejected body is
distinguishable from an accepted one; lines are in the order the bodies were
recorded. **This is the whole of what the sink writes** (that, and each
request's `NNNN.headers.json`): everything else `MANIFEST.json` carries — the
project's own manifest, `sink_version`, `collector_version`, `kind`,
`started_at`/`ended_at`, each entry's `content_type`/`content_encoding`, a
digest for every other file — is §5's, written when the run ends. There is
exactly one home for a digest.

A journal rather than the manifest itself, for two reasons. **Cost**: a
manifest rewritten after every POST is read and re-serialized once per body,
so recording the last body of a long run costs more than recording the first,
and an exporter exporting 1,600 times would pay for that curve. Appending a
line is the same work every time. **Honesty under a hard stop**: a flushed line
is on disk the moment the body is, and nothing is half-rewritten.

The journal is part of the capture: it stays in the run directory and the
manifest carries its sha256 like any other file's (§5.6).

`zoo verify` therefore stops refusing and re-hashes: for every run directory
under `captures/`, it reads `MANIFEST.json`, re-reads every file the manifest
lists, and exits non-zero if a digest differs, a length differs, a listed file
is missing, or the manifest is absent or unreadable. A run with a manifest it
cannot read is still a refusal, not a pass. §5.6 is the whole of what `verify`
checks, including the other direction — a file on disk that the manifest never
listed.

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

## 4. The Collector, and the tee

The sink records bytes (§3). The Collector makes those same bytes readable as
JSON **without the zoo parsing one of them**, and its output is kept *beside*
the record, never instead of it (`CLAUDE.md` §0.6 rule 4). It is the one
component here that parses, because that is what it is (§1.1).

```
   the pet project                 zoo capture
   ---------------                 -----------------------------------------
   OTLP/HTTP exporter  --POST-->   raw sink        :4318   writes raw/NNNN
                                       |  forward (byte-identical)
                                       v
                                   Collector       :4320   re-encodes to JSON
                                       |  otlp_http exporter, encoding: json
                                       v
                                   json sink       :4319   writes json/NNNN
```

### 4.1 Stock, pinned, checked in — and not committed

`collector/` holds three files and no binary:

| File | What it is |
|---|---|
| `collector/VERSION` | the pinned release, one line, no leading `v` |
| `collector/SHA256SUMS` | the release's own sha256 of each platform's tarball |
| `collector/config.yaml` | the config the Collector runs, verbatim |

`make collector` downloads
`otelcol-contrib_<VERSION>_<os>_<arch>.tar.gz` from the
`open-telemetry/opentelemetry-collector-releases` release of exactly that
version, **checks its sha256 against the matching line in
`collector/SHA256SUMS`**, refuses to unpack on a mismatch or on a platform the
file does not pin, and extracts `collector/otelcol-contrib`. The digests are
the release's own: each asset is published with a `.sha256` beside it, and
those are the bytes copied here.

The binary is about 100 MB and is **gitignored**. The version and the digest
are the record; the bytes are a download. Nothing in `make check` fetches it,
and `make collector` is never a prerequisite of a gate: a build that reaches
the network to decide whether it passes is a build that fails when GitHub does.

The Collector is **stock**. No custom build, no components beyond those named
in §4.2, and no patch. A zoo that shipped its own Collector would be back to
re-encoding bytes with code nobody else has reviewed.

### 4.2 `collector/config.yaml`

One `otlp` receiver, the `batch` processor **at its defaults**, one
`otlp_http` exporter with `encoding: json`, one traces pipeline. Each endpoint
is written as `${env:NAME:-default}` — the stock confmap environment-variable
form — so that the file that is checked in is also the file that runs, with the
ports supplied rather than edited:

| Variable | Default | What it is |
|---|---|---|
| `ZOO_COLLECTOR_OTLP_GRPC` | `127.0.0.1:4317` | the receiver's gRPC endpoint |
| `ZOO_COLLECTOR_OTLP_HTTP` | `127.0.0.1:4318` | the receiver's HTTP endpoint |
| `ZOO_JSON_SINK` | `http://127.0.0.1:4319` | where the JSON goes |

The defaults are the canonical OTLP pair — 4317 and 4318 — which is what the
config means standing alone: a project pointed straight at the Collector,
without a zoo in front of it. Under `zoo capture` the defaults do not apply to
the HTTP receiver, because **4318 belongs to the exporter**: every brief gave
the pet projects `$ENDPOINT/v1/traces` on 4318, the raw sink holds that port,
and the Collector sits behind the sink on a third port (§4.4). The app's port
is the one thing the zoo does not move.

Two settings are not defaults and are here for a reason:

- **`compression: none`** on the exporter. `otlp_http` compresses with gzip by
  default; the sink never decompresses anything (§1.1), so a compressed
  forward would make `json/NNNN.json` a gzip member rather than the JSON §2.4
  promises. The re-encoding must arrive readable or it is not a re-encoding.
- **`service.telemetry.metrics.level: none`**. The Collector's own internal
  metrics endpoint is a fourth listening port the zoo never reads, and a
  recorder should not open one. Its own telemetry is not part of a capture.

One setting is written out although it *is* the stock default, because
`zoo capture` depends on it: **`service.telemetry.logs.level: info`**. The
Collector logs `Everything is ready. Begin running and processing data.` at
`info` once every component in its pipeline has started, and that line is what
readiness means (§4.6). At `warn` — which this config asked for until A3a — a
healthy Collector says nothing at all on startup, and readiness would have to
be guessed from a port accepting a connection, which a stranger holding that
port does too. The Collector's log is the Collector's own: the zoo reads one
line of it to know it is running, echoes it to the operator, and copies none of
it into a capture.

The `WORKPLAN.md` A2 row names this exporter `otlphttp`. At the pinned version
that spelling is a **deprecated alias** and the Collector says so on every
start; the config uses the current name, `otlp_http`, for the same component.

### 4.3 The tee: write first, then forward, byte for byte

The raw sink forwards every body it **accepts** (§3.2 — a POST to
`/v1/traces`) to the Collector, and the forward is **byte-identical**:

- the body is the bytes on disk, the same object that was written as
  `raw/NNNN.body`. Still gzipped if it arrived gzipped, still protobuf if it
  arrived as protobuf. The sink does not decompress, decode, re-encode or
  re-frame it to forward it, exactly as it does not to record it;
- the headers are **every header as received, in order, repeats included**,
  with two exceptions that name the connection rather than the payload:
  `Host` (which names the destination, and the destination has changed) and
  the hop-by-hop headers of RFC 9110 §7.6.1 — `Connection`, `Keep-Alive`,
  `Transfer-Encoding`, `TE`, `Upgrade`, `Proxy-Authorization`,
  `Proxy-Authenticate`. `Content-Type`, `Content-Encoding`, `Content-Length`
  and `User-Agent` go through untouched, because they are what the Collector
  needs in order to read the bytes the exporter actually sent.

**The body is on disk before the forward is attempted.** That order is the
whole point: the record is made first and the convenience second, so there is
no arrangement of failures in which the zoo forwarded something it did not
record.

A POST the sink **rejects** (§3.4, any other path) is recorded and *not*
forwarded. Forwarding it would invent traffic the exporter never aimed at the
Collector, and the Collector's answer to it would be a fact about the zoo
rather than about the capture.

The answer to the exporter is still §3.3's: `200`, empty body, its own content
type echoed. It does not depend on the bytes and it does not depend on the
forward. The sink's `200` means "recorded"; it has never meant "understood",
and it must not start meaning "re-encoded".

### 4.4 A forward that fails

The Collector is a separate process and may be absent, starting, stopped or
wedged. A failed forward **loses nothing and is never silent** (`CLAUDE.md`
§0.6):

- the body, its headers and its digest are already recorded, and are not
  touched;
- the failure is written into `MANIFEST.json` as a `forwards` entry (§4.5);
- it is printed, naming the body and the error;
- `zoo capture` exits **non-zero** when any forward failed, so a run whose
  `json/` is incomplete cannot be mistaken for one that is complete.

The forward has a timeout (5 seconds by default, `--forward-timeout`). A
Collector that never answers must not become an exporter that never gets an
answer, and a recorder that blocks the system it is recording has changed the
thing it was supposed to observe.

### 4.5 One run directory, one manifest, two sinks

`zoo capture` runs **two recorders in one process** on one run directory
(`SPEC.md` §2): the raw sink on `raw/` and the json sink on `json/`. They write
**one `MANIFEST.json`**, in the run directory, which is the file §5 completes
and `zoo verify` re-hashes. There is one manifest per run and there always was;
the two recorders share it.

Three things follow, and each is a decision rather than an accident:

1. **Different `--out` directories.** `raw/` and `json/`. Two recorders on one
   directory would share a counter and a rejected directory and would
   overwrite each other's bodies.
2. **A lock on the manifest, not just on each recorder.** A recorder
   serializes its own writes (§3.2); the manifest is shared, so the
   read-modify-write that appends an entry is serialized **per run
   directory**, across recorders, in `manifest.py`. The recorder's own lock is
   always taken first and the manifest's last, so the two can never deadlock.
3. **A rejected directory per sink.** The raw sink keeps `rejected/` (§3.4).
   The json sink, whose only caller is our own Collector with our own config,
   writes to `rejected-json/` — so a misdirected POST is still recorded (§3.4)
   and the two counters cannot collide. A POST in `rejected-json/` means the
   zoo's own exporter endpoint is wrong, which is worth finding out.

The json sink writes `json/NNNN.json` rather than `NNNN.body`, because §2.4
names that file. Its two headers files are written beside it like any other
request's (§2.3): the Collector is an HTTP client like any other and the sink
does not keep less of what one caller sent than of another's. A **rejected** body keeps
`.body` in either sink (§3.4): it is not a re-encoding of anything, it is bytes
aimed at the wrong path, and naming it `.json` would be a claim about its
contents — which is the one kind of claim the sink does not make.

`zoo capture` adds two fields to the manifest, and no more:

```json
{"bodies": [...],
 "collector_version": "0.162.0",
 "forwards": [{"file": "raw/0001.body", "status": 200},
              {"file": "raw/0002.body",
               "error": "ConnectionRefusedError: [Errno 111] ..."}],
 "problems": ["collector exited: 137"]}
```

- **`collector_version`** is `collector/VERSION` — the pin, not a guess. It is
  written before the first body arrives. `zoo capture` runs the binary's
  `--version` and **refuses to start** if it does not match the pin (§4.6): a
  capture labelled with a version that did not re-encode it would be worse
  than one labelled with nothing.
- **`forwards`** is one entry per attempted forward, in the order the forwards
  *completed* (which is receipt order unless two exports were in flight),
  carrying either the Collector's HTTP `status` or the `error` that stopped it.
  It is about **delivery**, not about bytes, which is why it is a list of its
  own and not a field on a `bodies` entry: A1 pinned those to `file`, `sha256`
  and `bytes`, and `zoo verify`'s re-hash reads only those (§3.5). Each
  outcome is journalled to `forwards.jsonl` as it completes, for §3.5's
  reasons, and the list is assembled from that journal when the run ends. Both
  the key and the journal are **absent** from a run that forwarded nothing —
  `zoo sink` alone has no Collector behind it.
- **`problems`** is one line per thing that went wrong during the run which the
  capture cannot fix — a Collector that exited (§4.6), a project manifest that
  could not be copied (§5.3). A problem noticed *during* the run is written
  when it is noticed rather than at the end, so a capture whose Collector died
  says so even if the run is then stopped the hard way; one found while the
  manifest is being assembled goes in with it. The key is **absent** from a
  capture that had none, rather than an empty list: a reader asking "did
  anything go wrong here" should not have to tell `[]` from a field nobody
  wrote. `zoo capture` exits non-zero on any problem and `zoo verify` fails on
  any (§5.6).

Everything else in `MANIFEST.json` is §5's: `collector_version` is written once
at the start beside `kind`, `sink_version` and `started_at`, and the rest when
the run ends (§5.5).

### 4.6 `zoo capture`

```bash
zoo capture --project z4 --run-id 2026-10-09T12-00-00Z \
            --kind real --project-manifest ../streaming-concierge/MANIFEST.json
```

**A capture exists on disk only once it is ready**, and ready means two things,
both of them:

- all three listeners accept: the json sink, the raw sink, and the Collector's
  OTLP/HTTP receiver;
- the Collector child is alive and has said so **itself** — its own ready line,
  `Everything is ready. Begin running and processing data.`, read from its own
  log (§4.2).

Both, because neither implies the other. A connection the receiver accepts says
only that *something* holds that port: a stranger already on 4320 accepts one
too, while the Collector that could not have the port has meanwhile exited —
and the run gets recorded as if it were fine, with a `json/` that could only
ever be empty. A ready line without a connection is the mirror image: a
Collector that reported itself started on a port the forward cannot reach.

So the order is, and these steps are in this order for that reason:

1. read the pin, and confirm the binary reports it (§4.5);
2. construct both recorders and **bind** both sinks — which is where a run
   directory that already holds a body (§3.1) and a port something else is
   holding are both refused;
3. start the Collector and wait for it, a bounded number of looks with the
   injected `sleep` between them (§4.8);
4. **then** create `captures/<project>/<run-id>/` and label the manifest
   (§5.5);
5. set the sinks serving, raw last, so a forward always has somewhere to go and
   no body can be recorded before the manifest says what the capture is;
6. print the one readiness line:

```
zoo capture: the raw bytes are the record. Ctrl-C to stop.
```

That line is printed **once**, after the directory exists, and it is the only
line that means a capture is up. `zoo sink`'s banner (§3) says a different
thing — bytes being recorded with nothing behind the sink — and says it
differently: each names its own command and neither is a prefix of the other,
because an operator reading a log should not have to work out which command
wrote it. The lines after it name the ports and the directories of the run that
is now up.

A **refusal** is therefore a refusal before anything exists. Any of the three
ports held, the Collector exiting, a config it cannot load, a binary that is
not the pin: each names the port or the cause — the Collector's refusals quote
its own last log lines, which is where `bind: address already in use` and the
port it is about are written — and `zoo capture` exits **2** leaving **no run
directory at all**. That is what makes a capture directory mean a capture was
made.

Then it serves until interrupted. Then it stops the raw sink, stops the
Collector, stops the json sink, **assembles the manifest** (§5.5) — the
journals, a digest for every other file, the project's own manifest copied as
it stands now (§5.3), `ended_at` last — prints what it recorded and exits
non-zero if any forward failed (§4.4), the Collector exited (below), or the
manifest could not be completed as asked (§5.3).

**Every line it prints is flushed as it is written.** An operator watching a
pet project export into a log file sees each body as it lands, not when the
capture is stopped; a capture that looks silent is a capture somebody is about
to kill.

**A stdout nobody is reading ends the run, rather than killing it.** `zoo
capture | head -5` closes the pipe while three threads are recording, and the
next line written raises `BrokenPipeError` — out of a sink's handler thread, in
the worst case, leaving a capture on disk whose manifest was never assembled.
So the first broken pipe asks the run to stop the way Ctrl-C does, every later
line goes nowhere, and the manifest is completed. The exit status is then what
the capture was — zero when nothing else went wrong — because a reader walking
away is not a fact about the bytes.

**A Collector that exits during the run** is recorded, not absorbed. The
caller's wait notices it on its next hop, writes
`problems: ["collector exited: <code>"]` into `MANIFEST.json` there and then
(§4.5), prints it, and `zoo capture` exits non-zero. It is recorded once,
however often it is looked at. The raw sink keeps recording, because the raw
bytes are the record and an exporter still exporting must still be recorded;
what has stopped is the re-encoding, and the manifest says so rather than
leaving an operator to find a `json/` that quietly stopped filling. `zoo
verify` fails on any capture whose manifest records a problem (§5.6), so a
capture nobody can trust does not pass the check whose whole job is trust.

**`SIGINT` and `SIGTERM` both end a run**, through a handler that only asks it
to stop; the shutdown itself happens on the main thread, which is where the
Collector gets stopped rather than orphaned holding its port. This is installed
rather than relied upon, and the caller waits in short hops rather than once
and forever: a capture has three threads blocked in `select`, the kernel may
hand the signal to any of them, and a main thread parked in an untimed wait
never runs the Python handler that would have noticed. A run that cannot be
stopped with Ctrl-C is not a detail — it is a Collector left holding 4320 and
an operator who has to find it.

| Option | Default | |
|---|---|---|
| `--project` | required | `z1` … `z6`, as `ZOO-BRIEFS.md` names it (§2.1) |
| `--run-id` | required | one path segment, not starting with a dot (§2.1) |
| `--kind` | required | `recorded` \| `real`, never inferred (§5.2) |
| `--project-manifest` | required | the project's own `MANIFEST.json`, copied verbatim (§5.3) |
| `--captures` | `captures` | the capture root |
| `--port` | `4318` | the raw sink: **the app's port** |
| `--json-port` | `4319` | the json sink, where the Collector exports |
| `--collector-port` | `4320` | the Collector's OTLP/HTTP receiver |
| `--collector-grpc-port` | `4317` | its gRPC receiver, which the tee never feeds |
| `--host` | `127.0.0.1` | what all three bind |
| `--collector-dir` | `collector` | where `VERSION`, `SHA256SUMS` and `config.yaml` are |
| `--forward-timeout` | `5.0` | seconds (§4.4) |

It **refuses to start**, writing nothing, when: the run directory already holds
a body (§3.1, both sinks); any of `--port`, `--json-port` and
`--collector-port` is held by something else — the sinks' own binds say so, and
a port held under the Collector is the Collector exiting and saying so in its
log; `--collector-dir` has no `VERSION` or no `config.yaml`; the binary is
absent — naming `make collector`; the binary's `--version` does not match the
pin; `--kind` is missing or is not one of the two (§5.2);
`--project-manifest` names a path that is not a readable JSON document (§5.3);
or the Collector does not report ready within the readiness budget. A capture
that was never re-encoded is a fact worth refusing for, because the operator
can still fix it; a capture *silently* missing its `json/` is a fact discovered
a week later.

Only the HTTP receiver is fed. An exporter that speaks OTLP/gRPC reaches the
Collector directly or not at all, and the raw sink — which is HTTP — never sees
it, so it is never captured. Every brief gave the projects OTLP/HTTP; a gRPC
export is an unrecorded export, and that is stated here rather than discovered
from an empty `raw/`.

### 4.7 `raw/NNNN` and `json/NNNN` are not a promise

§2.4 says the two forms of one export are named by one number, and under one
export at a time they are. They are **not guaranteed** to be, and the reason is
in this section's own config: the `batch` processor at defaults may coalesce
two exports into one JSON POST, or split one large export into several. The
Collector may also retry, which sends the same spans twice.

So: `json/NNNN.json` is the **NNNN-th POST the Collector made**, and
`raw/NNNN.body` is the NNNN-th POST the exporter made. The manifest records
both sequences and `zoo verify` re-hashes both. The pairing is a convenience
that holds for the common case, and the raw bytes are the record either way
(§2.4). The zoo does not renumber, split or merge anything to make the two
columns line up — that would be improving the capture.

### 4.8 The seams §4 introduces

| Seam | What it is | Why |
|---|---|---|
| `forward` | called with the method, path, headers and body once the body is on disk; returns the forwarded request's HTTP status or raises | the only outbound socket in the package. A test drives the tee with a forward that records what it was handed, so the tee's mechanics need no Collector |
| `launch` | called with the resolved config, environment and ports; returns a handle that can be stopped **and asked whether the child is still there** | starting a process is touching the world. A test passes a launcher that starts nothing, reports the pinned version, and can say the child exited — which is how §4.6's mid-run failure is driven without killing anything |
| `sleep` | the readiness wait between looks, a bounded number of them | no module under `spanweave_zoo/` reads a clock or sleeps on its own (`CLAUDE.md`); `cli.py` passes the one real `sleep`, as it passes the one real `now` |
| `after_forward` | called with each forward's outcome once it is in the manifest | one printed line per forward, and the way a test observes a forward without polling a file |

### 4.9 The Collector in CI, and locally

The integration test — a hand-built OTLP protobuf export through the tee into
the real binary, asserting `json/0001.json` is OTLP JSON carrying **the same
trace and span ids** — runs when `collector/otelcol-contrib` is present and is
**skipped when it is absent**, which is how it behaves in CI: nothing in CI
downloads a 100 MB binary. `make check` is therefore green both with the binary
and without it, and on a developer machine that has run `make collector` it is
green having actually run the Collector.

What holds in CI without the binary: the config and the pin are asserted as
text, the tee's mechanics are asserted against the `forward` seam,
`collector_version` in the manifest is asserted equal to `collector/VERSION`
through the `launch` seam, and §4.6's readiness and refusals are asserted
against a **stand-in child process** — a few lines that bind the receiver
endpoint they are given through `ZOO_COLLECTOR_OTLP_HTTP` and log the way the
Collector does. It stands in for the Collector's *lifecycle*, which is all
readiness is about: a port it cannot have, a ready line it does or does not
log, a config it cannot load. It stands in for no re-encoding, which is the one
thing it is not allowed to claim. What only a machine with the binary proves is that a
real protobuf export comes back as JSON with the same ids — and a test that
quietly passed without proving it would be the kind of reassuring pass this
repository exists to refuse (`CLAUDE.md`). It skips loudly instead.

## 5. The manifest, and verification

One `MANIFEST.json` per run directory (§2.5, §4.5): **labelled when
`zoo capture` starts and assembled when it ends**, from the journals the run
kept (§3.5) and a walk of the directory. It says what this capture is, what is
in it, and what hash every file in it had when the run ended — and `zoo verify`
re-hashes the tree against it on every `make check`.

```json
{
  "bodies": [
    {"bytes": 1234,
     "content_encoding": "gzip",
     "content_type": "application/x-protobuf",
     "file": "raw/0001.body",
     "sha256": "9f86d0..."},
    {"bytes": 2048,
     "content_encoding": null,
     "content_type": "application/json",
     "file": "json/0001.json",
     "sha256": "2c2616..."}
  ],
  "collector_version": "0.162.0",
  "ended_at": "2026-10-09T12:04:11.902000+00:00",
  "files": [
    {"bytes": 211, "file": "bodies.jsonl", "sha256": "4f7c91..."},
    {"bytes": 104, "file": "forwards.jsonl", "sha256": "b1d4a0..."},
    {"bytes": 389, "file": "json/0001.headers.json", "sha256": "7a0c3e..."},
    {"bytes": 214, "file": "json/0001.headers.raw", "sha256": "5d2f88..."},
    {"bytes": 412, "file": "raw/0001.headers.json", "sha256": "e3b0c4..."},
    {"bytes": 231, "file": "raw/0001.headers.raw", "sha256": "c0ffee..."}
  ],
  "forwards": [{"file": "raw/0001.body", "status": 200}],
  "kind": "real",
  "project_manifest": {"contract_version": "1.0", "framework": "openai",
                       "instrumentation": ["..."], "mode": "real"},
  "sink_version": "0.0.1",
  "started_at": "2026-10-09T12:00:00.117000+00:00"
}
```

| Field | What it is |
|---|---|
| `kind` | `recorded` or `real` — **required** (§5.2) |
| `project_manifest` | the pet project's own `MANIFEST.json`, copied verbatim when the run ends (§5.3) |
| `sink_version` | `spanweave_zoo.__version__`: the recorder that wrote this |
| `collector_version` | `collector/VERSION`, the pin that re-encoded it (§4.5) |
| `started_at` / `ended_at` | the run's two ends, from the injected `now` (§3.6) |
| `bodies` | one entry per recorded body, `raw/` and `json/` and rejected alike (§3.5, §5.4) |
| `files` | one entry per **other** file in the run directory, `MANIFEST.json` excepted (§5.6) |
| `forwards` | one entry per attempted forward: delivery, not bytes (§4.5) |
| `problems` | what went wrong during the run — **absent** above because nothing did (§4.5, §4.6, §5.3) |

Nothing else. The manifest has no field for how many spans a capture holds, how
long an export was, which project the bytes came from beyond what the project's
own manifest says, or whether anything about the capture is good: the zoo counts
bodies and bytes (§1.4).

### 5.1 `zoo capture`'s two new options

```bash
zoo capture --project z4 --run-id 2026-10-09T12-00-00Z \
            --kind real \
            --project-manifest ../streaming-concierge/MANIFEST.json
```

| Option | Default | |
|---|---|---|
| `--kind` | **required** | `recorded` \| `real` (§5.2) |
| `--project-manifest` | **required** | path to the project's own `MANIFEST.json` (§5.3) |

Both are refusals when absent, before anything is started and before a
directory is made: a capture that cannot say what it is, or cannot carry the
document saying what produced it, is one to refuse while the operator can still
fix it — not one to discover at the end with bytes already on disk, which could
only be completed by editing a capture (`CLAUDE.md`, "Halt points").

### 5.2 `kind` is required, and is never inferred

A `recorded` capture and a `real` capture differ **only** by this declaration.
The bytes look the same, the layout is the same, the Collector is the same; what
differs is whether a real model answered, and nothing in the traffic says so in
a way the zoo is willing to read. So `kind` has no default, and is not inferred
— not from the project's own manifest, not from the endpoint, not from how long
the run took, not from whether a key was in the environment.

`recorded` means the run went against the key-free stub the contract requires
(`EXPORT-CONTRACT.md` §1, `make run-recorded`). `real` means it went against a
real model (`make run-real`). The audit (§7) reads this field as the truth about
which it was, and A5's report is organized by it, which is exactly why a guess
here would be a lie there.

An unknown value is refused the same way a missing one is: `zoo capture` has
`choices`, and `manifest.label` raises rather than writing a manifest it cannot
label.

### 5.3 The project's own manifest is copied, not merged and not validated

`EXPORT-CONTRACT.md` §1 tells every pet project to write a `MANIFEST.json`
recording the contract version, the framework and its version, the
instrumentation packages pinned, the SDK and exporter, the Python version and
platform, the model, `recorded` | `real`, the endpoint and the start time. That
document is **the** record of what made these bytes, written by the
implementer, and the zoo carries it **verbatim** under `project_manifest`.

The zoo does not re-derive any of it (it could not: it never sees the project's
environment), does not check it for required keys, does not reconcile it with
anything, and reads **no field of it** — including `mode`, which the contract
asks the project to record and which is **not** where `kind` comes from (§5.2).
If the project's `mode` and the capture's `kind` disagree, both are in the
record side by side and a reader can see the disagreement: the zoo records, and
improving the record is the one thing it must not do (§1.3).

The one thing checked at the start is that the path holds a readable JSON
**document**, because a document is what the manifest carries. A path that is
missing, unreadable or not JSON is a refusal at the start of the capture
(§5.1), with the path in the message — while nothing is on disk and the
operator can still fix the typo.

**The copy is taken when the run ends**, not when it starts. The contract has
the project write this file *while it runs* (`EXPORT-CONTRACT.md` §1), so the
document that is there at the start is the one the project's **previous** run
left behind, and the one that is there at the end is the recorded run's. A
capture that carried the earlier one would be making a claim about the run it
recorded that is not true, and a reader could not tell the two apart.

So the capture dates the document it finds, and this is the **one field of the
project's manifest the zoo reads**: `started_at`, compared against the
capture's own (§5.5), and read for this and nothing else. It is still not
copied anywhere, still not reconciled with anything, and `mode` is still not
where `kind` comes from (§5.2). Four outcomes:

| What is at the path when the run ends | `project_manifest` | `problems` |
|---|---|---|
| a JSON document whose `started_at` is at or after the capture's | the document, verbatim | — |
| nothing, or not a JSON document any more | `null` | one line, naming the path |
| a document whose `started_at` is **before** the capture's | `null` | one line, naming both times |
| a document with no `started_at` the zoo can read | the document, verbatim | one line, saying it could not be dated |

A stale document is dropped rather than carried, because a stale copy is worse
than none: a reader cannot tell it from a true one. An undatable document is
**kept**, because the zoo does not drop a record it was handed — and the
problem is recorded all the same, because a capture that cannot date its
project manifest is not a capture that is fine. Either way `zoo capture` exits
non-zero and `zoo verify` fails (§5.6): a capture is never silently fine.

Two timestamps from two clocks are compared here, which is the one comparison
this section permits and it is bounded: both are values that were *written
down*, no clock is read to make it, and a value that does not parse as an
ISO-8601 moment **with an offset** is not compared at all. Guessing a timezone
would be inventing a fact about somebody else's run.

The project's manifest describes the **project's run**; the zoo's own fields
describe the **capture**. They are two records of one event, and they are kept
apart on purpose: what the zoo claims — the pin, the digests, the two
timestamps, the declaration — it writes itself.

### 5.4 `content_type` and `content_encoding`

Every `bodies` entry carries the two headers the request made its claim with,
as the request sent them, and `null` where it sent neither: the zoo has no
content type of its own to invent (§3.3).

They are **carried across from `NNNN.headers.json`** when the run ends, not
observed by the sink as the POST arrives. That is the whole of why they can be
here without the sink acquiring a taste (§1.1): the values are already verbatim
in the record beside the body, and copying two of them into the manifest reads
no byte of any body. The header name is matched case-insensitively, because
HTTP says header names are; a header that legally repeats is carried **once**,
first-as-received, and `headers.json` stays the record of the repeat because it
is the record of the request.

A1's three keys are untouched: `file`, `sha256` and `bytes` mean exactly what
they meant, and `zoo verify`'s re-hash still reads only those. There is still
exactly one home for a digest (§3.5).

### 5.5 When each field is written

| When | Where | What |
|---|---|---|
| `zoo capture` starts, before a body can arrive | `MANIFEST.json` | `kind`, `sink_version`, `collector_version`, `started_at` |
| each POST, as it is recorded (§3.5) | `bodies.jsonl` | one line: `file`, `sha256`, `bytes` |
| each forward, as it completes (§4.5) | `forwards.jsonl` | one line |
| the Collector child is seen to have exited (§4.6) | `MANIFEST.json` | one `problems` entry |
| `zoo capture` stops, after both sinks and the Collector have | `MANIFEST.json` | `bodies` and `forwards` from the journals, each body entry's `content_type` / `content_encoding` (§5.4), `files`, `project_manifest` (§5.3), any further `problems`, and `ended_at` |

The declaration is written **first** so that a run stopped the hard way still
says what it was. The bodies go to a journal rather than into the document, so
that recording the sixteen-hundredth body costs what recording the first did
(§3.5). The assembly happens **after** the Collector has flushed and both sinks
are down, so the last `json/NNNN.json` is in `bodies` with its headers carried
like every other, and the digest of every file is the digest of the file as the
run left it.

**`ended_at` is written last, and nothing is written after it** — it is one
atomic write with everything above, and it is the last of them. That is what
lets `zoo verify` read its absence as a capture that was never completed
(§5.6) rather than as a field somebody forgot.

The assembly runs once per capture: `stop()` is also what a failed `start()`
unwinds through, and a capture that never got as far as a labelled manifest is
left with nothing written at all.

Both timestamps come from the injected `now` (§3.6) and from nowhere else, so a
test's manifest carries the values the test chose and `cli.py` stays the one
place the real clock enters the package.

### 5.6 `zoo verify`

```bash
zoo verify                                      # the capture root
zoo verify captures/z4/2026-10-09T12-00-00Z     # one run
```

`[path]` is a capture root **or one run directory**; a directory holding
`MANIFEST.json` or a `raw/` is a run. Both are accepted because both are typed:
globbing two levels down from a run directory would find nothing, say so, and
exit **zero** — a reassuring pass over a capture nobody checked, which is the
one failure mode this command exists to prevent (`CLAUDE.md`).

For every run it finds, `zoo verify` reads `MANIFEST.json` and then checks
**both directions**:

1. every file the manifest lists — in `bodies` and in `files` alike — is on
   disk, and its sha256 and its length are what the manifest recorded;
2. every file in the run directory is one the manifest accounts for, by an
   entry of its own. Only `MANIFEST.json` accounts for nothing, including
   itself.

Nothing is accounted for by sitting *beside* something that is listed. Each of
a request's two headers files has an entry and a digest of its own, because the
headers are the record of what the exporter claimed about its own bytes (§2.3):
a rewritten `Content-Type` in `NNNN.headers.json`, or a bare CR tidied out of
`NNNN.headers.raw`, changes what the capture says the request was, while every
body in it still hashes to what it hashed to. A check that covered only bodies
would call that capture verified.

The walk is also why `NNNN.headers.raw` needed nothing added to `verify` when
A3c introduced it: `files` is a walk of the run directory, so a capture is
covered whether or not a recorder announced a file.

It then checks three things the manifest says about itself:

- **`ended_at` is there.** A capture without one was never completed — the run
  was killed or died between its first body and its last line — and nothing
  says the manifest covers what is on disk. A capture is never edited
  (`CLAUDE.md`, "Halt points"), so the line names the directory and the
  command that removes it.
- **`kind` is one the spec names**, or is absent. `recorded`, `real`, or
  nothing at all for a `zoo sink` run that never declared one (below).
  Anything else is a declaration the audit would read as the truth and could
  not use (§5.2).
- **`problems` is empty or absent.** A run that recorded something going wrong
  which the capture could not fix does not pass a check whose whole job is
  trust. `zoo capture` already exited non-zero saying so; `verify` says it
  again, every time.

It exits non-zero, printing one line per problem, on any of those: a digest
that differs, a length that differs, a listed file that is missing, a **file on
disk that the manifest does not list**, a missing `ended_at`, a `kind` the spec
does not name, a recorded problem, and a manifest that is absent or unreadable.
A manifest it cannot read is a refusal, never a pass.

The second direction is why the check walks the **directory** and not only the
list. A verify that iterated the manifest can only ever confirm what the
manifest already says; it cannot notice a body nobody recorded, and would report
a capture with a file in it from somewhere else as verified. A capture is the
bytes that were recorded, so a file nothing recorded is a problem with the
capture even when every digest in it agrees.

`zoo verify` prints each run's `kind` as the capture declares it, and `none
declared` where it declares nothing — a `zoo sink` run (§3) records bodies and
digests and declares nothing, and inventing one for the line would be inventing
the one field the audit reads. `zoo sink` does assemble its manifest when it
stops, journal and `ended_at` and all, because a capture that was never
completed is not one `verify` can pass.

`make verify` is `zoo verify` over `captures/`, and `make check` depends on it:
the immutability claim is worth making only because something checks it on every
run. A tree with no captures at all is nothing to re-hash and exits zero.

### 5.7 What the manifest is not

It is not frozen (`CLAUDE.md`, "Nothing is frozen"): these field names will
change while the zoo is pre-release, and `schema_version` is deliberately
absent because a version on an unfrozen shape is a promise nobody is making
yet. What is durable is the **bytes** of a capture — and `bodies`' digests are
how that is checkable.

It is also not a summary, not an index and not an analysis. The audit (§7)
writes what a capture *means* to a receiver, in its own file, naming the
repository that owns each finding. The manifest says what arrived, when, how
big it was and what it hashed to.

## 6. The replayer — A4

`zoo replay`: re-send each body with its captured headers in receipt order,
adding nothing. Not specified yet.

## 7. The audit — A5

`zoo audit`: every capture through `spanweave_live serve` and `spanweave.build`,
with every divergence written up as a reproduction naming the repository that
owns it. The one module that may import either library (`tests/gates.py`). Not
specified yet.
