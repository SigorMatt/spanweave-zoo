"""`MANIFEST.json`: what a capture is, and what is in it (`SPEC.md` §5).

`CLAUDE.md` §0.6 rule 2 says a capture is immutable -- "bytes as received, with
the request headers beside them and **a sha256 of each body in the manifest**"
-- and `zoo verify` re-hashes every capture on every `make check`. That makes
the digest the one part of `MANIFEST.json` the sink cannot defer: without it
there is nothing to re-hash against, and "immutable" is a claim nobody checks.

That is why the digest came first (A1) and the rest of the document followed
(A3): the `bodies` entries own the sha256 *alone*, so it is not also copied
into `NNNN.headers.json`, and there is exactly one home for a digest.

A2 added the two fields its own behaviour needs and no others (`SPEC.md` §4.5):
`collector_version`, the pin that re-encoded the capture, and `forwards`, one
entry per attempted forward to the Collector -- a record of *delivery* beside
the record of bytes. A2 also brought a second recorder into the same run
directory, which is why writing this file now goes through one lock per run.

A3 completed it (`SPEC.md` §5): `kind` -- `recorded` or `real`, required,
never inferred -- the pet project's own `MANIFEST.json` copied verbatim,
`sink_version`, `started_at` / `ended_at` from the injected clock, and each
body entry's `content_type` / `content_encoding`. Those last two are
**carried across** from the body's own `NNNN.headers.json`, where the request
already put them: the sink still only echoes a content type (`SPEC.md` §1.1,
§3.3), and copying two values out of the record at the end of a run is not the
sink looking at a payload. A3 extended these same entries rather than
replacing them, so `zoo verify`'s re-hash still reads only `file`, `sha256`
and `bytes`.

A3b changed *when* it is written and *how much* it covers (`SPEC.md` §3.5,
§5.5, §5.6). Each recorded body is journalled to `bodies.jsonl` as one flushed
line and each attempted forward to `forwards.jsonl`, and the manifest is
assembled **once**, at the end of the run, from those journals plus a walk of
the run directory that hashes **every** file in it except `MANIFEST.json`.
Two things follow. The capture is covered: a headers file, a journal and a
re-encoding are all re-hashed by `zoo verify`, not only the bodies. And the
cost of recording a body stopped depending on how many bodies came before it:
appending a line is constant work, where rewriting a manifest that grows by an
entry per POST is not.

Nothing here parses a body. It hashes bytes and counts them. The one document
it does parse is the project's own manifest, which is not a payload: the zoo
copies that document whole and reads exactly one field of it -- `started_at`,
and only to say whether the document can be the one the recorded run wrote
(`SPEC.md` §5.3) -- checks nothing in it against anything else, and refuses
loudly if the path it was given is not a readable JSON document at all.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from spanweave_zoo import __version__

MANIFEST_NAME = "MANIFEST.json"

# The journals (`SPEC.md` §3.5): one flushed line per recorded body and one per
# attempted forward, written as the run goes. They are the run's own notes, and
# the manifest is assembled from them when it ends -- so a body costs the same
# to record whether it is the first or the sixteen-hundredth. They stay in the
# capture afterwards and are hashed like every other file in it.
JOURNAL_NAME = "bodies.jsonl"
FORWARD_JOURNAL_NAME = "forwards.jsonl"

# The suffix of the file that holds one request verbatim beside its body
# (`SPEC.md` §2.3). It lives here rather than in `sink.py` because both the
# writer and the manifest's completion step (`finish`) name it, and `sink.py`
# imports this module rather than the other way round.
HEADERS_SUFFIX = ".headers.json"

# And the octets that parse was made from (`SPEC.md` §2.3). It is here beside
# the parse's name because both are read from here now: `finish` reads the
# parse to carry each body's content headers across (§5.4), and the replayer
# reads the octets, because the octets are the record of the request and the
# parse is not (`SPEC.md` §6.2). `sink.py`, which writes both files, names
# these two constants rather than the two strings.
HEADERS_RAW_SUFFIX = ".headers.raw"

# The key under which the per-body entries live. A3's fields sit beside it.
BODIES = "bodies"

# Every *other* file in the run directory, one entry each, with the same three
# keys a body entry carries (`SPEC.md` §5.6): the headers files, the journals,
# and anything else a capture turns out to hold. Together with `bodies` it
# accounts for every file except `MANIFEST.json`, each exactly once -- so there
# is still exactly one home for a digest, and `zoo verify` re-hashes the whole
# capture rather than the part of it that happens to be bodies.
FILES = "files"

# A2's two keys (`SPEC.md` §4.5). `forwards` is one entry per attempted forward
# and is about *delivery*, not about bytes -- which is why it is a list of its
# own rather than a field on a `bodies` entry: A1 pinned those to `file`,
# `sha256` and `bytes`, and `zoo verify`'s re-hash reads only those.
FORWARDS = "forwards"
COLLECTOR_VERSION = "collector_version"

# A3's keys (`SPEC.md` §5). `kind` is the one declaration a capture cannot be
# written without: a `recorded` capture and a `real` capture differ only by it,
# and the audit keys off it, so a default here would be a lie there.
KIND = "kind"
KINDS = ("real", "recorded")
PROJECT_MANIFEST = "project_manifest"
SINK_VERSION = "sink_version"
STARTED_AT = "started_at"
ENDED_AT = "ended_at"

# What went wrong during a run that the capture cannot fix: today, a Collector
# child that exited (`SPEC.md` §4.6). The key is **absent** from a capture that
# had none, rather than an empty list, because a reader asking "did anything go
# wrong here" should not have to tell `[]` from a field nobody wrote.
PROBLEMS = "problems"

# The two values a body entry carries across from its own headers file. The
# header names are matched case-insensitively -- HTTP says they are -- and the
# *values* are copied exactly as the request sent them.
CONTENT_TYPE = "content_type"
CONTENT_ENCODING = "content_encoding"
_CONTENT_HEADERS = {CONTENT_TYPE: "content-type", CONTENT_ENCODING: "content-encoding"}


class ProjectManifestUnreadable(Exception):
    """The path given for the project's own `MANIFEST.json` is not usable.

    Raised before a capture starts, never after (`SPEC.md` §5): a capture
    missing the one document that says what made it is a capture that cannot
    be completed without editing it, and a capture is never edited
    (`CLAUDE.md`, "Halt points").
    """


@dataclass(frozen=True, slots=True)
class BodyEntry:
    """One recorded body, as the manifest carries it (`SPEC.md` §3.5)."""

    file: str
    """The body's path relative to the run directory: `raw/0001.body`."""

    sha256: str
    bytes: int

    def as_document(self) -> dict[str, Any]:
        return {"bytes": self.bytes, "file": self.file, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class ForwardEntry:
    """One attempted forward to the Collector (`SPEC.md` §4.4, §4.5).

    Either the Collector's HTTP `status` or the `error` that stopped the
    forward, never both and never neither. A failed forward loses nothing --
    the body, its headers and its digest are already recorded -- and is never
    silent, and this is where it stops being silent.
    """

    file: str
    """The forwarded body's path relative to the run directory."""

    status: int | None = None
    error: str | None = None

    def as_document(self) -> dict[str, Any]:
        if self.error is not None:
            return {"error": self.error, "file": self.file}
        return {"file": self.file, "status": self.status}

    @property
    def failed(self) -> bool:
        return self.error is not None or self.status is None or self.status >= 400


# One lock per run directory, shared by every recorder writing into it.
#
# `zoo capture` runs TWO recorders on one run directory (`SPEC.md` §4.5) -- the
# raw sink and the json sink -- and they write ONE manifest. A recorder
# serializes its own writes, but the manifest is shared, so the
# read-modify-write that appends an entry is serialized here, per run
# directory, across recorders. The recorder's own lock is always taken first
# and this one last, so the two can never deadlock.
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _lock_for(run: Path) -> threading.Lock:
    key = str(run.resolve())
    with _LOCKS_LOCK:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def digest(data: bytes) -> str:
    """The sha256 of some bytes, hex. The only hash this repository uses."""
    return hashlib.sha256(data).hexdigest()


def dumps(document: object) -> str:
    """The one JSON spelling: two-space indent, `sort_keys=True`, newline."""
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, document: object) -> None:
    """Write JSON atomically, so a reader never sees half a document.

    The sink rewrites `MANIFEST.json` after every POST while an exporter is
    still sending, and `zoo verify` may be reading it. A rename within one
    directory is atomic, so the file on disk is always one whole manifest.
    """
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(dumps(document), encoding="utf-8")
    temporary.replace(path)


