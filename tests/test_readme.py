"""The README's two contract digests are recomputed, not trusted.

`README.md`, "Provenance of the contract and the briefs", prints a sha256 for
`EXPORT-CONTRACT.md` and one for `ZOO-BRIEFS.md` and says those digests are how
"byte-identical to the ones handed to the project" is checked. A digest printed
in prose is checked by nobody: edit either document and the README goes on
claiming the old bytes, which is the one thing the Provenance section exists to
rule out.

So the digests are recomputed here, from the files on disk, on every
`make check`. The test fails on drift in **either** direction -- a document
edited, or a digest edited -- and names which file, because the fix differs:
a deliberate revision of the contract is a new version with a new digest in
the README, while an accidental edit is a revert.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"

# The documents the Provenance section accounts for, and the only ones: the
# two files handed to the pet projects.
CONTRACT_FILES = ("EXPORT-CONTRACT.md", "ZOO-BRIEFS.md")

# `<64 hex>  <file name>`, which is `sha256sum`'s own output format, so the
# block in the README can be checked by pasting it into `sha256sum -c`.
DIGEST_LINE = re.compile(r"^([0-9a-f]{64})  (\S+)$", re.MULTILINE)


def printed_digests() -> dict[str, str]:
    """Every `<sha256>  <file>` line the README prints, by file name."""
    return {
        name: sha
        for sha, name in DIGEST_LINE.findall(README.read_text(encoding="utf-8"))
    }


def test_the_readme_prints_a_digest_for_each_contract_document():
    # A README that stopped printing one of the two would otherwise pass the
    # drift test below by having nothing to compare.
    assert sorted(printed_digests()) == sorted(CONTRACT_FILES)


def test_each_printed_digest_is_the_digest_of_the_file_on_disk():
    printed = printed_digests()
    for name in CONTRACT_FILES:
        data = (REPO / name).read_bytes()
        assert printed[name] == hashlib.sha256(data).hexdigest(), (
            f"{name} and the sha256 the README prints for it have drifted. "
            f"The documents are the record and nothing here reflows them "
            f"(README.md, Provenance): either the edit to {name} is a "
            f"deliberate revision whose digest belongs in the README, or it "
            f"is one to revert."
        )


def test_the_readme_states_the_contract_version_the_contract_states():
    # "Both root copies are **contract version 1.1**" is checkable against the
    # contract's own declaration, which is its third line.
    contract = (REPO / "EXPORT-CONTRACT.md").read_text(encoding="utf-8")
    declared = re.search(r"^Contract version \*\*([0-9.]+)\*\*", contract, re.MULTILINE)
    assert declared is not None, "EXPORT-CONTRACT.md no longer declares a version"
    readme = README.read_text(encoding="utf-8")
    assert f"**contract version {declared.group(1)}**" in readme
