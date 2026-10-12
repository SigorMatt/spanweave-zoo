"""The licence exists, says MIT, and is declared where a tool reads it.

Until A0a this repository had no `LICENSE` and no `license` field, so the built
wheel carried no licence at all (review thread T5): a recorder whose whole
product is other people's bytes, published for strangers to reproduce findings
from, with nothing saying what they may do with it.

Three places have to agree, and they drift independently: the file, the
metadata `pip` and PyPI read (`pyproject.toml`), and the README's claim about
it. `make install-check` holds the fourth -- that the wheel actually ships the
file -- because that is the one only a build can answer.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LICENSE = REPO / "LICENSE"

# The holder, spelled as `spanweave` and `spanweave-live` spell it. Three
# repositories that are read together should not differ here.
HOLDER = "MATTHEW SIGURKO"


def metadata() -> dict[str, object]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return dict(data["project"])


def test_the_licence_file_is_mit_and_names_the_holder():
    text = LICENSE.read_text(encoding="utf-8")
    assert text.startswith("MIT License"), text[:40]
    assert HOLDER in text, "LICENSE does not name the copyright holder"
    assert "WITHOUT WARRANTY OF ANY KIND" in text, "the MIT text is incomplete"


def test_the_package_declares_the_licence_it_ships():
    project = metadata()
    assert project["license"] == "MIT", project.get("license")
    assert project["license-files"] == ["LICENSE"], project.get("license-files")
    assert "License :: OSI Approved :: MIT License" in project["classifiers"]


def test_the_readme_names_the_licence_the_package_declares():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "MIT licensed (`LICENSE`)" in readme, (
        "the README does not say what the package's metadata says"
    )