def read(run: Path) -> dict[str, Any]:
    """The run's manifest as a document. Raises if there isn't a readable one.

    `OSError` if it is absent or unreadable, `ValueError` if it is not JSON or
    not a document with a `bodies` list. A manifest that cannot be read is a
    refusal (`SPEC.md` §3.5), never a pass, so this does not return a default.
    """
    path = run / MANIFEST_NAME
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{MANIFEST_NAME} is not a JSON object")
    bodies = document.get(BODIES)
    if not isinstance(bodies, list):
        raise ValueError(f"{MANIFEST_NAME} has no {BODIES!r} list")
    return document


def update(run: Path, change: Callable[[dict[str, Any]], None]) -> None:
    """Read, change and rewrite the run's manifest under the run's lock.

    The one way anything here writes `MANIFEST.json`, so that two recorders on
    one run directory (`SPEC.md` §4.5) cannot interleave a read-modify-write
    and lose an entry. `change` mutates the document in place and returns
    nothing; it must not do anything slow, because it runs holding the lock.
    """
    path = run / MANIFEST_NAME
    with _lock_for(run):
        document: dict[str, Any] = {BODIES: []}
        if path.exists():
            document = read(run)
        change(document)
        write_json(path, document)


def _append(document: dict[str, Any], key: str, entry: object) -> None:
    """Append to one of the manifest's lists, creating it if it is not there.

    `entry` is whatever that list holds: a `bodies` or `forwards` document, or
    a `problems` line (`SPEC.md` §4.6).
    """
    listed: list[Any] = list(document.get(key) or [])
    listed.append(entry)
    document[key] = listed


