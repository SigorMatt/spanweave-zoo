"""The README's claims about itself are checked here, not trusted.

Two of them. **Every command it prints is complete and runnable as printed** --
the README says so in "What exists today", and an operator reading top to bottom
types the first `zoo capture` they see, not the one introduced sixty lines
later. So each command in each `bash` block is parsed here with `cli._parser()`
itself, every `make` target is looked up in the `Makefile`, and every
`uv sync --extra` names an extra `pyproject.toml` declares. A flag the CLI
requires and the README omits fails the gates instead of failing a stranger.

And **the digests it prints are the files' own**. `README.md`, "Provenance of
the contract and the briefs", prints a sha256 for
`EXPORT-CONTRACT.md` and one for `ZOO-BRIEFS.md` and says those digests are how
"byte-identical to the ones handed to the project" is checked. A digest printed
in prose is checked by nobody: edit either document and the README goes on
claiming the old bytes, which is the one thing the Provenance section exists to
rule out. So the digests are recomputed here, from the files on disk, on every
`make check`. That test fails on drift in **either** direction -- a document
edited, or a digest edited -- and names which file, because the fix differs:
a deliberate revision of the contract is a new version with a new digest in
the README, while an accidental edit is a revert.
"""

from __future__ import annotations

import hashlib
import re
import shlex
import tomllib
from pathlib import Path

import pytest

from spanweave_zoo import capture, cli, collector

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"

# The documents the Provenance section accounts for, and the only ones: the
# two files handed to the pet projects.
CONTRACT_FILES = ("EXPORT-CONTRACT.md", "ZOO-BRIEFS.md")

# `<64 hex>  <file name>`, which is `sha256sum`'s own output format, so the
# block in the README can be checked by pasting it into `sha256sum -c`.
DIGEST_LINE = re.compile(r"^([0-9a-f]{64})  (\S+)$", re.MULTILINE)

# A ```bash fence and its contents. Only `bash` blocks: the `Ctrl-C` of the
# operator flow is fenced without a language on purpose -- it is a keystroke,
# not a command, and nothing can parse it.
BASH_BLOCK = re.compile(r"^```bash\n(.*?)^```$", re.MULTILINE | re.DOTALL)

# The programs the README is allowed to print. Not a style rule: each of these
# is checked below, and a command starting with anything else would be printed
# as runnable with nothing here holding it so. Adding one means teaching
# `test_every_command_the_readme_prints_is_one_this_test_checks` how to check
# it, which is the point.
KNOWN_PROGRAMS = frozenset({"uv", "make", "timeout"})

# `make` targets the README prints that are NOT the zoo's. They are the pet
# project's own commands, and `EXPORT-CONTRACT.md` is where they come from --
# asserted below, so this exemption cannot become a place to park a target
# nobody declares.
FOREIGN_MAKE_TARGETS = frozenset({"run-real", "run-recorded"})

# Where the shell takes over: a redirect, a pipe or a background `&` ends the
# command's own arguments. `zoo capture ... > capture.log 2>&1 &` is one
# command whose argv stops at the `>`.
SHELL_OPERATORS = ("|", ">", "<", "&", ";")


def readme_commands() -> list[str]:
    """Every command the README prints in a `bash` block, comments stripped.

    Backslash continuations are joined, because what the operator pastes is
    one command however many lines it is printed over.
    """
    commands: list[str] = []
    for block in BASH_BLOCK.findall(README.read_text(encoding="utf-8")):
        joined = block.replace("\\\n", " ")
        for line in joined.splitlines():
            text = line.split("#", 1)[0].strip()
            if text:
                commands.append(text)
    return commands


def argv_of(command: str) -> list[str]:
    """The command's own argv: tokens up to where the shell takes over."""
    argv: list[str] = []
    for token in shlex.split(command):
        if token.startswith(SHELL_OPERATORS) or token == "2>&1":
            break
        argv.append(token)
    return argv


def declared_extras() -> set[str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return set(data["project"]["optional-dependencies"])


def declared_make_targets() -> set[str]:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z][\w-]*):", makefile, re.MULTILINE))


def test_the_readme_prints_commands_at_all():
    # Every test below is vacuous on a README that prints none, and the
    # operator section is the README's reason to exist.
    assert len(readme_commands()) >= 8


