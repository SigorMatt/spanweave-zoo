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
zoo's CRLF split of them beside them -- see §2.3; A3f: the manifest is
sealed -- see §5 -- and that split replaced the stdlib's parse; A3g: the
split records the request line whole, the tee forwards the recorded head
octets rather than the stdlib's parse, and `SIGHUP` ends a capture as Ctrl-C
does); §6 is specified and implemented (A4: `zoo replay`, which re-sends a
capture's bytes and its captured head octets to another receiver and adds
nothing); §7 is specified and implemented (A5: `zoo audit`, which runs
`spanweave-live serve`, `spanweave.build` and `agentgolden`'s signature over a
capture and writes down what happened, naming the owner of every finding).

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
  and `spanweave_live` -- and `agentgolden`, the consumer the audit smokes
  (§7) -- are pinned by git sha in `pyproject.toml`'s `audit` extra, imported
  only by §7's module, and never changed from here.
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
        0001.headers.json       that same head split on CRLF (§2.3)
        0002.body
        0002.headers.raw
        0002.headers.json
        ...
    json/
        0001.json               the Collector's JSON re-encoding of 0001.body
        0001.headers.raw        the head the Collector sent it with, octet for octet
        0001.headers.json       that same head split on CRLF (§2.3)
        ...
    bodies.jsonl                one line per recorded body, written as it lands
    forwards.jsonl              one line per attempted forward to the Collector
    collector.log               the Collector's stdout and stderr, verbatim (§4.2)
    MANIFEST.json
