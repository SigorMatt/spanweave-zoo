"""The invariant gate, watched failing (`tests/gates.py`).

The gate is asserted twice: once against a **planted violation** and once
against the real package. The first assertion is the one that matters. A gate
that has only ever been seen passing is indistinguishable from a gate that
cannot fail.
"""

import pytest

from tests import gates

# Every shape an import of the analysers can take. The point of the list is
# that a gate written as a grep for `^import spanweave` passes the first line
# and fails every other one.
PLANTED = [
    ("import spanweave", "spanweave"),
    ("import spanweave_live", "spanweave_live"),
    ("import spanweave as sw", "spanweave"),
    ("import spanweave_live as live", "spanweave_live"),
    ("from spanweave import build", "spanweave"),
    ("from spanweave import build as b", "spanweave"),
    ("from spanweave.adapters import classify", "spanweave.adapters"),
    ("from spanweave_live.serve import Serve", "spanweave_live.serve"),
    ("import json, spanweave", "spanweave"),
    ("def load():\n    import spanweave\n    return spanweave", "spanweave"),
    ("class C:\n    import spanweave_live", "spanweave_live"),
    ("try:\n    import spanweave\nexcept ImportError:\n    pass", "spanweave"),
    (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from spanweave import Graph",
        "spanweave",
    ),
]


@pytest.mark.parametrize(("source", "expected"), PLANTED)
def test_gate_fails_on_a_planted_violation(source, expected):
    found = gates.check_source("spanweave_zoo/planted.py", source)
    assert [v.rule for v in found] == ["no-analyser-imports"]
    assert expected in found[0].detail


@pytest.mark.parametrize(("source", "expected"), PLANTED)
def test_gate_exempts_the_audit_module(source, expected):
    # The audit is the one module whose job is to run both libraries over a
    # capture (SPEC.md section 7). Every shape the gate catches elsewhere is
    # allowed there -- including the nested and aliased ones.
    assert gates.check_source("spanweave_zoo/audit.py", source) == []


def test_the_exemption_is_one_path_and_not_a_file_name():
    # The exemption is `spanweave_zoo/audit.py` -- that path (SPEC.md section
    # 7). A gate that matched the *name* would exempt any file called
    # `audit.py` anywhere, so a module could be moved one directory down and
    # keep an exemption nobody granted it.
    for path in (
        "spanweave_zoo/sink/audit.py",
        "spanweave_zoo/replay/audit.py",
        "tests/audit.py",
        "audit.py",
    ):
        found = gates.check_source(path, "import spanweave")
        assert [v.rule for v in found] == ["no-analyser-imports"], path


def test_the_exemption_is_by_file_not_by_directory():
    # `spanweave_zoo/sink/audit_helpers.py` is not the audit module, and a
    # path that merely contains the word must not inherit the exemption.
    for path in (
        "spanweave_zoo/audit_helpers.py",
        "spanweave_zoo/audit/sink.py",
        "spanweave_zoo/not_audit.py",
    ):
        found = gates.check_source(path, "import spanweave")
        assert [v.rule for v in found] == ["no-analyser-imports"], path


def test_gate_passes_on_things_that_merely_look_alike():
    # The gate must not fire on the package's own name, on prose, or on a
    # string -- otherwise the first false positive gets it switched off, which
    # is worse than not having it.
    innocent = "\n".join(
        [
            '"""Records what spanweave would be fed. Imports it never."""',
            "# from spanweave import build  -- deliberately not done here",
            "import spanweave_zoo",
            "from spanweave_zoo.cli import verify",
            'LIBRARIES = ("spanweave", "spanweave_live")',
        ]
    )
    assert gates.check_source("spanweave_zoo/sink.py", innocent) == []


def test_the_package_imports_neither_analyser():
    found = gates.check_package()
    assert found == [], "\n".join(str(v) for v in found)


def test_the_gate_actually_scanned_something():
    # A gate that silently scans zero files passes forever. This is the
    # tripwire for that.
    assert len(gates.package_files()) >= 2