@pytest.mark.parametrize("command", readme_commands())
def test_every_command_the_readme_prints_is_one_this_test_checks(command):
    program = argv_of(command)[0]
    assert program in KNOWN_PROGRAMS, (
        f"the README prints `{command}` as runnable and nothing checks it. "
        f"Teach this test how to check `{program}` rather than widening "
        f"KNOWN_PROGRAMS and leaving the claim unheld."
    )


@pytest.mark.parametrize("command", readme_commands())
def test_every_zoo_command_the_readme_prints_parses_as_printed(command):
    """A `zoo` command in the README is complete: the real parser accepts it.

    This is the test for the first `zoo capture` an operator meets. It used to
    be `zoo capture --project z4 --run-id ...` -- exit 2, "the following
    arguments are required: --kind, --project-manifest", because both flags
    were introduced sixty lines further down the page.
    """
    argv = argv_of(command)
    if argv[:2] == ["uv", "run"]:
        argv = argv[2:]
    if not argv or argv[0] != "zoo":
        return
    # `parse_args` exits on a missing required flag, an unknown flag and a
    # misspelled subcommand alike, which is exactly the set of ways a printed
    # command fails for a reader.
    cli._parser().parse_args(argv[1:])


@pytest.mark.parametrize("command", readme_commands())
def test_every_make_target_the_readme_prints_exists(command):
    argv = argv_of(command)
    if argv[0] != "make":
        return
    targets = [arg for arg in argv[1:] if "=" not in arg]
    for target in targets:
        if target in FOREIGN_MAKE_TARGETS:
            continue
        assert target in declared_make_targets(), (
            f"the README prints `{command}` and the Makefile has no `{target}` target"
        )


@pytest.mark.parametrize("command", readme_commands())
def test_every_uv_sync_extra_the_readme_prints_is_declared(command):
    argv = argv_of(command)
    if argv[:2] != ["uv", "sync"]:
        return
    for position, token in enumerate(argv):
        if token == "--extra":
            extra = argv[position + 1]
            assert extra in declared_extras(), (
                f"the README prints `{command}` and pyproject.toml declares "
                f"no `{extra}` extra"
            )


def test_the_foreign_make_targets_are_the_contracts_own():
    # The exemption above is only honest if the pet project really was asked
    # for these commands: `EXPORT-CONTRACT.md` is what it was handed.
    contract = (REPO / "EXPORT-CONTRACT.md").read_text(encoding="utf-8")
    for target in FOREIGN_MAKE_TARGETS:
        assert f"make {target}" in contract, (
            f"`make {target}` is exempted as the pet project's own command, "
            f"but EXPORT-CONTRACT.md never asks for it"
        )


def test_the_operator_flow_is_numbered_and_starts_with_uv_sync():
    """The flow is a numbered list, and step 1 installs what the rest needs.

    `uv run zoo ...` is unrunnable in a bare checkout until the dev extra is
    synced, and the step that does it used to be prose beside the list rather
    than a step in it -- so the numbered flow was short by exactly the command
    an operator had to type first (review finding F15).
    """
    text = README.read_text(encoding="utf-8")
    start = text.index("## Running a pet project's real run")
    section = text[start : text.index("\n## ", start + 1)]

    steps = [int(n) for n in re.findall(r"^\*\*(\d+)\.", section, re.MULTILINE)]
    assert steps, "the operator flow is not numbered"
    assert steps == list(range(1, len(steps) + 1)), (
        f"the operator flow's steps are {steps}, not 1..{len(steps)}"
    )

    first = BASH_BLOCK.findall(section)[0].strip()
    assert first == "uv sync --extra dev", (
        f"the operator flow's first command is `{first}`, not `uv sync --extra dev`"
    )


def test_the_readme_waits_on_the_line_the_code_actually_prints():
    """The readiness line in the README is the one `zoo capture` prints.

    Step 3 tells the operator to wait for a line, and prints a `grep` that a
    supervisor can wait on. A line quoted in prose drifts from the string the
    code prints with nothing failing -- and what it costs is a script that
    waits thirty seconds for a line that will never come, or an operator who
    starts the pet project before the capture exists.
    """
    text = README.read_text(encoding="utf-8")
    flattened = " ".join(text.split())
    assert capture.READY_LINE in flattened, (
        f"the README does not print the readiness line as it is: {capture.READY_LINE!r}"
    )

    anchored = re.search(r'grep -q "\^([^"]+)"', text)
    assert anchored is not None, "the README prints no anchored wait for it"
    assert capture.READY_LINE.startswith(anchored.group(1)), (
        f"the README's wait pattern {anchored.group(1)!r} does not match the "
        f"start of {capture.READY_LINE!r}"
    )