```

`bodies.jsonl` and `forwards.jsonl` are the run's own notes, written as the run
goes and flushed line by line (§3.5). `MANIFEST.json` is assembled from them
when the run ends (§5.5), and lists a sha256 for **every** file above except
itself — the journals and both headers files included (§5.6) — and is sealed
by a digest of its own (§5).

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
- **`NNNN.headers.json` is the zoo's split of those same octets**, written
  for convenience and **derived from `NNNN.headers.raw` alone**, by the rule
  below. It is kept *beside* the octets, never instead of them, on the same
  rule as §2.4's `json/`: if the two disagree, the octets are what arrived.

It is **not** the stdlib's parse (A3f). Python's `http.server` parses the head
to handle the request — its `Content-Type` is echoed (§3.3), its path chooses
the directory (§3.4) — and that parse is still what the sink *handled* the
request with. Since A3g it is nothing more: the tee forwards the recorded
octets, not the parse (§4.3); and since B5d it frames nothing — a body is read
by the framing headers on *this* split (§3.7). It
is not what the record says the request carried, because it can say more than
the request did. A **bare CR inside a header value** is the case: HTTP forbids
it, real clients emit it, and `email`'s header parser splits the line on it.
For `X-Weird: a\rb` the parse says `X-Weird: a`; for
`User-Agent: otel\rX-Injected: yes` it says the request carried an
`X-Injected` header, which no client sent. A record that can assert a header
the client did not send is not a record (§1).

**The split.** The octets of `NNNN.headers.raw` are decoded as Latin-1 (one
character per octet, so nothing is replaced or lost) and split on **CRLF and on
nothing else**. A bare CR, or a bare LF, is inside the line it arrived in and
therefore inside the value. This rule was ratified by the maintainer on
2026-10-11 (`TASKS.md`, series 1's decisions log, "header rule"), with the request-line amendment
A3g implements.

- The **first line** is the request line, recorded **verbatim** under
  `request_line`, so nothing after the path — the HTTP version, or anything
  else — is dropped. `method` is what precedes its first space; `path` is what
  lies between that space and the next one (or the end of the line),
  verbatim, query string included.
- Every **later non-empty line** is a header if what precedes its first colon
  is a non-empty field-name token (RFC 9110 §5.6.2: letters, digits and
  ``!#$%&'*+-.^_`|~``). Its pair is `[name, value]`: the name as sent, the
  value as sent with the spaces and horizontal tabs around it removed (RFC
  9110 §5.5's optional whitespace, which is not part of a value) — a CR or LF
  inside it stays. Pairs are in the order received, repeats included.
- Every **other non-empty line** — a continuation line (RFC 9110's obsolete
  line folding), a line with no colon, a line whose name is not a token — is
  no header and is not joined to one. It is listed verbatim, in order, under
  `unparsed`, which is **absent** when there is none.
- **Empty lines** are the block's terminator and carry nothing.
- A head that holds **no CRLF at all** — every line of it ended by a bare LF,
  which the stdlib's reader accepts — is one line on this split, and the
  split finds no request line in it. Its text is the one `unparsed` entry,
  verbatim, and `request_line`, `method` and `path` are **absent**; `headers`
  is empty. Reading a method out of it would be splitting on LF, and listing
  nothing would omit the whole block without saying so — which is what this
  split did before A3g.

The split is a pure function of the octets: the same `NNNN.headers.raw` gives
the same `headers`, `request_line`, `method`, `path` and `unparsed` on any
machine. Because `NNNN.headers.json` is a derivation and the octets are the
record, a later rule may re-derive it from `NNNN.headers.raw` without touching
a capture; a capture taken under an earlier rule keeps the json it was taken
with (Z4's two captures of 2026-10-12 carry no `request_line`).

`NNNN.headers.json` is JSON with `sort_keys=True`: the request line, the
method, the path, every header the split produced, `unparsed` when there is
any, the body length in bytes, and the receipt time. The last two are the only things in it the octets
of the head do not carry. A1 (§3.2) wrote these key names and A3 kept them.
The manifest carries two of these values across — `Content-Type` and
`Content-Encoding` — so that a reader of one `bodies` entry knows what the
request claimed (§5.4); it reads them from this file, the first value the
request sent for each, and the octets remain the record of everything the
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
- **`NNNN.headers.json`**: that same head split on CRLF (§2.3), as JSON with
  `sort_keys=True`:

  ```json
  {
    "bytes": 1234,
    "headers": [["Content-Type", "application/x-protobuf"],
                ["Content-Encoding", "gzip"],
                ["User-Agent", "OTel-OTLP-Exporter-Python/1.37.0"]],
    "method": "POST",
    "path": "/v1/traces",
    "received_at": "2026-10-09T12:00:01.500000+00:00",
    "request_line": "POST /v1/traces HTTP/1.1"
  }
  ```

  `headers` is a **list of `[name, value]` pairs in the order received**, with
  names as sent and values as sent less the whitespace around them (§2.3),
  because a header may legally repeat and a JSON object would silently keep
  one of them. `request_line` is the request line whole (§2.3, A3g); `path` is
  the request target verbatim, query string included. `bytes` is the length of `NNNN.body` on
  disk. `received_at` comes from the injected `now` (§3.6) and is the only
  clock the record has. (§2.3: A1 wrote these key names and A3 kept them;
  §5.4 carries two of these values into the manifest and changes nothing here.)
  It is derived from `NNNN.headers.raw` and never from the stdlib's parse, so
  a bare CR in a value is inside that value here too (§2.3); the octets are
  still the file a reader believes.

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

A POST the sink **could not frame** (§3.7) gets that same answer with one
header more, **`Connection: close`**, and the connection is closed once the
answer is sent (B5, Q9; every case is §3.7's table, B5a, B5b, B5c). The sink decodes no framing, so after such a request
it does not know where the next one begins: kept alive, it read a chunked
body's chunks as a request line and answered a `400` no exporter asked for.
Closing records what it could see and guesses nothing about what follows
(the decision of 2026-10-12, B5(a)); a client with more to send opens a new
connection. Whether the answer says close depends on the framing headers the
request carried and never on its bytes.

A POST that reaches a sink after its journals have closed (§5.5) — `zoo
sink`'s or either of `zoo capture`'s — is not recorded, so it is **not
answered**: the connection is closed
with no status, since a `200` there would say "recorded" of a body the
capture does not hold.

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
| `open_file` | opens a path in a binary mode (`wb`, `ab`) and returns the file; the default is the real filesystem | every file the recorder opens to record a body goes through it, so a test can count what recording one body costs (below) |

**What a body costs** (B2b), the one definition the §3.5 claim "the same work
every time" is tested by: the files the recorder opens through `open_file`
while recording that body, in order, each as its **mode**, the **octets read**
from it and the **octets written** to it. Today that is four opens — the body,
`NNNN.headers.raw`, `NNNN.headers.json` (its `.partial`, §5) and the journal
append — and none reads. For bodies of equal length and a fixed `now`, the cost
of the 1,600th body of a run **equals** the cost of the first: a manifest
rewritten per POST writes more octets each time, and a rescan of the journal
reads more. Creating a directory and the rename that makes `headers.json`
atomic open nothing and are not counted. The recorder opens no file to record
a body other than through `open_file`; the test fails on any file under the
run that is opened some other way while it records, so a rescan cannot hide
behind the seam. The cost is a count and never a clock: wall-clock and CPU
time both grew with no code change on a shared runner (B2a, B2b), so no time
is asserted anywhere.

The sink never reads the clock, never sleeps, never binds a socket, never
opens a file to record a body and never draws a random number outside these.

### 3.7 What the sink never does

It never decodes, decompresses, parses or validates a body; never edits or
renumbers an existing capture; never drops a body it cannot make sense of;
never varies its answer by content; and never imports `spanweave` or
`spanweave_live` (`tests/gates.py`). A body that is empty, truncated,
mislabelled, double-compressed or not OTLP at all is recorded like any other,
because the zoo records what exporters send and never improves it (§1).

**The sink frames by the record's own parse** (B5d). The framing headers —
`Transfer-Encoding` and `Content-Length`, either in any case — are read from
§2.3's split of the recorded head, the one `NNNN.headers.json` shows: split on
CRLF only, a header a line whose text before its first colon is a token, a
value less the spaces and tabs around it. They are never read from the
stdlib's parse, which splits on a bare CR and a bare LF and so can see a
framing header the record does not show, or miss one it does. The record and
the framing then cannot disagree, and every case below is a case of this one
rule:

- `Content-Length:` LF ` 5` is one line on the split, valued LF ` 5` — not
  digits — although the stdlib's reader ends the line at the LF and joins
  ` 5` to it as a fold.
- `X: a` CR `Content-Length: 5` is one header, `X`, on the split, and no
  length — although `email`'s parser splits the line at the CR and finds a
  `Content-Length: 5`.
- `X: a` CR `Transfer-Encoding: chunked` beside a `Content-Length: 5` is no
  `Transfer-Encoding` on the split, so the request is framed by its `5`.
- A head with no CRLF at all (§2.3) has no headers on the split, so no
  `Content-Length`, and is unframed whatever its bare-LF lines say.

The sink reads the framing it was given and does not guess one it was not:
decoding a `Transfer-Encoding` is decoding. A POST whose body the sink cannot
read by its `Content-Length` alone is recorded as a **zero-byte** body with its
headers beside it, and answered like any other. What it could see is what the
capture says it saw, and the header that said so is in the record.

Such a POST is **unframed**: the sink cannot tell where its body ends, and so
where the next request on the connection begins. An unframed POST is answered
with `Connection: close`, and its connection is closed after the answer
(§3.3): nothing sent after it on that connection is read, recorded or
answered. A request carrying **any** `Transfer-Encoding` is unframed whatever
its `Content-Length` says — the two together are the request-smuggling shape,
and read by its length the sink would take the first octets of the chunk
frames as a body and the rest as a request nobody sent (B5a).

A `Content-Length` is **digits, once** (B5b; RFC 9110 §8.6, `1*DIGIT`). Its
value is its value on §2.3's split (B5d), less the spaces and horizontal tabs
around it — RFC 9110 §5.5's optional whitespace, which the split removes and
which is not part of a value. What remains must be one or more ASCII
digits `0`–`9` and nothing else: `+5`, `-3`, `5_0`, `5, 5`, a digit from
another script, or a `5` with any other whitespace beside it (a vertical tab,
a no-break space) is not a length, although Python's `int()` reads several
of them as one. A request carrying **more than one** `Content-Length` declares
a length only if every value is the same once that whitespace is removed —
then it is one length — and none if any two differ, whichever comes first.

A `Content-Length` **continued on a folded line** declares no length (B5c).
On §2.3's split of the recorded head, that is a `Content-Length` header line
(any case) followed by a line beginning with a space or a horizontal tab —
RFC 9112 §5.2's obsolete line folding. The stdlib's parse joins the fold into
the value: for `Content-Length:` CRLF ` 5` it reads `5`, while the record's
split says the header is empty and lists ` 5` as `unparsed`, part of no
header. A fold beside a length is a line the record holds and cannot place,
so the request is unframed whatever the split's own value reads as —
`Content-Length: 5` CRLF ` 0` too; `NNNN.headers.json` is the split as ever,
and the fold stays `unparsed`. A fold on any other header frames nothing and
changes nothing.

The table is every case, decided by the framing headers on the record's
split alone (B5d) and never by the bytes:

| `Transfer-Encoding` | `Content-Length` | Body recorded | Connection |
|---|---|---|---|
| present, any value | any, or absent | zero bytes | closed (unframed) |
| absent | absent | zero bytes | closed (unframed) |
| absent | not `1*DIGIT` (`five`, `+5`, `5_0`, `-3`, empty, …) | zero bytes | closed (unframed) |
| absent | repeated, two values differ | zero bytes | closed (unframed) |
| absent | continued on a folded line (obs-fold) | zero bytes | closed (unframed) |
| absent | repeated, every value the same | as for that one value | as for that one value |
| absent | `0` | zero bytes (an empty body) | kept |
| absent | positive *n* | the *n* octets declared | kept |

A `Content-Length: 0` with no `Transfer-Encoding` is a framing — an empty
body — and keeps its connection, as does a positive one. A negative length is
one case of "not `1*DIGIT`" (B5a decided it first).

It **binds and resolves no name**. `http.server`'s own bind follows with
`socket.getfqdn(host)` — a reverse lookup of the address it was just given,
which only a CGI or WSGI environment ever reads — and the sink's server skips
it: its `server_name` is the `--host` it was given, as given. A sink is a bind
and nothing else, and the lookup is not free: on a macOS CI runner the first
one in a process took tens of seconds, during which the process's own signal
handlers could not run, so a `zoo capture` started as its own process sat
silent past its first bind. `tests/test_sink.py` fails if binding a sink
resolves a name.

It **stops on `SIGINT`, `SIGTERM` and `SIGHUP` alike** (B2, Q6), the three
`zoo capture` stops on (§4.6): a supervisor ending a pet project's run sends
the second, a terminal going away the third, and left to their default action
either killed the sink before its manifest was assembled — bodies on disk and
no `ended_at`, a capture `zoo verify` rightly fails. Each ends the serving loop
the way Ctrl-C does: the handler only asks the server to shut down, the loop
returns, the listening socket is closed, and the manifest is assembled and
sealed (§5.5) before `zoo sink` exits.

It **seals the way `zoo capture` does** (B3a): close, then seal, with no
exception for the sink alone. Once the loop has returned and the listening
socket is closed, every POST the sink is still handling is waited for, for at
most the bound `zoo capture` gives its sinks (10 seconds, §4.6); then the
recorder **closes its journals**, and only then is the manifest assembled.
A POST still being handled at the close — a client whose body was still
arriving past the bound — is one `problems` entry naming the body it had
recorded or `a POST not yet recorded` (§5.5), printed after the stop line as

```text
zoo sink: stopped. <n> body/bodies.
  ! <the body, or a POST not yet recorded>: still being handled when the journals closed; what its handler had not yet written is not in this capture
```

and whatever that handler does afterwards is written nowhere and answered
nothing (§3.3). `zoo sink` exits **0** when the sealed manifest records no
problem and **1** when it records one — that one, or a journal line the
assembly could not read (§5.5) — printing each on a `!` line, as `zoo capture`
does: a capture `zoo verify` will fail (§5.6) does not end in a quiet 0.

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

The downloaded archive is kept in `collector/.cache/<asset>` — gitignored too —
so a second `make collector` re-uses it instead of fetching 100 MB again, and
CI restores it between runs. The cache changes nothing about the check: the
archive is **re-hashed on every run**, whether it came from the network or from
the cache, and **a cached archive whose digest is not the pin is refused
exactly as a downloaded one is**, naming the file to delete. A cache hit that
trusted its own file name would be a way of running an unpinned Collector while
`make collector` printed the pin. The download writes `<asset>.part` and
renames it only once the digest matches, so an interrupted fetch never becomes
the cache. `collector/fetch.py --print-pin` prints the two lines CI keys the
cache on — `asset=` and `sha256=`, read from the pin itself and touching no
network — which makes a `VERSION` or `SHA256SUMS` change a miss and a fresh
download rather than a stale hit.

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
port does too.

The Collector's log is the Collector's own, and it is **the run's, not the
terminal's**. Its stdout and stderr are one pipe, read by the zoo; the zoo
reads one line of it to know it is running (§4.6), and writes every byte of it,
verbatim and as it is written, to **`collector.log` in the run directory** —
the lines from before that directory existed included, because the zoo keeps
them until it does. It is a file in the run directory like any other, so it is
listed in `files` with a digest of its own and `zoo verify` re-hashes it
(§5.6). Nothing of it is echoed: the operator's terminal shows the zoo's own
lines and no Collector line. A refusal before the run directory exists quotes
the Collector's last lines in the refusal instead (§4.6), because there is no
directory to put a log in.

The zoo's own lines are these, and there are no others. Each `<...>` stands
for a value; everything else is printed as it stands here:

```text
zoo capture: the raw bytes are the record. Ctrl-C to stop.
zoo capture: recording POST /v1/traces on http://<host>:<port> -> <run>/raw/
zoo capture: collector <version> re-encoding to JSON into <run>/json/, via http://<host>:<port>
  <file>  <bytes> bytes  sha256:<the digest's first 12 hex digits>
  ! <file> recorded, NOT forwarded: <the error>
  ! <file> forwarded, collector said <status>
  ! collector exited: <code> -- the raw bytes are still being recorded, json/ is not (SPEC.md section 4.6)
  ! a forward was still waiting on the Collector after <seconds>s; stopping it anyway
  ! <the body, or a POST not yet recorded>: still being handled when the journals closed; what its handler had not yet written is not in this capture
  ! the Collector did not stop on SIGTERM and was sent SIGKILL: its last batch may not have reached json/
zoo capture: stopping
zoo capture: <n> body/bodies in raw/<, n in each other directory>, under <run>/, MANIFEST.json written: kind=<kind><what went wrong>
zoo capture: refusing to start: <why>
```

- The **readiness line** is printed once, first, and only once the run
  directory exists (§4.6); the **two lines after it** name the raw sink's
  port and directory and the Collector's version, the json sink's directory
  and its port. Each port is the one the sink actually bound, so under
  `--port 0` or `--json-port 0` these two lines are where it is read (§4.6).
- **One line per recorded body**, on either side, as it lands (§3.6's
  `after_record`): its file relative to the run directory, its length and the
  start of its digest. A single export prints two, one in `raw/` and one in
  `json/`.
- The **`!` lines** are the run's failures as they happen: a forward that did
  not happen or that the Collector answered with anything but a 2xx (§4.4), the
  Collector exiting on its own (§4.6), the two bounded waits of the
  shutdown running out (§4.6), and a POST still being handled when the
  journals closed (§5.5), which is also a `problems` entry.
- **`zoo capture: stopping`** is printed when the run is asked to end, after an
  empty line, so that it does not share a line with the `^C` a terminal
  echoes.
- The **summary** counts bodies by the directory they are in (§4.6), and goes
  on, when they happened, with `, <n> forward(s) FAILED -- json/ is
  incomplete and MANIFEST.json says which (SPEC.md section 4.4)` and one `,
  PROBLEM: <problem>` per problem (§4.5).
- **`refusing to start`** is the one line on stderr: the refusal before
  anything exists (§4.6, §5.1), naming the port or the cause.

`tests/test_shutdown.py` holds the list both ways: every line the code prints
in the runs it drives is one of these, and each of these is one it printed. `collector.log` is opened to be created, never to
overwrite or append: one already in the run directory is refused, like a body
already there (§3.1).

Series 1's A2 batch row named this exporter `otlphttp` (`TASKS.md`, A2's
resume note of 2026-10-09). At the pinned version that spelling is a
**deprecated alias** and the Collector says so on every start; the config uses
the current name, `otlp_http`, for the same component.

### 4.3 The tee: write first, then forward, byte for byte

The raw sink forwards every body it **accepts** (§3.2 — a POST to
`/v1/traces`) to the Collector, and the forward is **byte-identical**:

- the body is the bytes on disk, the same object that was written as
  `raw/NNNN.body`. Still gzipped if it arrived gzipped, still protobuf if it
  arrived as protobuf. The sink does not decompress, decode, re-encode or
  re-frame it to forward it, exactly as it does not to record it;
- the head is **the recorded head**: the octets of `raw/NNNN.headers.raw`
  (§2.3) — the request line, every header line in the order sent, repeats,
  spacing and line endings as they arrived — written onto the socket by the
  zoo, as the replay writes its head (§6.2), with two changes that name the
  connection rather than the payload, each a whole line of §2.3's split:
  - the **`Host` line** is substituted by §6.2's rule — the name as sent,
    `: `, and the Collector's `host:port`, an IPv6 literal bracketed as
    §6.2 says — because the destination has changed;
  - the **hop-by-hop header lines** are dropped with their CRLF, because
    they describe a connection the forward is not. Which lines those are is
    two rules, matched by field name in any case:
    - **the zoo's own list of nine names.** No source carries this list;
      each name is on it for its own reason (R-3):
      - `Connection` — RFC 9110 §7.6.1: the field that names this
        connection's options, which an intermediary removes once it has
        read them;
      - `Proxy-Connection`, `Keep-Alive`, `TE`, `Transfer-Encoding`,
        `Upgrade` — named by RFC 9110 §7.6.1 among the fields an
        intermediary removes before forwarding whether or not `Connection`
        lists them. `Proxy-Connection` is non-standard, and no origin
        should see it; `Keep-Alive` and `TE` are about the exporter's
        connection; `Transfer-Encoding` announces a framing the forward does
        not use (§3.7: the sink decodes no `Transfer-Encoding`, so a
        chunked POST is recorded, and forwarded, as a zero-byte body);
        `Upgrade` asks for a protocol switch
        on a connection the forward is not;
      - `Trailer`, `Proxy-Authenticate`, `Proxy-Authorization` — from RFC
        2616 §13.5.1's hop-by-hop list (`Trailer` there as "Trailers"),
        which RFC 9110 does not repeat. `Trailer` announces a trailer
        section, and since `Transfer-Encoding` is dropped none follows; the
        two `Proxy-` fields authenticate the exporter to a proxy, and the
        Collector is not one;
    - **the fields the head's `Connection` lines name.** RFC 9110 §7.6.1
      requires an intermediary to remove every field named as a
      connection-option in `Connection`. The value of every `Connection`
      header line in the head (all of them, if it repeats) is read as a
      comma-separated list: each item stripped of spaces and tabs, empty
      items ignored, compared in any case. A header line whose name is one
      of them is dropped, whatever the name — `X-Foo` in
      `Connection: X-Foo, keep-alive`, and equally a field the Collector
      needs, if a client names one: the client said it is hop-by-hop, and
      the Collector's answer to what is left is the forward's outcome. A
      `Connection:` that §2.3's split puts inside another line names
      nothing.

    These rules change only the **forwarded copy**. The recorded head —
    `raw/NNNN.headers.raw` and `NNNN.headers.json` — keeps every line,
    hop-by-hop or not: the head is the record.

  `Content-Type`, `Content-Encoding`, `Content-Length` and `User-Agent` go
  through untouched, because they are what the Collector needs in order to
  read the bytes the exporter actually sent. Every other octet goes as it
  came: a line §2.3's split lists under `unparsed` is not a header line and
  is neither dropped nor changed; a head that carried no `Host` gets none; a
  `Host:` or a hop-by-hop name after a bare LF is inside another line and is
  not touched; and a head with no CRLF at all is one line and goes unchanged.

**The head is the record, not the stdlib's parse** (A3g; the run-2b review,
N-7). Until A3g the forward sent the headers `http.server` parsed, through
`http.client` — and a bare CR made that parse assert a header no client sent
(§2.3): `User-Agent: otel\rContent-Encoding: gzip` reached the Collector as a
`Content-Encoding: gzip` of its own, the Collector answered `400` for a body
the record says declared no encoding, and the forward's outcome was a fact
about a request nobody made. The forward now sends what the record says
arrived, so whatever the Collector answers is an answer to that. A head HTTP
forbids goes as it arrived, as it does on replay (§6.2): a bare CR inside a
value is the client's, and the Collector's answer to it is a fact about the
Collector.

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

Then it serves until interrupted, and then it shuts down **in this order**,
which is the order that lets the Collector's last batch land:

1. **the raw sink stops accepting.** Nothing more will be recorded;
2. **every POST it is already handling finishes** — which is every forward the
   Collector has not yet answered — for at most a bounded wait (10 seconds,
   longer than the forward's own timeout, §4.4). What the Collector has
   answered is what its final flush can carry. A wait that runs out is said,
   and the shutdown goes on: a Collector that never answers must not become a
   capture that never stops;
3. **the Collector is looked at one last time, and then sent `SIGTERM`.** Its
   own shutdown flushes its last batch into the json sink, which is still
   serving. It is given a bounded wait (10 seconds) to exit, then **`SIGKILL`**
   and another bounded wait. A `SIGKILL` is said, because a killed Collector
   may not have flushed;
4. **every POST the raw sink is still handling is waited for again**, for at
   most the same bounded wait: the Collector's stop has just failed every
   forward still waiting on it, and this is where those failures reach
   `forwards.jsonl`. Then **the json sink stops**, once the requests it is
   handling have finished (the same bound);
5. **both recorders close their journals**, and **the manifest is assembled**
   (§5.5) — the journals, a digest for every other file, `collector.log`
   included, the project's own manifest copied as it stands now (§5.3),
   `ended_at` last. A POST still being handled at the close — one every
   bounded wait gave up on — is a `problems` entry naming its body, and
   nothing it does afterwards is written anywhere (§5.5).

It then prints what it recorded — the bodies **counted by the directory they
are in**, `1 body/bodies in raw/, 1 in json/`, `raw/` first and never summed
with the rest, because one export and its re-encoding are not two exports —
and exits non-zero if any forward failed (§4.4), the Collector exited on its
own (below), or the manifest could not be completed as asked (§5.3).

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

**A Collector that exits during the run** is recorded, not absorbed. "During
the run" is every moment **until `zoo capture` sends it `SIGTERM`**: at step 3
above, and not after. An exit noticed on any hop of the caller's wait, or at
the last look before `SIGTERM`, is a Collector that went on its own; an exit
after `SIGTERM` — or after the `SIGKILL` that follows it — is the one
`zoo capture` asked for, and is **not** a problem. The caller's wait notices an
exit on its next hop, writes
`problems: ["collector exited: <code>"]` into `MANIFEST.json` there and then
(§4.5), prints it, and `zoo capture` exits non-zero. It is recorded once,
however often it is looked at. The raw sink keeps recording, because the raw
bytes are the record and an exporter still exporting must still be recorded;
what has stopped is the re-encoding, and the manifest says so rather than
leaving an operator to find a `json/` that quietly stopped filling. `zoo
verify` fails on any capture whose manifest records a problem (§5.6), so a
capture nobody can trust does not pass the check whose whole job is trust.

**The Collector child runs in its own session**, and so in its own process
group. A terminal does not send Ctrl-C to a process: it sends `SIGINT` to its
whole foreground process group. A Collector in `zoo capture`'s group heard the
keystroke itself, shut down on its own, and was then recorded as a Collector
that had exited — a clean capture failed for good by the one way the README
says to end it. In its own session only `zoo capture` hears Ctrl-C, and the
Collector is stopped by `zoo capture`, in the order above. The cost is stated
rather than hidden: a `zoo capture` killed with `SIGKILL` cannot stop its
Collector, which is then left running, holding its ports, until it is stopped by
hand.

**`SIGINT`, `SIGTERM` and `SIGHUP` all end a run**, through a handler that
only asks it to stop; the shutdown itself happens on the main thread, which is
where the Collector gets stopped rather than orphaned holding its port.
`SIGHUP` is the terminal going away — its window closed, its ssh session
dropped — and the kernel sends it to the foreground process group, which the
Collector, in its own session, is not in. Left to its default action it killed
`zoo capture` alone: the manifest was never completed and the Collector was
left running, holding its port (run-2b review, N-2). It is handled as Ctrl-C
is, and a line written to the terminal that hung up — which fails with `EIO`
rather than `EPIPE` — is the closed stdout above by another errno: the run is
already ending, and the line goes nowhere. This is installed
rather than relied upon, and the caller waits in short hops rather than once
and forever: a capture has three threads blocked in `select`, the kernel may
hand the signal to any of them, and a main thread parked in an untimed wait
never runs the Python handler that would have noticed. A run that cannot be
stopped with Ctrl-C is not a detail — it is a Collector left holding 4320 and
an operator who has to find it.

**The handler is installed before `zoo capture` starts anything**, and so
covers the readiness wait, which can last most of a minute (B2, Q1). Until the
run directory is about to be made, a stop signal **ends the start**: the
readiness wait is abandoned, the Collector child — already started, in its own
session, and so deaf to whatever ended its parent — is stopped as it would be
at the end of a run, both sinks are closed, and `zoo capture` exits **2**
with `zoo capture: refusing to start: <signal> arrived before the capture was
ready …` and **no run directory**: a start that was stopped is a refusal, and
writes nothing a refusal would not. From the moment the directory is made the
handler only asks the run to stop, as it does during the run: the start
finishes, the readiness line is printed, and the shutdown above follows
straight away, so a stop signal never leaves a run directory behind whose
manifest was not completed. A second signal while the first is still unwinding the
start only asks again; it does not interrupt the stopping of the Collector.

**Every step of the start after the Collector is up is inside the same unwind**
(B2, Q8): keeping its log, reading the clock, labelling the manifest, setting
the sinks serving and printing the readiness line. Any of them failing stops
the Collector and closes both sinks before the failure propagates, and a
manifest that was already labelled is completed (§5.5). A directory made before
the failure is left as it is — the zoo deletes nothing it wrote — and a run
directory with no `ended_at` is one `zoo verify` fails (§5.6).

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

**`0` for either sink is a port the kernel chooses.** `--port 0` and
`--json-port 0` bind whatever free port the sink is given, and the two lines
after the readiness line (§4.2) name the port each one got — a script, or the
test suite, that passes `0` reads them there. `--collector-port` is not given
that meaning: the forward and the child are both told the Collector's port
before the child exists, so `zoo capture` picks no port of its own and names
the one it was given in any refusal (`OPEN_QUESTIONS.md` §6). A test harness
that picks one, and loses it to something else before the Collector binds it,
gets §4.6's refusal like anyone else; retrying is the harness's business, not
the zoo's.

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
| `forward` | called with the request's recorded head octets (`NNNN.headers.raw`, §2.3) and its body once both are on disk; returns the forwarded request's HTTP status or raises | one of the package's two outbound sockets, with §6.2's `send`. A test drives the tee with a forward that records what it was handed, so the tee's mechanics need no Collector |
| `launch` | called with the resolved config, environment and ports; returns a handle that can be stopped — saying whether it took a `SIGKILL` — **asked whether the child is still there**, and told where to keep the child's log once the run directory exists | starting a process is touching the world. A test passes a launcher that starts nothing, reports the pinned version, and can say the child exited — which is how §4.6's mid-run failure is driven without killing anything |
| `sleep` | the readiness wait between looks, a bounded number of them | no module under `spanweave_zoo/` reads a clock or sleeps on its own (`CLAUDE.md`); `cli.py` passes the one real `sleep`, as it passes the one real `now` |
| `after_forward` | called with each forward's outcome once it is in the manifest | one printed line per forward, and the way a test observes a forward without polling a file |

### 4.9 The Collector in CI, and locally

The integration test — a hand-built OTLP protobuf export through the tee into
the real binary, asserting `json/0001.json` is OTLP JSON carrying **the same
trace and span ids** — runs when `collector/otelcol-contrib` is present and is
**skipped when it is absent**, which is how it behaves on CI's five `check`
legs: none of them downloads a 100 MB binary. `make check` is therefore green
both with the binary and without it, and on a developer machine that has run
`make collector` it is green having actually run the Collector.

What holds in CI without the binary: the config and the pin are asserted as
text, the tee's mechanics are asserted against the `forward` seam,
`collector_version` in the manifest is asserted equal to `collector/VERSION`
through the `launch` seam, and §4.6's readiness and refusals are asserted
against a **stand-in child process** — a few lines that bind the receiver
endpoint they are given through `ZOO_COLLECTOR_OTLP_HTTP` and log the way the
Collector does. It stands in for the Collector's *lifecycle*, which is all
readiness is about: a port it cannot have, a ready line it does or does not
log, a config it cannot load — and, since A3e, how it ends: a stand-in that
logs which signal stopped it, as the stock Collector does, is what lets a test
send `SIGINT` to the **process group** of a real `zoo capture` process, as a
terminal does, and read in `collector.log` that the Collector got `SIGTERM` from
the zoo rather than the keystroke. The same test runs against the stock binary
as a `needs_collector` test. It stands in for no re-encoding, which is the one
thing it is not allowed to claim. What only a machine with the binary proves is that a
real protobuf export comes back as JSON with the same ids — and a test that
quietly passed without proving it would be the kind of reassuring pass this
repository exists to refuse (`CLAUDE.md`). It skips loudly instead.

**A skip is honest, and it is not enough.** `pytest` exits `0` when every
selected test skips, so a leg on which all of them skipped is, in a green tick,
indistinguishable from a leg on which all of them passed — and for five legs
the claim was therefore only ever *checked* on a machine that happened to have
run `make collector`, the maintainer's. So:

- the tests that need the binary carry the **`needs_collector` marker** as well
  as the skip. The marker is registered in `pyproject.toml` and is the name
  `-m` selects by; a bare `skipif` has no name to select by;
- **`make collector-check`** runs exactly `-m needs_collector`, reads pytest's
  own junit-xml report rather than its summary prose, and **exits non-zero if
  any selected test skipped**, failed or errored — *and* if the marker selected
  **no test at all**, which is how a renamed marker or a dropped decorator
  would otherwise turn the check into a no-op that passes. It is not a
  prerequisite of `check`, which must stay green with no binary;
- CI has a **sixth leg, `collector (ubuntu-latest)`**: one interpreter, `make
  collector` with the archive cached by the sha256 that pins it (§4.1), then
  `make collector-check`. It is the only job that downloads the binary, and the
  only job that can say the stock Collector re-encoded anything.

The guard's verdict is a pure function of the report text, so it is run against
planted reports — a skip, an empty run, a failure, an error — in
`tests/test_collector_ci.py`: a guard nobody has watched fail is a guard nobody
knows works.

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
    {"bytes": 2730, "file": "collector.log", "sha256": "0d5e17..."},
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
  "seal": "6016b6...",
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
| `seal` | the sha256 of this document's canonical JSON with `seal` absent (below) |

**The seal.** A capture's manifest carries `seal`: the sha256, as lowercase
hex, of the manifest's **canonical JSON with the `seal` key absent**. Canonical
means exactly the bytes of

```python
json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
```

over the document as `json.loads` reads it from `MANIFEST.json`: keys sorted
by code point at every level, no whitespace between tokens, every character
outside ASCII written as a `\uXXXX` escape (a UTF-16 surrogate pair beyond the
BMP), so the text is ASCII and its encoding is not a choice; numbers as
Python's `json` writes them. Every parameter is pinned rather than defaulted,
so the bytes are the same on any platform and in any locale. What is sealed is
the document and not the file: re-indenting `MANIFEST.json` changes no claim
and no seal, and changing any value — `kind`, a `problems` line, an entry of
`bodies`, `files` or `forwards`, `project_manifest`, a timestamp — changes the
seal it should carry. `zoo verify` recomputes it (§5.6).

The seal is what makes an edit to the manifest's own claims show. The file
digests cover every other file, but nothing covered the manifest: `kind`
flipped between the two values the spec names, a `problems` line deleted, or a
`files` entry rewritten together with the file it describes all left every
digest agreeing.

**What the seal is, and no more** (the decision of 2026-10-11, "the seal"). It
catches accidental and incidental edits — a hand edit, a tool that rewrote a
field, a merge that kept the wrong side — because any of them leaves a seal
that no longer matches. It is **not authentication**: it is a digest anyone
can compute, so a manifest edited and then **resealed by hand verifies**, and
`tests/test_manifest.py` holds that limit so this text cannot drift back into
promising more. Nothing here proves who wrote a manifest, or when.

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

**`file` is a normalized relative path under the run directory** (B4), in
`bodies` and `files` alike: POSIX separators, not absolute, no empty, `.` or
`..` part — `raw/0001.body`, never `./raw/0001.body`, `raw/../raw/0001.body`
or `/somewhere/0001.body` — and naming, with symlinks followed, a file inside
the run directory. The zoo writes entries only of this shape — `bodies` from
the names the sink gave its files, `files` from the walk — so the rule exists for every
reader of the manifest: `zoo verify` (§5.6), `zoo replay` (§6.1, B4a) and,
through `verify`, `zoo audit` (§7.2), each of which reads the entry as a claim
and not as an instruction. One function holds it, and all three apply it. An
entry that breaks it is a problem naming the entry, and the file it points at
is **not read**: a manifest that could send the re-hash anywhere on the disk
would let a capture be "verified" by bytes it does not hold. This confines
*where* the seal's claims can point, not *whether* a resealed manifest
verifies (§5, "What the seal is, and no more"): within the run directory, it
still does.

### 5.5 When each field is written

| When | Where | What |
|---|---|---|
| `zoo capture` starts, before a body can arrive | `MANIFEST.json` | `kind`, `sink_version`, `collector_version`, `started_at` |
| each POST, as it is recorded (§3.5) | `bodies.jsonl` | one line: `file`, `sha256`, `bytes` |
| each forward, as it completes (§4.5) | `forwards.jsonl` | one line |
| the Collector child is seen to have exited (§4.6) | `MANIFEST.json` | one `problems` entry |
| the run directory is made, before the manifest is labelled (§4.2) | `collector.log` | the Collector's output so far, and then each line as it is written |
| `zoo capture` stops, after both sinks and the Collector have (§4.6); `zoo sink` stops (§3.7) | `MANIFEST.json` | one `problems` entry per POST still being handled when the journals close (below); then `bodies` and `forwards` from the journals, each body entry's `content_type` / `content_encoding` (§5.4), `files` — `collector.log` among them — `project_manifest` (§5.3), any further `problems`, `ended_at`, and `seal` |

The declaration is written **first** so that a run stopped the hard way still
says what it was. The bodies go to a journal rather than into the document, so
that recording the sixteen-hundredth body costs what recording the first did
(§3.5). The assembly happens **after** the Collector has flushed and both sinks
are down, so the last `json/NNNN.json` is in `bodies` with its headers carried
like every other, and the digest of every file is the digest of the file as the
run left it.

**`ended_at` is written last, and nothing is written after it** but the seal —
it is one atomic write with everything above, and it is the last field of
them; `seal` is computed over that whole document, `ended_at` included, and
goes into the same write. That is what lets `zoo verify` read the absence of
`ended_at` as a capture that was never completed (§5.6) rather than as a field
somebody forgot, and the seal as covering everything the run wrote. A run
stopped the hard way has neither. `zoo sink` assembles its manifest the same
way when it stops, so its captures are sealed too.

**Writing ends before the seal, not at it.** The seal covers the files as the
run left them, so nothing may be written into the run directory once the
assembly has read them. `zoo capture` therefore **closes both recorders'
journals** after the last bounded wait of its shutdown (§4.6) and before it
assembles, and `zoo sink` closes its one recorder's the same way, after its
own bounded wait (§3.7; B3a): from then on a recorder refuses every write — a body that arrives
on a connection still open is recorded nowhere and answered nothing, the
connection closed, because any status would say it was received into a
capture that does not hold it; a forward that completes is journalled nowhere
and is in no list. A POST still being handled at the close — a forward the
Collector held past every bound, or under `zoo sink` a body still arriving
past the bound — is one `problems` entry, written before the
assembly, naming the body it had recorded (`raw/0001.body: still being handled
when the journals closed; …`), or `a POST not yet recorded` when it had
recorded none: what that handler had yet to write is not in the capture, and
the capture says so rather than letting a late line break every digest after
the fact. So a capture whose forward outlived the shutdown is sealed, every
digest holds, and `zoo verify` (§5.6) names the one problem the run recorded.

**A journal line that cannot be read is a problem, not an abort.** The
journals are decoded a line at a time: a line that is not UTF-8, or not a JSON
object, is a `problems` entry naming the journal and the line (`bodies.jsonl
line 2 is not UTF-8, so what it recorded is not listed in MANIFEST.json`), the
lines around it are read as usual, and the assembly goes on to write
`ended_at` and the seal. The file it was the record of is still on disk and is
covered by `files` (§5.6), so nothing is unaccounted for and nothing is
claimed; a capture whose own note could not be read is a reportable outcome,
and one left without `ended_at` by it would not be.

The assembly runs once per capture: `stop()` is also what a failed `start()`
unwinds through — a failure at any step of it, the steps after the label
included (§4.6), and a capture that never got as far as a labelled manifest is
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

A path that is **not a capture** is that same failure mode by another route,
so it is a refusal: `zoo verify <path>` on a directory that does not exist, on
a file, or on a directory that holds no `MANIFEST.json`, no `raw/` and no
`<project>/<run-id>` under it prints one line **naming the path** and exits
**2**. Two is the status, and not 1, because nothing was checked — the same
distinction `zoo capture` and `zoo sink` already make between a run that
refused to start and a run that went wrong (§4.6). A typed path is a claim
that a capture is there, and a typo must not read as a clean bill of health.

The **default** root is the one exception and the only place emptiness passes:
with no `[path]` at all, a `captures/` that is absent or holds no run is
nothing to re-hash and exits **0**. That is a repository that has recorded no
captures yet, which this one was until Z4's, and is why `make verify` also
names a capture it can actually read (below).

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

It then checks the manifest itself, and three things it says about itself:

- **The seal is the one its contents hash to** (§5). `seal` is recomputed
  from the document as read — canonical JSON, `seal` absent — and a seal that
  is absent, that is not that string, or that differs is a failure. Absent is
  not "nothing to check": a manifest nothing vouches for is not verified,
  and removing the seal must not be the way round it. This is the check that
  sees an edit no file digest can: `kind` flipped from `recorded` to `real`,
  a `problems` entry removed, a `files` entry rewritten along with its file.

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
  again, every time. This is also how a capture whose forward outlived the
  shutdown fails (§5.5): by the one problem the run recorded, and never by a
  digest or a seal, because nothing was written after the seal for either to
  disagree with.

It exits non-zero, printing one line per problem, on any of those: a digest
that differs, a length that differs, a listed file that is missing, a **file on
disk that the manifest does not list**, a seal that is absent or differs, a
missing `ended_at`, a `kind` the spec does not name, a recorded problem, and a
manifest that is absent or unreadable.
A manifest it cannot read is a refusal, never a pass.

Two more, both about the manifest's shape rather than the capture's bytes
(B4). A `files` or `problems` that is present and **not a list** is a line
saying so, never a crash: a `files` that is not a list accounts for no file,
so every file on disk is also unlisted; a `problems` that is not a list is a
problem in itself, because what the run recorded going wrong cannot be read
(a `bodies` that is not a list is already a manifest that cannot be read).
And a `file` entry that is not a normalized relative path under the run
directory (§5.4) — absolute, with a `..`, or a symlink resolving outside it —
is a line naming the entry, and that file is not read.

The second direction is why the check walks the **directory** and not only the
list. A verify that iterated the manifest can only ever confirm what the
manifest already says; it cannot notice a body nobody recorded, and would report
a capture with a file in it from somewhere else as verified. A capture is the
bytes that were recorded, so a file nothing recorded is a problem with the
capture even when every digest in it agrees.

`zoo verify` prints each run's bodies counted by the directory they are in
(§4.6), and its `kind` as the capture declares it, and `none
declared` where it declares nothing — a `zoo sink` run (§3) records bodies and
digests and declares nothing, and inventing one for the line would be inventing
the one field the audit reads. `zoo sink` does assemble its manifest when it
stops, journal and `ended_at` and all, because a capture that was never
completed is not one `verify` can pass.

`make verify` is `zoo verify` over `captures/` **and then over
`tests/fixtures/capture/`**, and `make check` depends on it: the immutability
claim is worth making only because something checks it on every run. A tree
with no captures at all is nothing to re-hash and exits zero — which is what
`captures/` was in this repository until Z4's first captures were committed,
and is what it is in any checkout without them — and a gate that re-hashes
nothing on every CI leg is a line in a log rather than a check. So one real
capture is committed
under `tests/fixtures/capture/`: a single OTLP protobuf body through the real
tee — the hand-built export of `tests/otlp.py` into the raw sink, the stock
Collector behind it, its JSON re-encoding into the json sink — with both
headers files on each side, both journals and the manifest the run assembled,
and the Collector's `collector.log`, on a clock the run chose. It is a capture,
so it is never edited (`CLAUDE.md`, "Halt points"); and it is deliberately not
under `captures/`, which is where the zoo's own recorded runs go. It has been
**regenerated twice**, each time as a new run through the same tee and never
as an edit of the one before, its two bodies byte-identical every time: by
A3f, because the decision of 2026-10-11 ("the seal") gave every capture a seal
and a capture is sealed when it is taken or not at all; and by A3g, because
the ratified header rule (§2.3) gave its `headers.json` files a `request_line`
they did not have, and a fixture whose json is not the split of its own octets
would hold `tests/test_fixture_capture.py` to a rule that is no longer the
rule. The zoo's own captures under `captures/` are never regenerated for a
new rule (§2.3). A fixture that went missing makes `make verify` exit 2 by the
rule above, rather than quietly checking nothing again.

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

## 6. The replayer

```bash
zoo replay captures/z4/2026-10-10T09-00-00Z --to http://127.0.0.1:4318
zoo replay captures/z4/2026-10-10T09-00-00Z --to http://127.0.0.1:8080 --json --timing
```

Re-send each recorded body to another receiver with its captured head, in
receipt order, **adding nothing** (`CLAUDE.md` §0.6 rule 5). It writes the
captured head octets onto a socket itself, with only the `Host` line
substituted, and then the body (§6.2). It goes through neither `http.client` nor the
stdlib's parse — `http.client` writes a head of its own from the pieces it is
handed, and a replay is a claim about the head (the decision of 2026-10-11,
"replay"). Since A3g the tee's forward (§4.3) sends the recorded octets by the
same rule, and differs from a replay in one thing: it drops the hop-by-hop
lines, because a forward to the Collector is a way to get a body re-encoded
and not a claim about the exporter's connection.

The replayer is what makes a capture usable by a receiver that was not there
when it was recorded — the audit (§7) is its first caller, and it sends the
same capture to `spanweave-live serve` twice, once as the exporter's own bytes
and once as the Collector's JSON. So a replay says nothing about what the
receiver did with the bytes beyond the status it answered with: a `415` is an
answer, not an error, and what it *means* is the audit's to write down.

| Option | Default | |
|---|---|---|
| `--to` | **required** | `http://host[:port]`, the receiver. `http` only; no path, because the request target comes from the capture |
| `--raw` / `--json` | `--raw` | which side of the capture to send: the exporter's own bytes under `raw/`, or the Collector's re-encoding under `json/` (§2.4) |
| `--timing` | off | sleep the recorded inter-arrival gaps (§6.3) |

### 6.1 What is sent, in what order

The bodies are the `bodies` entries of the run's `MANIFEST.json` whose `file`
is in the chosen directory, in the order the manifest lists them — which is the
order the journal was written, which is receipt order (§2.2, §3.5). The order
is read from the record rather than recovered from the file names: `NNNN` is
receipt order because a recorder assigned it in receipt order, and a replayer
that sorted the directory would be re-deriving a fact the capture already
states.

Nothing else is sent. A `rejected/` body (§3.4) was aimed at another path and
is not in either directory; re-sending it would be the zoo inventing traffic,
which is what §4.3 already refuses for the same bytes.

The body is **the bytes on disk**, as they are: still gzipped if it was
recorded gzipped, still protobuf if it was recorded as protobuf. Nothing here
decompresses, decodes, re-encodes or re-frames, and nothing here reads a byte
of a body for any purpose other than sending it.

A capture with no body in the chosen directory sends nothing, and that is a
refusal rather than a success: one line naming the path and the directory, exit
**2**. `--json` on a capture whose Collector never ran (§2.4) is exactly this,
and a replay that sent nothing must not read as a replay that worked
(`CLAUDE.md`, "Honest refusal beats a reassuring pass"). The same **2** is a
path that is not a capture, or one whose `MANIFEST.json` is absent or
unreadable, on §5.6's rule: nothing was sent.

**Replay trusts a manifest's paths only as far as `verify` would** (B4a).
Before it reads a body or a head, the replayer applies §5.4's rule — the same
function `verify` uses — to every `file` entry of `bodies` and of `files`: an
entry that is absolute, is not a normalized relative path (a `..`, a `.`, an
empty part), or resolves, symlinks followed, outside the run directory is a
refusal naming the entry, exit **2**, nothing read and nothing sent. It
checks **both sides**, the one it sends and the one it does not, and the
`files` list beside them: a manifest is one document, and one claim pointing
out of the run makes all of it untrusted (decided 2026-10-13,
`OPEN_QUESTIONS.md` §7). Without it, `raw/../../elsewhere.body` passed the
`raw/` filter above and a file outside the capture was sent as if recorded.

### 6.2 The head is the captured octets, with the `Host` line substituted

Each request's head is its **`NNNN.headers.raw`** — the request line and the
header block as the octets arrived (§2.3) — and **not** `NNNN.headers.json`,
and not a head rebuilt from either. That is the whole of why A3c kept the
octets: a parse is what some parser could represent, and a replayer built on
one sends a tidied request that no exporter sent, with the capture it claimed
to be replaying sitting on disk next to it saying otherwise.

What goes out on one connection is those octets with **one** line substituted,
then the body, and nothing else:

- **The `Host` line.** The lines are §2.3's — the octets split on CRLF and on
  nothing else — and a `Host` line is a line after the request line and before
  the empty line whose field name (§2.3's token rule) is `Host` in any case. It
  becomes the name as sent, `: `, and the `--to` destination as `host:port`;
  its CRLF stays. A host that is an IPv6 literal is written in brackets, as
  RFC 9110 §7.2 and RFC 3986 §3.2.2 write one — `--to http://[::1]:4318`
  names `Host: [::1]:4318` — because unbracketed its colons cannot be told
  from the port's (B5, Q11). Every such line is substituted, so a head that carried two
  names the destination in both. A head that carried **none** gets none —
  adding a header is adding something — and a `Host:` that §2.3's split puts
  inside another line (after a bare LF, or in a head whose every line ends in
  a bare LF) is inside that line and is not touched, exactly as
  `NNNN.headers.json` does not list it.
- **Everything else as captured, octet for octet**: the request line (an
  `HTTP/1.0` stays `HTTP/1.0`), the headers in the order sent, repeats
  included, each name and value with the spacing it had, every line ending as
  it was (a bare LF stays a bare LF), and the hop-by-hop headers too — unlike
  the tee's forward, which drops the zoo's list and what `Connection` names
  (§4.3), the replay does not drop them,
  because they are octets of the head the exporter sent and the replay is a
  claim about that head.

So the replayed head is **byte-identical to `NNNN.headers.raw` except the
`Host` line**, and a test holds that by replaying into a fresh `zoo sink`,
whose own `NNNN.headers.raw` is what actually crossed the socket — for a
captured head with `Host` not first, with no space after a colon, with
`HTTP/1.0`, with bare-LF line endings, and with hop-by-hop headers, each of
which a replay through `http.client` changed.

A head **HTTP forbids** goes out as it arrived. A bare CR inside a value is
the case: it arrived on a socket, so it goes out on one, and the receiver's
answer to it is a fact about the receiver. The same holds for a head whose
framing the recorded body does not match — a `Transfer-Encoding: chunked`
POST is recorded with a zero-byte body (§3.7). What happens next is the
receiver's: one that reads the framing waits for chunks that never come — the
stock Collector does — and the timeout that follows counts as not sent
(§6.4); one that does not, a `zoo sink` among them, reads no body and answers
`200`, recording a zero-byte body again. Either is a fact about the receiver,
and the replay sends the same octets to both.

**`--json`.** `json/NNNN.json` is a body the Collector POSTed to the json
sink, and that sink recorded the Collector's head beside it as
`json/NNNN.headers.raw` by the same rule as the raw side's (§2.3, §4.5). So
"the head as the Collector sent it" is that file, octet for octet, and
`--json` replays it by the same rule: those octets with the `Host` line
substituted, then the body. Nothing about it is reconstructed from the raw
side's head or from the Collector's configuration; a `json/` body whose
`NNNN.headers.raw` is absent is a head that cannot be read (below).

A head that **is not one** is not sent and is not mended into one. A
`NNNN.headers.raw` that is missing or unreadable, that is empty, or that does
not end with the empty line closing a header block (a CRLF or a bare LF after
the last line's ending) is one line naming the file and the reason, the rest
of the capture still sent, and a non-zero exit (§6.4): a body written after a
head that never ended would arrive as more of the head, which is a request no
exporter made. The sink never records such a head; a capture holding one was
made some other way.

**The `send` seam.** The send is injected, like §4.8's `forward`: called with
one request's captured head octets and its body, it returns the answer's
status or raises. `cli.py` passes the real one, which substitutes the `Host`
line and writes the octets on a socket it connects to `--to`, and reads the
answer with the stdlib's response parser so that it is framed and the
connection ends cleanly; a test passes one that records what it was handed.
Together with §4.8's `forward` it is the only outbound socket in the package.

### 6.3 `--timing`

Without `--timing` the bodies go out back to back, as fast as the receiver
accepts them. With it, before each body after the first, the replayer sleeps
the gap between that body's receipt time and the previous one's — so a receiver
sees the export pattern the exporter actually had, batches and bursts included.

"The previous one" is the body before it **in the capture**, whether or not
that body was sent. A body whose head cannot be read (§6.2) is not sent, but
the sink still received it when its `received_at` says, so the next gap is
measured from that receipt (B5, Q3): skipping the first body does not cost
the second its gap, and skipping a middle one does not stretch the next gap
back to the body before it. A skipped body with no readable `received_at`
leaves the next gap one that cannot be computed (below), rather than one
measured from an earlier body.

The receipt times come from `NNNN.headers.json`'s `received_at`, which is the
one thing in that file the request did not say: it is the sink's own note of
when the body landed, written from the injected `now` (§3.2, §3.6), and the
octets are the record of the request alone. Reading it is not reading a body.

The sleep is an **injected seam**, like the clock and the Collector's readiness
wait (§3.6, §4.8): `cli.py` passes the one real `time.sleep` and a test passes
its own, so the suite never waits for anything and a slept gap is a value a
test can assert. Nothing under `spanweave_zoo/` sleeps outside it.

A gap the replayer cannot compute is **not slept, and not guessed**: a
`received_at` that is missing, that is not an ISO-8601 moment with an offset
(§5.3's bound, for §5.3's reason — guessing a timezone invents a fact about
somebody else's run), or that is earlier than the one before it. Each is one
printed line, and the send still happens.

It does not change the exit status. The replayer's claim is about the bytes and
the headers, and those went out as captured; `--timing` shapes a replay and
never shapes a request, so a gap nobody could compute is a note on the replay
and not a failure of it. The lines are there so that a replay of an unknown
shape cannot be mistaken for a faithful one.

### 6.4 What it prints, and what it exits

One line per body as it is sent — the file, the status, the length — flushed as
it is written, for §4.6's reason: an operator replaying a long capture watches
it go rather than waiting for the end.

**A send that does not succeed never stops the rest.** Every remaining body is
still sent, and the exit status says afterwards. A receiver that refuses the
third export of a capture is a fact about that receiver, and a replay that
stopped there would hide what it would have done with the fourth — which is
exactly what the audit (§7) is for, and why a `415` on a protobuf body is a
finding and not an error (`CLAUDE.md` §0.6 rule 7).

| Exit | When |
|---|---|
| **0** | every body was sent and every answer was a 2xx |
| **1** | any answer was not a 2xx, or any body could not be sent at all — a head that is missing, empty or unterminated (§6.2), a body file the manifest lists that is not on disk, a connection that failed or an answer that never came |
| **2** | nothing was sent: the path is not a capture, its manifest is unreadable, it names a file outside the run directory (§6.1), or it holds no body in the chosen directory |

The summary line says how many were sent, how many of those did not answer
2xx, and how many were not sent at all, and the problems are printed again
under it, because a replay of a long capture scrolls and the last line is the
one that is read:

```
zoo replay: <n> sent, <n> that did not answer 2xx, <n> not sent
```

**Sent means answered**: a body is counted as sent when a receiver answered it
with a status. A head that could not be read, a body file that is missing, a
connection refused and an answer that never came are each *not sent* — before
A3g they were counted as sent and as not answering 2xx, so a replay into a
port with nothing on it said every body had been sent (run-2b review, N-10).

### 6.5 What the replayer is not

It does not verify the capture it sends: `zoo verify` re-hashes bytes (§5.6)
and `make verify` runs it on every gate, and a second re-hash here would be a
second place for the rule to live. The one check it shares with `verify` is
*where* the manifest's entries point (§5.4, §6.1), and it shares it by calling
the same function, not by restating it: a replayer that followed a path out of
the run would be sending bytes the capture does not hold. It does not parse, decode or validate a
body, does not look at a response beyond its status, does not retry, and does
not record anything: a replay produces no capture, and a receiver that wants
one points a `zoo capture` at itself.

It also adds nothing to the request. No header of its own, no `Accept-Encoding`
the exporter did not send, no re-framing, no re-ordering, no re-spacing, no
re-terminating, no protocol version of its own. The **one** difference between
the head the exporter sent and the head the replayer sends is the `Host` line,
which names the new destination (§6.2). Where the head carried hop-by-hop
headers, they go out too: the connection they described no longer exists, but
the replay sends the head that was sent, and a receiver that reads them is
reading what the exporter said.

## 7. The audit — A5

```bash
zoo audit captures/z4/2026-10-12-real                 # writes audit/z4-2026-10-12-real.md
zoo audit captures/z4/2026-10-12-recorded --out audit
```

Every capture through `spanweave-live serve` and `spanweave.build`, and
`agentgolden`'s signature over what came out, with every divergence written up
as a **reproduction** naming the repository that owns it (§1.2). The audit
runs the three libraries; it repairs nothing, retries nothing and works around
nothing, and a finding is the product rather than a failure (`CLAUDE.md` §0.6
rule 7).

### 7.1 Where it lives, and what it may import

`spanweave_zoo/audit.py`, and the gate's exemption is that **path** and
nothing else (`tests/gates.py`, `CLAUDE.md` §0.6 rule 6). A gate that matched
the file *name* would hand the exemption to any `audit.py` anywhere under the
package — a module moved one directory down would keep an exemption nobody
granted it, and the rule could be switched off by a `mkdir`. There is one audit
module, it is at that path, and every other file under `spanweave_zoo/`
imports none of the three libraries the gate names: `spanweave`,
`spanweave_live` and `agentgolden` (decided 2026-10-12; `OPEN_QUESTIONS.md`
§5).

The three are the `audit` extra's, pinned by git sha in `pyproject.toml`, and
nothing else in the package needs them. `cli.py` imports the audit module only
when `zoo audit` runs, so the bare wheel's `zoo --version`, `sink`, `capture`,
`replay` and `verify` work with the extra uninstalled (`make install-check`
installs no extra and proves it). `zoo audit` without the extra is a refusal,
exit **2**, naming the command that installs it.

### 7.2 What it refuses, and the pins it records

`zoo audit <run>` refuses — one line naming the cause, exit **2**, no report
written — when it could check nothing honestly:

- `<run>` is not one run directory holding a readable `MANIFEST.json`;
- the run does not verify (§5.6) — an audit of bytes that are not the bytes
  recorded would be a reproduction of nothing. A `file` entry outside the run
  directory (§5.4) is such a run: the refusal line carries `verify`'s first
  problem — for a run whose one fault is such an entry, the entry itself —
  and nothing is read (B4a; an incomplete report for it was declined,
  `OPEN_QUESTIONS.md` §7);
- the `audit` extra is not installed;
- for any of the three libraries, the commit that is installed is not the
  commit `pyproject.toml` pins, or cannot be read. The pinned sha is read from
  the zoo's own installed metadata (the `audit` extra's `Requires-Dist`), the
  installed one from the library's PEP 610 `direct_url.json`. A finding cites
  a sha, and a sha the run did not use would make it irreproducible.

The report's header records, for each of the three, its version, the pinned
sha and the installed sha — so every finding, step 5's included, carries the
commit of the library it is about.

### 7.3 The five steps

The capture's bodies are the manifest's, in receipt order (§6.1). Each step's
command is printed in the report as an operator would type it, with the port
written `<port>` because the audit lets the kernel choose one.

1. **The exporter's bytes into `serve`.** `spanweave-live serve --port 0 --out
   graphs --requests N`, where *N* is the number of `raw/` bodies, started as a
   child process of the same interpreter (`python -m spanweave_live.cli`), and
   `zoo replay <run> --raw` into it (§6, in-process, through the same `send`).
   Recorded: every answer's status and every event line `serve` wrote to
   stderr, verbatim, and its exit status. A `415` on protobuf is a finding,
   not an error.
2. **The Collector's JSON into `serve`, three times** (B6a). The same, with
   `--json` and *N* the number of `json/` bodies, under three completions, in
   this order:
   - **End of input.** `serve --port 0 --out graphs --requests N`, replayed
     back to back as step 1 is. **Completion** is `serve --requests N`: after
     the *N*th request the input has ended, and the end of input runs
     spanweave-live's `Run.finish()`, which replaces the completion with
     `Cap(0)` and ticks once, so every trace still held completes and is
     written as `graphs/<trace_id>.json` (its `SPEC.md` §8.5 at the pinned
     sha). That is the `Cap(0)`-at-end the plan names, chosen by the
     receiver's own CLI and not by the audit; the report says so once, in its
     method section. Recorded: the statuses, every event, the exit status and
     every graph file's bytes. Step 2's findings are this run's, and it is
     the run step 3 compares and checks against.
   - **`--quiet 0`.** `serve --port 0 --out graphs --quiet 0 --requests N`,
     and `zoo replay <run> --json` into it, back to back as step 1 is.
   - **`--root-grace 0`.** The same, with `--root-grace 0`.

   **Zero is the audit's value, not the receiver's.** The pinned
   spanweave-live documents no default for either flag — absent is "no such
   policy", and its README ("The CLI") calls every bound the caller's number
   (`OPEN_QUESTIONS.md` §8) — so the audit chooses the smallest legal value,
   at which each policy fires at the first tick its condition holds (its §5.3:
   both boundaries inclusive, "`Quiet(0)` ... is legal"). `--requests N` is
   still passed, so a trace a policy has not completed by the *N*th request
   is completed at end of input by `Cap(0)`, and the `completed` event's reason
   says which of the two it was: what each policy did with a root that arrived
   last, or with a trace that has no root, is observed rather than to be
   established. The receiver ticks once per request (its §8.5), so at `0`
   the sequence of events is the capture's whether or not the replay sleeps
   the captured gaps, and **no replay is `--timing`** (B6b; B6a's timed
   replays rested on a premise that turned out weaker than written).
   `--cap` and non-zero policy values are not run: a non-zero value fires or
   not by wall clock, and the audit asserts nothing a clock decides. The
   report's method states that the values are the audit's.

   Recorded for each of the two: every answer's status, the replayer's own
   lines, the exit status, every event verbatim, and one table of every `completed`,
   `late_arrival`, `written` and `released` event in the order `serve` wrote
   them — code, trace id, `index`, generation and reason — with the
   `finished` event beneath it. The **reason** of a `completed` is the clause
   of its `detail` before the first colon ("the quiet policy fired on
   Quiet(seconds=0.0)"): at the pinned sha the event carries its policy in no
   field of its own, and the clock readings follow the colon. A `written` or
   `released` event's reason is its `detail`; a `late_arrival`'s is none, its
   `detail` being clock readings. The **generation** is the receiver's (its
   §5.5), counted from its events, which carry none: a trace's *n*th
   `completed` completes generation *n*, a `late_arrival` opens the next one,
   a `written` or `released` belongs to the generation just completed, and a
   `forgotten` for the trace starts the count again (its `--max-completed`:
   the next record opens generation 1). The two policy runs yield **no
   finding**: they are an observation, and step 2's findings are the
   end-of-input run's. One that could not be completed (§7.5) is an
   incomplete step and exit 1, and stops nothing after it.
3. **Live against batch.** For each trace, the records the receiver fed, in
   order, through `spanweave.build` — the live graph must equal the batch graph
   byte for byte (spanweave's `SPEC.md` §10.1, prefix consistency, on a
   stranger's trace). The records are re-read in-process by the pinned
   receiver's own code — each `json/` body handed, in receipt order, to
   `spanweave_live.Endpoint.handle` as the request `serve` received (its
   method, path, `Content-Type`, `Content-Encoding` and `Transfer-Encoding`
   taken from `json/NNNN.headers.json`, §2.3), and each record partitioned by
   `spanweave_live.routing.trace_id_of`. Three graphs per partition, each
   serialized with `spanweave.dumps`:
   - **live**: the file `serve` wrote in step 2;
   - **batch**: `spanweave.build` of the partition's records as JSON lines,
     with `meta.source_digest` removed — the one field a builder fed records
     cannot carry (spanweave's `SPEC.md` §10.4);
   - **incremental**: a `spanweave.Builder` fed the same records in order.

   The reconstruction is checked before it is believed: the in-process status
   of each body must be the status `serve` answered, and the number of records
   must be the `routed` count in `serve`'s `finished` event. If either differs,
   step 3 is **incomplete** rather than a finding about anyone: a
   reconstruction that is not what `serve` read vouches for nothing built from
   it, so no partition is compared, steps 4 and 5 are not run, and none of the
   three yields a finding. The report renders each of steps 3, 4 and 5 as
   *not run*, step 3 naming the difference (the statuses against `serve`'s,
   the records against `routed`), and the audit exits **1** (§7.5). Steps 1
   and 2's findings stand: they are what `serve` answered and wrote, observed
   directly.
4. **`spanweave inspect` on each graph.** `spanweave inspect graphs/<trace_id>.json`
   on each live file (run as `python -m spanweave.cli`), its output recorded
   verbatim; and from the graph itself, through the public API: every
   diagnostic code with its count, the keys of the `unmapped_attributes`
   diagnostics by size (the number of diagnostics naming each key, largest
   first, and the bytes those diagnostics take in the graph document as
   compact sorted JSON), and every node of kind `unknown` by name. Then **one
   row per node** (B6a, B6b), in the graph's order: its id; its **span
   name** (`Node.name`); its kind; its status; its `model` (the key of that
   name in `Node.attributes`, spanweave's normalized subset), or *absent*;
   whether its parent is present — *yes* where a `parent` edge points at it,
   *absent from graph* where an `orphan_parent` diagnostic names it (its
   record states a parent this graph does not hold), *no* where its record
   states none; its **parent id** — the id of each node whose `parent` edge
   points at it, or `—` where none does (an absent parent's stated id is
   not a node of this graph, and the `orphan_parent` diagnostic is where it
   is read); the codes of the diagnostics naming it (`Diagnostic.node_id`),
   each once with its count where more than one; the **unmapped attribute
   keys** on it — the keys the `unmapped_attributes` diagnostics naming it
   list, each once, sorted, by **name only**, never a value — or *none*; its
   **payload state**, inputs and outputs each, as `Payload.state` says it
   (`present`, `absent`, and spanweave's `empty`, `redacted` and `truncated`,
   never collapsed into one another); and its **span events as the record
   carries them**:
   the value under the `events` key of `Node.raw.source` — OTLP's span field,
   kept verbatim on the record spanweave's reader flattened — written beneath
   the table as compact sorted JSON, one block per node, and the row saying
   how many; *absent* where the record has no such key. Nothing in a row is
   read from a payload: every value is the pinned library's, through its
   public API.
5. **`agentgolden`'s signature on each graph.** `agentgolden.signature.signature(graph)`,
   as a smoke, no rules evaluated. Recorded: the number of steps and their
   tokens, or the exception it raised.

Steps 4 and 5 read the graph a `Builder` produced from the partition's records
(step 3's *incremental*): spanweave has no public reader from a graph document
back to a `Graph`, and step 3 has just compared that graph's bytes with the
live file's. Where the two differ, the report says which one steps 4 and 5
read.

The audit parses no payload of its own (§1.1): bodies are read only by the
pinned receiver and the pinned library, and the graphs only through their
public API. The `listening` event's port and the clock readings a `completed`
or `late_arrival` event carries (`seconds`, and the two readings in its
`detail`) are the receiver's and differ from run to run; nothing else in a
report does.

### 7.4 Findings, and who owns them

A finding is a reproduction: the capture path, the commands, the observed
result and the expected one, and the repository that owns it. The audit's rules
for naming the owner are these, and nothing is fixed here:

| Observed | Owner |
|---|---|
| a body answered other than 2xx by `serve` (steps 1, 2) | spanweave-live |
| `serve` exited other than 0, or wrote a stderr line that is not one JSON object | spanweave-live |
| records `serve` routed that reached no graph it wrote (its no-trace builder is never completed or written, its `SPEC.md` §5.4, §8.5) | spanweave-live |
| a record `spanweave.adapters.classify` claimed for no adapter | spanweave |
| a trace whose live file is missing, or a live file no partition explains | spanweave-live |
| live ≠ batch, where incremental = batch | spanweave-live |
| live ≠ batch, where incremental ≠ batch, or either raised | spanweave (its §10.1) |
| `spanweave inspect` exited other than 0 | spanweave |
| `signature(graph)` raised, on a graph `spanweave.validate` finds well-formed | agentgolden |
| `signature(graph)` raised, on a graph `spanweave.validate` finds malformed | spanweave |

Diagnostics, unmapped attributes and `unknown` nodes are recorded in step 4's
tables and are not findings: they are spanweave saying what it did not
understand, which is its job (`A6` turns the tables into probes).

### 7.5 The report

`<out>/<project>-<run-id>.md` (`--out` defaults to `audit/`), where
`<project>` and `<run-id>` are the run directory's parent's name and its own.
In order: the header (the capture, its `kind` and seal, the zoo's version, the
three libraries' versions and shas), the method, the findings with a count per
owner, then one section per step with its command, a table and every event.
Step 2's section holds its three runs, the end-of-input run first, each
policy run under a heading naming its flag; step 4's holds, per graph, the
inspect output, the diagnostic tables and the node table (§7.3), whose
columns are, in order: Node, Span name, Kind, Status, Model, Parent, Parent
id, Diagnostics, Unmapped keys, Inputs, Outputs, Span events (B6b). Reports
written by an earlier audit keep the layout they were written with: a report
records its audit at one sha, and is replaced only by being audited again.
Written whole at the end; a second audit of the same capture overwrites it.

| Exit | When |
|---|---|
| **0** | every step ran; the report is written (findings or not) |
| **1** | the report is written and a step could not be completed: `serve` did not start, did not finish within its bound (in step 1, or in any of step 2's three runs), the capture has no `json/` body, or step 3's reconstruction did not match what `serve` reported |

`serve` did not start covers both a child that exits before its `listening`
event and a command that cannot be executed at all — `Popen` raising
`OSError` (a missing or non-executable program): that step's problem is
`serve did not start: <the error>`, nothing is replayed, and the audit goes on
to write the report. A step that could not be completed, and every later step
that reads what it would have produced, is rendered in the report as *not
run* with its reason; none of them yields a finding.
| **2** | refused (§7.2): nothing was audited and no report was written |

### 7.6 The audit's seams

The audit reads no clock, sleeps on no clock of its own, draws no random
number and binds no socket (`CLAUDE.md`, "Architecture invariants"). Where it
touches the world — the children it starts, the one socket it connects, the
installed metadata it reads — the touch is a parameter of `audit.audit()` or a
seam of §6's, named here:

| Seam | What it is | Why |
|---|---|---|
| `serve_command` | the argv prefix that runs `spanweave-live`; the audit appends `serve --port 0 --out graphs --requests N`, or for step 2's policy runs `serve --port 0 --out graphs --quiet 0 --requests N` and `... --root-grace 0 --requests N` (§7.3). Default `SERVE_COMMAND`, `python -m spanweave_live.cli` on this interpreter | starting a process is touching the world. A test passes a command that never starts or cannot be executed, or one that wraps the real `serve` and changes what it writes — which is how a live ≠ batch divergence is driven to the report |
| `reread` | called with the run and its `json/` files; returns the in-process reconstruction step 3 checks against `serve` (the statuses, and the records by partition). Default `reread`, the pinned `Endpoint` and `trace_id_of` as above | a test passes one that returns statuses or records other than `serve`'s, so step 3's mismatch (§7.3) is driven without a defect in spanweave-live |
| `inspect_command` | the argv prefix that runs `spanweave`; the audit appends `inspect graphs/<trace_id>.json`. Default `INSPECT_COMMAND`, `python -m spanweave.cli` | the same, for step 4 |
| `signature` | called with each step-3 graph; returns agentgolden's `Signature` or raises. Default `agentgolden.signature.signature` | a test passes one that raises, so a step-5 finding and its owner (§7.4) are driven without a defect in agentgolden |
| `installed` | called with a distribution name; returns the commit installed (its PEP 610 `direct_url.json`) or `None`. Default `installed_sha` | a test passes one that reports a sha other than the pin, so §7.2's refusal is driven without reinstalling anything |
| `send` (§6.2) | the capture reaches `serve` through `zoo replay`'s own `send`, in-process: `replay.sender("127.0.0.1", port, timeout=SEND_TIMEOUT)` | the one outbound socket the audit uses is §6.2's, the package's second outbound socket with §4.8's `forward`; the audit opens none of its own |
| `--port 0` | `serve` is told to bind port `0`; the kernel chooses the port, and the audit reads it from `serve`'s `listening` event on stderr | the audit binds nothing, never collides with a port in use and never races a fixed one |

**Bounded waits are not clock reads.** The audit waits on its children with
the stdlib's own timeouts, and each is a named constant in `audit.py`, in
seconds. A bounded wait reads no time into anything the audit records — the
report carries no clock reading of the audit's — so it is not the clock the
invariant forbids; the rule is about reading time, not about waiting a bounded
time (the close review's R-7, ruled 2026-10-12; `TASKS.md`). A bound passed is an incomplete step (exit **1**,
§7.5), never a finding, except where the table says otherwise:

| Constant | Value | What it bounds | When it passes |
|---|---|---|---|
| `START_WAIT` | `30.0` | each `queue.get(timeout=)` on `serve`'s stderr lines until its `listening` event: the wait for the **next** line, not for the event in total | the step is incomplete ("serve wrote no `listening` event in 30s"), nothing is replayed, and `serve` gets `FINISH_WAIT` to exit |
| `SEND_TIMEOUT` | `10.0` | the socket timeout of each replayed request (`socket.create_connection(timeout=)`): the connect, and each send and receive on it | that body's send raises, so it is not sent (§6.4); `serve` is killed, since it waits for *N* requests, and the step is incomplete |
| `FINISH_WAIT` | `60.0` | `process.wait(timeout=)` for `serve` to exit after the replay; again after a kill | the first: `serve` is killed and the step is incomplete ("serve did not finish within 60s"). The second is not caught: the audit stops with `subprocess.TimeoutExpired` and writes no report |
| `FINISH_WAIT` | `60.0` | `thread.join(timeout=)` on the thread draining `serve`'s stderr, once `serve` has exited | the join returns and the report carries the lines read so far |
| `FINISH_WAIT` | `60.0` | `subprocess.run(timeout=)` of each step-4 `inspect` | not caught: the stdlib kills the child and raises `subprocess.TimeoutExpired`, and the audit stops with it and writes no report |

The two uncaught cases are stated as the code behaves at this commit, not as a
decision: a bound passed there is neither a finding nor an incomplete step,
and nothing in a report says so.