def _journal(run: Path, name: str, document: object) -> None:
    """Append one line to one of the run's journals, and flush it.

    Append, flush, close -- per line, under the run's lock, so two recorders
    writing into one run directory (`SPEC.md` §4.5) cannot interleave halves of
    a line and the order on disk is the order things happened. The work is the
    same for the first line and the ten-thousandth, which is the whole reason
    the journal exists: rewriting a document that grows by an entry per POST
    makes recording the last body of a long run cost more than recording the
    first (`SPEC.md` §3.5).
    """
    line = json.dumps(document, sort_keys=True) + "\n"
    with _lock_for(run):
        run.mkdir(parents=True, exist_ok=True)
        with (run / name).open("a", encoding="utf-8") as journal:
            journal.write(line)
            journal.flush()


def journal_body(run: Path, entry: BodyEntry) -> None:
    """Write one recorded body down, now (`SPEC.md` §3.5).

    One line, flushed, in the order the bodies were recorded -- which is
    receipt order, the only ordering a capture carries (`SPEC.md` §2.2).
    `finish` turns the journal into the manifest's `bodies` list at the end of
    the run; until then the journal is where the digests are, which is why it
    is flushed rather than buffered.
    """
    _journal(run, JOURNAL_NAME, entry.as_document())


def journal_forward(run: Path, entry: ForwardEntry) -> None:
    """Write one attempted forward down, now (`SPEC.md` §4.5).

    In the order the forwards *completed*, which is receipt order unless two
    exports were in flight at once.
    """
    _journal(run, FORWARD_JOURNAL_NAME, entry.as_document())


