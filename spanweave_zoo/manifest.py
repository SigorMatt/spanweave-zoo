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

Nothing here parses a body. It hashes bytes and counts them. The one document
it does parse is the project's own manifest, which is not a payload: the zoo
copies that document whole, reads no field of it, checks nothing in it against
anything, and refuses loudly if the path it was given is not a readable JSON
document at all (`SPEC.md` §5).
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spanweave_zoo import __version__

MANIFEST_NAME = "MANIFEST.json"

# The suffix of the file that holds one request verbatim beside its body
# (`SPEC.md` §2.3). It lives here rather than in `sink.py` because both the
# writer and the manifest's completion step (`finish`) name it, and `sink.py`
# imports this module rather than the other way round.
HEADERS_SUFFIX = ".headers.json"

# The key under which the per-body entries live. A3's fields sit beside it.
BODIES = "bodies"

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


def _append(document: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
    listed: list[Any] = list(document.get(key) or [])
    listed.append(entry)
    document[key] = listed


def append_body(run: Path, entry: BodyEntry) -> None:
    """Add one body to the run's manifest, creating the file if need be.

    Appends rather than rewrites the list, so entries stay in the order the
    bodies were recorded -- which is receipt order, the only ordering a capture
    carries (`SPEC.md` §2.2).
    """
    update(run, lambda document: _append(document, BODIES, entry.as_document()))


def append_forward(run: Path, entry: ForwardEntry) -> None:
    """Add one attempted forward to the run's manifest (`SPEC.md` §4.5).

    In the order the forwards *completed*, which is receipt order unless two
    exports were in flight at once.
    """
    update(run, lambda document: _append(document, FORWARDS, entry.as_document()))


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
    project_manifest: object,
    started_at: str,
) -> None:
    """Say what this capture is, before a body can arrive (`SPEC.md` §5).

    Everything a capture knows about itself at the start: the declaration
    (`kind`), the project's own manifest copied whole, the two versions, and
    `started_at` from the injected clock. Written first rather than last, so a
    run stopped the hard way still says what it was; `finish` adds `ended_at`.

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
        document[PROJECT_MANIFEST] = project_manifest
        document[SINK_VERSION] = __version__
        document[STARTED_AT] = started_at

    update(run, change)


def finish(run: Path, *, ended_at: str) -> None:
    """Close the manifest: `ended_at`, and each body's content headers.

    The end of `zoo capture` (`SPEC.md` §5). The content headers are copied
    out of each body's own `NNNN.headers.json`, where the request already put
    them verbatim -- so the sink inspects nothing to produce them and there is
    still one record of what the exporter claimed about its own bytes. A body
    whose headers file declared neither gets `null` for both: the zoo has no
    content type of its own to invent (`SPEC.md` §3.3).
    """

    def change(document: dict[str, Any]) -> None:
        document[ENDED_AT] = ended_at
        for listed in document[BODIES]:
            if not isinstance(listed, dict):
                continue
            name = listed.get("file")
            if not isinstance(name, str):
                continue
            listed.update(_declared_content(run, name))

    update(run, change)


def _declared_content(run: Path, file: str) -> dict[str, str | None]:
    """What `file`'s own headers file said its content type and encoding were.

    `None` for either the request did not send. A header may legally repeat
    (`SPEC.md` §3.2), and the first value as received is the one carried: the
    headers file stays the record of the repeat, because it is the record of
    the request.
    """
    body = Path(file)
    headers_file = run / body.with_name(body.stem + HEADERS_SUFFIX)
    declared: dict[str, str | None] = {CONTENT_TYPE: None, CONTENT_ENCODING: None}
    try:
        document = json.loads(headers_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return declared
    if not isinstance(document, dict):
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


def problems(run: Path) -> list[str]:
    """Re-hash one run against its manifest. Returns one line per problem.

    An empty list means two things, and it takes both directions to mean them
    (`SPEC.md` §5): every body the manifest lists is on disk with the length
    and the sha256 it recorded, **and** every file on disk is one the manifest
    lists. The second half is why this walks the directory as well as the
    list: a check that only iterated the manifest could never notice a body
    nobody recorded, and would report a capture with a file in it from
    somewhere else as verified.

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
    for position, listed in enumerate(document[BODIES]):
        if not isinstance(listed, dict):
            found.append(f"{run}: {BODIES}[{position}] is not an object")
            continue
        name = listed.get("file")
        if not isinstance(name, str):
            found.append(f"{run}: {BODIES}[{position}] has no 'file'")
            continue
        body = run / name
        try:
            data = body.read_bytes()
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
    return found + _unlisted(run, document)


def _unlisted(run: Path, document: dict[str, Any]) -> list[str]:
    """Every file in the run directory the manifest does not account for.

    The capture is walked, not the list. A body is accounted for by its own
    `bodies` entry; a `NNNN.headers.json` is accounted for by the entry of the
    body it sits beside (`SPEC.md` §2.3: the headers are part of the capture,
    and a headers file beside no listed body is a body that went missing from
    the manifest). `MANIFEST.json` itself accounts for nothing, including
    itself.
    """
    listed = {
        entry["file"]
        for entry in document[BODIES]
        if isinstance(entry, dict) and isinstance(entry.get("file"), str)
    }
    beside = {Path(name).with_suffix("").as_posix() for name in listed}
    found: list[str] = []
    for path in sorted(run.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(run).as_posix()
        if name == MANIFEST_NAME:
            continue
        if name.endswith(HEADERS_SUFFIX):
            stem = name[: -len(HEADERS_SUFFIX)]
            if stem in beside:
                continue
            found.append(
                f"{run}: {name} is on disk but no body of its own is listed "
                f"in {MANIFEST_NAME}"
            )
            continue
        if name not in listed:
            found.append(
                f"{run}: {name} is on disk but absent from {MANIFEST_NAME} -- "
                f"nothing recorded it, so nothing says what it should hash to"
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
