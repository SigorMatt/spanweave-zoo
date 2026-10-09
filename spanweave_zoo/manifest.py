"""`MANIFEST.json`: where a body's sha256 lives, and nothing else yet.

`CLAUDE.md` §0.6 rule 2 says a capture is immutable -- "bytes as received, with
the request headers beside them and **a sha256 of each body in the manifest**"
-- and `zoo verify` re-hashes every capture on every `make check`. That makes
the digest the one part of `MANIFEST.json` the sink cannot defer: without it
there is nothing to re-hash against, and "immutable" is a claim nobody checks.

So this module is deliberately a third of a manifest. It owns the `bodies`
entries (`SPEC.md` §3.5) and the re-hash, and it owns them *alone*: there is
exactly one home for a digest, so the sha256 is not also copied into
`NNNN.headers.json`. Everything else `MANIFEST.json` will carry -- the pet
project's own manifest, `sink_version`, `collector_version`, `kind`,
`started_at` / `ended_at`, each entry's `content_type` / `content_encoding`,
the `json/` hashes -- is `SPEC.md` §5, added by A3 to this same file and these
same entries. A3 extends; it does not replace, and it has no second source of
truth to reconcile.

Nothing here parses a body. It hashes bytes and counts them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_NAME = "MANIFEST.json"

# The key under which the per-body entries live. A3's fields sit beside it.
BODIES = "bodies"


@dataclass(frozen=True, slots=True)
class BodyEntry:
    """One recorded body, as the manifest carries it (`SPEC.md` §3.5)."""

    file: str
    """The body's path relative to the run directory: `raw/0001.body`."""

    sha256: str
    bytes: int

    def as_document(self) -> dict[str, Any]:
        return {"bytes": self.bytes, "file": self.file, "sha256": self.sha256}


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


def append_body(run: Path, entry: BodyEntry) -> None:
    """Add one body to the run's manifest, creating the file if need be.

    Appends rather than rewrites the list, so entries stay in the order the
    bodies were recorded -- which is receipt order, the only ordering a capture
    carries (`SPEC.md` §2.2).
    """
    path = run / MANIFEST_NAME
    document: dict[str, Any] = {BODIES: []}
    if path.exists():
        document = read(run)
    bodies: list[Any] = list(document[BODIES])
    bodies.append(entry.as_document())
    document[BODIES] = bodies
    write_json(path, document)


def problems(run: Path) -> list[str]:
    """Re-hash one run against its manifest. Returns one line per problem.

    An empty list means every listed body is on disk with the length and the
    sha256 the manifest recorded. Anything else -- including a manifest that
    cannot be read -- is a line here, and a non-zero exit upstream.

    What this does *not* check, and `SPEC.md` §5 leaves to A3: a body present
    on disk but absent from the manifest.
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
    return found


def body_count(run: Path) -> int:
    """How many bodies the run's manifest lists. Zero if it has none."""
    try:
        return len(read(run)[BODIES])
    except (OSError, ValueError):
        return 0