def _journalled(run: Path, name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """What one journal recorded, and what it did not record readably.

    A line that is not a JSON object is **not** dropped quietly: it becomes a
    problem, so the thing it was the record of is missing from the manifest
    loudly rather than silently. A half-written last line is what a run killed
    mid-write leaves, and "we could not read our own note" is a reportable
    outcome (`CLAUDE.md`, "Honest refusal beats a reassuring pass").
    """
    try:
        text = (run / name).read_text(encoding="utf-8")
    except OSError:
        return [], []
    entries: list[dict[str, Any]] = []
    found: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except ValueError:
            document = None
        if not isinstance(document, dict):
            found.append(
                f"{name} line {number} is not a JSON object, so what it "
                f"recorded is not listed in {MANIFEST_NAME}"
            )
            continue
        entries.append(document)
    return entries, found


def append_problem(run: Path, problem: str) -> None:
    """Record one thing that went wrong during the run (`SPEC.md` §4.6).

    Written when it is noticed rather than at the end, so a capture whose
    Collector died says so even if the run is then stopped the hard way. One
    line per distinct problem: the caller records a problem once, not once per
    look at it.
    """
    update(run, lambda document: _append(document, PROBLEMS, problem))


def read_project_manifest(path: Path) -> object:
    """The pet project's own `MANIFEST.json`, as a document, verbatim.

    `EXPORT-CONTRACT.md` §1 is what the implementer was told to write there;
    this reads it and returns it, and that is all. No field is looked at, no
    key is required, nothing is reconciled against the capture's own `kind`
    (`SPEC.md` §1.3): the zoo copies and does not improve. The only thing
    checked is that the bytes are a JSON document, because a document is what
    the manifest carries -- and a path that is not one is a refusal at the
    start of a capture rather than a surprise at the end of it.

    The return type is `object` and not a shape: there is nothing here that
    may be indexed, counted or asked for a key, and the type is where that is
    said once rather than remembered.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as unreadable:
        raise ProjectManifestUnreadable(
            f"cannot read the project's own {MANIFEST_NAME} at {path}: "
            f"{unreadable}. It is the document EXPORT-CONTRACT.md section 1 "
            f"tells a pet project to write, and `make run` writes it; the "
            f"capture carries it verbatim and cannot be completed without it."
        ) from unreadable
    try:
        return json.loads(text)
    except ValueError as malformed:
        raise ProjectManifestUnreadable(
            f"the project's own {MANIFEST_NAME} at {path} is not a JSON "
            f"document: {malformed}. The zoo copies it verbatim and parses no "
            f"field of it, but it cannot copy what it cannot read."
        ) from malformed


def label(
    run: Path,
    *,
    kind: str,
    collector_version: str,
    started_at: str,
) -> None:
    """Say what this capture is, before a body can arrive (`SPEC.md` §5).

    Everything a capture knows about itself at the start: the declaration
    (`kind`), the two versions, and `started_at` from the injected clock.
    Written first rather than last, so a run stopped the hard way still says
    what it was; `finish` writes everything that is only knowable at the end --
    the bodies, every other file's digest, the project's own manifest and
    `ended_at` (`SPEC.md` §5.5).

    `kind` is required and is one of `KINDS`. There is no default and nothing
    is inferred -- not from the project's manifest, not from the endpoint, not
    from whether a model was reachable -- because `recorded` and `real` differ
    by this declaration alone and the audit reads it as the truth.
    """
    if kind not in KINDS:
        raise ValueError(
            f"a capture must declare its kind as one of {' or '.join(KINDS)} "
            f"(SPEC.md section 5): {kind!r} is neither. There is no default: "
            f"a recorded capture and a real one differ only by this."
        )

    def change(document: dict[str, Any]) -> None:
        document[KIND] = kind
        document[COLLECTOR_VERSION] = collector_version
        document[SINK_VERSION] = __version__
        document[STARTED_AT] = started_at

    update(run, change)


def finish(
    run: Path,
    *,
    ended_at: str,
    project_manifest: Path | None = None,
    started_at: str | None = None,
) -> list[str]:
    """Assemble the manifest, once, at the end of the run (`SPEC.md` §5.5).

    Everything that is only true at the end is written here, in one atomic
    write, and `ended_at` is in it -- nothing is written to the manifest after
    `ended_at`, which is what lets `zoo verify` read its absence as a capture
    that was never completed (`SPEC.md` §5.6):

    - `bodies`, from `bodies.jsonl`, in the order the bodies were recorded,
      each entry's content headers carried across from its own
      `NNNN.headers.json` where the request already put them verbatim -- so
      the sink inspects nothing to produce them (`SPEC.md` §5.4). A body whose
      headers file declared neither gets `null` for both: the zoo has no
      content type of its own to invent (`SPEC.md` §3.3);
    - `forwards`, from `forwards.jsonl`, absent when nothing was forwarded;
    - `files`: a sha256 and a length for **every other file** in the run
      directory, `MANIFEST.json` excepted, so the capture is covered rather
      than sampled;
    - `project_manifest`: the pet project's own document, copied now rather
      than at the start, so the copy is the one the recorded run left behind
      (`SPEC.md` §5.3).

    Returns the problems it found -- a journal line it could not read, a
    project manifest it could not use -- which it has also written into the
    manifest's `problems`. The caller reports them and exits non-zero: a
    capture is never silently fine.
    """
    bodies, found = _journalled(run, JOURNAL_NAME)
    forwards, forward_problems = _journalled(run, FORWARD_JOURNAL_NAME)
    found += forward_problems
    for listed in bodies:
        name = listed.get("file")
        if isinstance(name, str):
            listed.update(_declared_content(run, name))

    copied: object = None
    if project_manifest is not None:
        copied, copy_problems = _project_copy(project_manifest, started_at)
        found += copy_problems

    recorded = {
        listed["file"] for listed in bodies if isinstance(listed.get("file"), str)
    }
    others = _hashed(run, recorded)

    def change(document: dict[str, Any]) -> None:
        document[BODIES] = bodies
        if forwards:
            document[FORWARDS] = forwards
        document[FILES] = others
        if project_manifest is not None:
            document[PROJECT_MANIFEST] = copied
        for problem in found:
            _append(document, PROBLEMS, problem)
        # Last, and after everything above: an `ended_at` means the rest of
        # this document is there (`SPEC.md` §5.5).
        document[ENDED_AT] = ended_at

    update(run, change)
    return found


def _hashed(run: Path, recorded: set[str]) -> list[dict[str, Any]]:
    """Every file in the run directory except the bodies and the manifest.

    The walk is the point. A manifest assembled from what the recorders
    remember can only cover what they wrote; walking the directory covers the
    headers files, the journals and anything else the capture turns out to
    hold, so `zoo verify` re-hashes the capture rather than the part of it that
    happens to be bodies (`SPEC.md` §5.6). Sorted, because a manifest is a
    record and two runs over one capture produce one document.
    """
    entries: list[dict[str, Any]] = []
    for path in sorted(run.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(run).as_posix()
        if name == MANIFEST_NAME or name in recorded:
            continue
        data = path.read_bytes()
        entries.append(
            BodyEntry(file=name, sha256=digest(data), bytes=len(data)).as_document()
        )
    return entries


def _project_copy(path: Path, started_at: str | None) -> tuple[object, list[str]]:
    """The project's own manifest as the capture will carry it, and why not.

    Copied at the end of the run (`SPEC.md` §5.3), which is the only time the
    file the project's own run wrote can be the file that is read. Four
    outcomes, and each is in the record:

    - the document is there and can be the recorded run's: copied verbatim;
    - it is gone, or is no longer a JSON document: `null`, and a problem
      naming the path -- a stale copy would be worse than none, because a
      reader cannot tell a stale one from a true one;
    - it is there and its own `started_at` predates the capture's: `null`, and
      a problem -- that document was written before this capture existed, so
      it is some earlier run's and carrying it would be the capture claiming
      something about the run it recorded that is not true;
    - it is there and carries no `started_at` the zoo can read: copied, and a
      problem all the same. The document is kept because the zoo does not drop
      a record it was handed, and the problem is recorded because a capture
      that cannot date its project manifest is not a capture that is fine.
    """
    try:
        document = read_project_manifest(path)
    except ProjectManifestUnreadable as unreadable:
        return None, [
            f"the project's own {MANIFEST_NAME} could not be copied when the "
            f"capture ended, so this capture does not carry one: {unreadable}"
        ]
    if started_at is None:
        return document, []
    written, capture_started = _moment(document), moment_of(started_at)
    if written is None or capture_started is None:
        return document, [
            f"the project's own {MANIFEST_NAME} at {path} carries no "
            f"{STARTED_AT} this zoo can read, so nothing here says whether it "
            f"is the document the recorded run wrote (EXPORT-CONTRACT.md "
            f"section 1 asks for one, ISO-8601)"
        ]
    if written < capture_started:
        return None, [
            f"the project's own {MANIFEST_NAME} at {path} says it started at "
            f"{document.get(STARTED_AT) if isinstance(document, dict) else '?'}"
            f", before this capture started at {started_at}: it is an earlier "
            f"run's document, not the recorded run's, so this capture carries "
            f"none (SPEC.md section 5.3)"
        ]
    return document, []


def _moment(document: object) -> datetime | None:
    """A document's own `started_at` as a moment, or `None`.

    The one field of the project's manifest the zoo reads, and it reads it for
    one purpose: to say whether the document can be the one the recorded run
    wrote (`SPEC.md` §5.3). Nothing else in it is looked at, nothing is
    reconciled, and the value is not copied anywhere -- the document is carried
    whole or not at all.
    """
    if not isinstance(document, dict):
        return None
    return moment_of(document.get(STARTED_AT))


def moment_of(value: object) -> datetime | None:
    """One ISO-8601 string as a moment, or `None` if it is not one.

    Public because `replay.py` compares two recorded `received_at` values the
    same way and under the same bound (`SPEC.md` §6.3): the rule about what is
    and is not a comparable moment has one home.

    `datetime.fromisoformat` and no clock read: the two timestamps compared
    here are both values that were written down, one by the project and one
    from the zoo's injected `now`. A value that does not parse, or that carries
    no offset, is not compared at all -- guessing a timezone is inventing a
    fact about somebody else's run.
    """
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def _declared_content(run: Path, file: str) -> dict[str, str | None]:
    """What `file`'s own headers file said its content type and encoding were.

    `None` for either the request did not send. A header may legally repeat
    (`SPEC.md` §3.2), and the first value as received is the one carried: the
    headers file stays the record of the repeat, because it is the record of
    the request.
    """
    declared: dict[str, str | None] = {CONTENT_TYPE: None, CONTENT_ENCODING: None}
    document = _parsed_head(run, file)
    if document is None:
        return declared
    received = document.get("headers")
    if not isinstance(received, list):
        return declared
    for pair in received:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        name, value = pair
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        for key, header in _CONTENT_HEADERS.items():
            if name.lower() == header and declared[key] is None:
                declared[key] = value
    return declared


def _parsed_head(run: Path, file: str) -> dict[str, Any] | None:
    """`file`'s own `NNNN.headers.json` as a document, or `None`.

    The parse, which is not the record (`SPEC.md` §2.3): what is read from it
    here is the two content headers the manifest carries across (§5.4) and the
    `received_at` the sink wrote (§6.3), and nothing else ever.
    """
    body = Path(file)
    headers_file = run / body.with_name(body.stem + HEADERS_SUFFIX)
    try:
        document = json.loads(headers_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def received_at(run: Path, file: str) -> str | None:
    """When the sink recorded `file`, as it wrote it down, or `None`.

    The one thing in a headers file the **request** did not say: it is the
    sink's own note, from the injected `now` (`SPEC.md` §3.2, §3.6), which is
    why it is in the parse beside the body and not in the octets of the head.
    `zoo replay --timing` sleeps the gaps between these values (`SPEC.md`
    §6.3), and reading one is not reading a body.
    """
    document = _parsed_head(run, file)
    if document is None:
        return None
    moment = document.get("received_at")
    return moment if isinstance(moment, str) else None


def recorded_bodies(run: Path) -> list[str]:
    """Every body the manifest lists, in the order it lists them.

    Which is the order the journal was written, which is receipt order
    (`SPEC.md` §2.2, §3.5) -- so a caller that must re-send a capture in the
    order it arrived reads that order out of the record rather than deciding it
    again by sorting a directory (`SPEC.md` §6.1). Raises whatever `read` does
    on a manifest that cannot be read: there is no default here either.
    """
    document = read(run)
    return [
        entry["file"]
        for entry in document[BODIES]
        if isinstance(entry, dict) and isinstance(entry.get("file"), str)
    ]


def problems(run: Path) -> list[str]:
    """Re-hash one run against its manifest. Returns one line per problem.

    An empty list means all of this, and it takes both directions to mean it
    (`SPEC.md` §5.6): every file the manifest lists -- bodies, headers files,
    journals, the Collector's re-encodings -- is on disk with the length and
    the sha256 it recorded; every file on disk is one the manifest lists; the
    capture was completed (`ended_at`); it declares a `kind` the spec names, or
    declares none at all; and nothing went wrong during the run that the
    capture could not fix (`problems`).

    The directions matter both ways round. A check that only iterated the
    manifest could never notice a file nobody recorded, and would report a
    capture with something in it from somewhere else as verified; a check that
    only walked the directory could never notice a body that went missing.

    Anything else -- including a manifest that cannot be read -- is a line
    here, and a non-zero exit upstream.
    """
    try:
        document = read(run)
    except OSError:
        return [
            f"{run}: no readable {MANIFEST_NAME} -- nothing records what "
            f"this capture's bodies should hash to"
        ]
    except ValueError as malformed:
        return [f"{run}: {MANIFEST_NAME} cannot be read: {malformed}"]

    found: list[str] = []
    for key in (BODIES, FILES):
        found += _rehashed(run, document, key)
    found += _unlisted(run, document)
    return found + _incomplete(run, document)


def _rehashed(run: Path, document: dict[str, Any], key: str) -> list[str]:
    """Every file one of the manifest's lists claims, re-read and re-hashed.

    `bodies` and `files` carry the same three keys and are checked by the same
    code for the same reason: a digest is a digest, and a capture is covered
    only if the thing that walks it does not care which list a file is in
    (`SPEC.md` §5.6).
    """
    listed_files = document.get(key)
    if listed_files is None:
        return [
            f"{run}: {MANIFEST_NAME} has no {key!r} list, so it does not say "
            f"what this capture holds"
        ]
    if not isinstance(listed_files, list):
        return [f"{run}: {MANIFEST_NAME}'s {key!r} is not a list"]
    found: list[str] = []
    for position, listed in enumerate(listed_files):
        if not isinstance(listed, dict):
            found.append(f"{run}: {key}[{position}] is not an object")
            continue
        name = listed.get("file")
        if not isinstance(name, str):
            found.append(f"{run}: {key}[{position}] has no 'file'")
            continue
        try:
            data = (run / name).read_bytes()
        except OSError:
            found.append(f"{run}: {name} is listed in {MANIFEST_NAME} but missing")
            continue
        actual = digest(data)
        if actual != listed.get("sha256"):
            found.append(
                f"{run}: {name} sha256 is {actual}, "
                f"{MANIFEST_NAME} says {listed.get('sha256')}"
            )
        elif len(data) != listed.get("bytes"):
            found.append(
                f"{run}: {name} is {len(data)} bytes, "
                f"{MANIFEST_NAME} says {listed.get('bytes')}"
            )
    return found


def _listed(document: dict[str, Any]) -> set[str]:
    """Every file the manifest accounts for, from both of its lists."""
    names: set[str] = set()
    for key in (BODIES, FILES):
        for entry in document.get(key) or []:
            if isinstance(entry, dict) and isinstance(entry.get("file"), str):
                names.add(entry["file"])
    return names


def _unlisted(run: Path, document: dict[str, Any]) -> list[str]:
    """Every file in the run directory the manifest does not account for.

    The capture is walked, not the list. Every file has an entry of its own --
    a body in `bodies`, everything else in `files` (`SPEC.md` §5.6) -- and
    `MANIFEST.json` accounts for nothing, including itself. Nothing is
    accounted for by sitting *beside* something that is listed: a headers file
    whose digest nobody wrote down is a file nothing says anything about, which
    is the gap this check closed.
    """
    listed = _listed(document)
    found: list[str] = []
    for path in sorted(run.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(run).as_posix()
        if name == MANIFEST_NAME or name in listed:
            continue
        found.append(
            f"{run}: {name} is on disk but absent from {MANIFEST_NAME} -- "
            f"nothing recorded it, so nothing says what it should hash to"
        )
    return found


def _incomplete(run: Path, document: dict[str, Any]) -> list[str]:
    """What the manifest says about itself that makes the capture not verified.

    Three things, and none of them is about bytes (`SPEC.md` §5.6):

    - **no `ended_at`**: the capture was never completed. The run was killed,
      or died, between its first body and its last line, and nothing says the
      manifest covers what is on disk. The fix is not a repair -- a capture is
      never edited (`CLAUDE.md`, "Halt points") -- so the line says how to get
      rid of it and capture again.
    - **a `kind` the spec does not name**: `recorded` or `real`, or nothing at
      all for a `zoo sink` run that never declared one. Anything else is a
      declaration the audit would read as the truth and could not use.
    - **`problems`**: the run recorded something going wrong that the capture
      cannot fix (a Collector that exited, a project manifest that could not
      be copied). `zoo capture` already exited non-zero saying so; `verify`
      says it again every time, because a capture nobody can trust should not
      pass a check whose whole job is trust.
    """
    found: list[str] = []
    if not isinstance(document.get(ENDED_AT), str):
        found.append(
            f"{run}: no {ENDED_AT} in {MANIFEST_NAME} -- this capture was "
            f"never completed, so nothing says the manifest covers what is on "
            f"disk. A capture is never edited: remove it with "
            f"`rm -rf {run}` and capture again."
        )
    declared = document.get(KIND)
    if declared is not None and declared not in KINDS:
        found.append(
            f"{run}: {KIND} is {declared!r}, which is neither "
            f"{' nor '.join(KINDS)} (SPEC.md section 5.2) -- the audit reads "
            f"this field as the truth about the run"
        )
    for problem in document.get(PROBLEMS) or []:
        found.append(
            f"{run}: {MANIFEST_NAME} records a problem from the run: {problem}"
        )
    return found


def kind_of(run: Path) -> str | None:
    """What the run declared itself to be, or `None` if it did not.

    `zoo verify` prints it, and prints nothing where there is nothing: a
    capture written by `zoo sink` alone has no `kind` to declare, and inventing
    one for the line would be inventing the one thing the audit reads.
    """
    try:
        declared = read(run).get(KIND)
    except (OSError, ValueError):
        return None
    return declared if isinstance(declared, str) else None


def body_count(run: Path) -> int:
    """How many bodies the run's manifest lists. Zero if it has none."""
    try:
        return len(read(run)[BODIES])
    except (OSError, ValueError):
        return 0