def test_the_readme_does_not_count_the_commands_it_prints():
    """A count in prose is a third place for the flow to disagree with itself.

    The README said "Five commands, in two terminals" while the plan's row
    said four and a `Ctrl-C` and an operator had to type six (review finding
    F15). The list is numbered; the numbers are the count, and nothing else
    claims one.
    """
    counted = re.findall(
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
        r"[ -]commands?\b",
        README.read_text(encoding="utf-8"),
        re.IGNORECASE,
    )
    assert not counted, (
        f"the README counts its commands ({counted}); the numbered steps are "
        f"the count, and a second one drifts from them"
    )


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


def operator_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## Running a pet project's real run")
    return text[start : text.index("\n## ", start + 1)]


def test_the_log_variant_waits_on_the_file_it_redirects_to():
    """The supervisor's wait reads the log the capture writes, for this run.

    A3g; run-2b review N-4 (run 2's N-9). Step 3's log-to-file variant is two
    commands: `zoo capture ... > <log>` and a `timeout ... grep ... <log>`
    loop. Nothing held the two names together, so a README edit that renamed
    one waited thirty seconds on a file nothing writes and every suite stayed
    green. Both name the same file, the file names the run the command
    captures, every run id in the flow is that one, and the wait gives the
    zoo at least its own readiness budget before it gives up.
    """
    commands = [
        " ".join(block.replace("\\\n", " ").split())
        for block in BASH_BLOCK.findall(operator_section())
    ]
    variant = next(
        command for command in commands if "zoo capture" in command and ">" in command
    )
    capture_command, _, wait = variant.partition(" & ")
    redirect = re.search(r'> ("[^"]+"\S*)', capture_command)
    assert redirect is not None, "the variant redirects its log nowhere"
    log = redirect.group(1)
    assert log.startswith('"${TMPDIR:-/tmp}"/'), (
        f"the log {log} is not outside the checkout and the run directory"
    )

    timeout = re.fullmatch(
        r"\s*timeout (\d+(?:\.\d+)?) bash -c '(.*)'\s*", wait, re.DOTALL
    )
    assert timeout is not None, f"the wait is not a timeout loop: {wait!r}"
    loop = timeout.group(2)
    assert loop.rstrip("; ").split()[-1] == "done" and "sleep" in loop, (
        "the wait loop does not pause between looks"
    )
    grepped = re.search(r'grep -q "[^"]+" (\S+);', loop)
    assert grepped is not None, "the wait greps no file"
    assert grepped.group(1) == log, (
        f"the capture writes {log} and the wait reads {grepped.group(1)}"
    )

    run_id = argv_of(capture_command)[argv_of(capture_command).index("--run-id") + 1]
    assert log.endswith(f"/zoo-capture-{run_id}.log"), (
        f"the log {log} does not name the run it captures, {run_id}"
    )
    section = operator_section()
    named = set(re.findall(r"--run-id (\S+)", section)) | set(
        re.findall(r"captures/z4/([^\s/`]+)", section)
    )
    assert named == {run_id}, f"the flow names more than one run: {sorted(named)}"

    # The zoo itself waits up to READY_ATTEMPTS looks for the Collector, each
    # a pause and a connect that can take its whole timeout; a supervisor that
    # gives up sooner gives up on a capture that is still legitimately coming
    # up.
    budget = collector.READY_ATTEMPTS * (
        collector.READY_PAUSE + collector.READY_CONNECT_TIMEOUT
    )
    assert float(timeout.group(1)) >= budget, (
        f"the wait gives up after {timeout.group(1)}s; the zoo's own readiness "
        f"wait can take {budget:g}s"
    )


def test_step_4_names_the_key_a_real_run_needs():
    # A3g; run-2b review N-5. `make run-real` in z4's checkout exits 2 without
    # `OPENAI_API_KEY`, before it exports anything -- and the capture already
    # running has spent its run id on a run that recorded nothing.
    section = operator_section()
    step_4 = section[section.index("**4.") : section.index("**5.")]
    assert "OPENAI_API_KEY" in step_4
