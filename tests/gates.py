"""The invariant gate, as a reusable check over source text.

One gate (`CLAUDE.md` §0.6): **no module under `spanweave_zoo/` imports
`spanweave` or `spanweave_live` except `audit.py`.** The sink records bytes and
the replayer re-sends them; neither may learn what a span means, and the
separation is what keeps a capture a record rather than an interpretation. The
audit is the one module whose whole job is to run the two libraries over a
capture, so it is the one exemption.

It is an AST check, not a grep: a grep is fooled by a comment, a docstring and
a line it never thought of, while the AST sees `import spanweave` wherever it
is -- aliased (`import spanweave as sw`), renamed through `from` (`from
spanweave import build as b`), nested inside a function or a `try`, or hidden
under an `if TYPE_CHECKING`. All of those are imports, and all of them are
caught.

The rule lives here, apart from `test_gates.py`, so that it can be run against
a **planted violation** -- source that deliberately breaks it -- as well as
against the real package. A gate nobody has watched fail is a gate nobody knows
works.
"""

from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "spanweave_zoo"

# The libraries the zoo is a capture harness *for*, and must not become a
# consumer of. Submodules count: `spanweave.adapters` is `spanweave`.
ANALYSER_MODULES = ("spanweave", "spanweave_live")

# The one exemption, by file name at the package root (`SPEC.md` §7). Written
# by A5; absent until then, which the gate does not mind -- an exemption for a
# file that does not exist yet exempts nothing.
EXEMPT_FILES = ("audit.py",)


@dataclass(frozen=True)
class Violation:
    """One gate failure, located precisely enough to fix."""

    rule: str
    path: str
    line: int
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.detail}"


def _imported_modules(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Every module name any `import` in the tree names, with its line.

    `ast.walk` reaches nested statements, so an import inside a function, a
    `try` or an `if TYPE_CHECKING:` is reported like any other. An `as` clause
    renames the binding and not the module, so the alias is irrelevant and the
    name reported is always the real one.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            # `from spanweave import build` names the module in `.module`;
            # `from spanweave.adapters import x` is covered by the same name.
            yield node.module, node.lineno


def _matches_module(imported: str, banned: str) -> bool:
    """`spanweave.adapters` matches `spanweave`; `spanweave_zoo` does not."""
    return imported == banned or imported.startswith(banned + ".")


def no_analyser_imports(path: str, source: str, tree: ast.AST) -> list[Violation]:
    """The gate. `path` decides the exemption, so it must be the real path."""
    if pathlib.PurePath(path).name in EXEMPT_FILES:
        return []
    found = []
    for imported, line in _imported_modules(tree):
        for banned in ANALYSER_MODULES:
            if _matches_module(imported, banned):
                found.append(
                    Violation(
                        "no-analyser-imports",
                        path,
                        line,
                        f"imports {imported!r}; only "
                        f"{'/'.join(EXEMPT_FILES)} may consume the libraries "
                        f"the zoo captures for (CLAUDE.md section 0.6)",
                    )
                )
    return found


def check_source(path: str, source: str) -> list[Violation]:
    """Run the gate over one piece of source text."""
    return no_analyser_imports(path, source, ast.parse(source))


def package_files() -> list[pathlib.Path]:
    """Every module under `spanweave_zoo/`, in sorted order."""
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def check_package() -> list[Violation]:
    """Run the gate over the whole package."""
    found: list[Violation] = []
    for file in package_files():
        relative = file.relative_to(PACKAGE_ROOT.parent)
        found.extend(check_source(str(relative), file.read_text(encoding="utf-8")))
    return found
