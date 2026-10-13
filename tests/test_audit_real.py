"""The audit, run for real (`SPEC.md` §7).

Every test here needs the `audit` extra -- the three pinned libraries -- and
is marked `needs_audit`. They skip when it is absent, which is how they behave
on CI's `check` legs, and `make audit-check` (CI's `audit` leg) runs exactly
these and **fails if any of them skipped** (`tests/audit_check.py`).

`spanweave-live serve` runs as a real child process on a loopback port the
kernel chooses, and the capture is replayed into it through the zoo's own
replayer: the audit's claim is about what those two did with a capture, and a
fake receiver could only confirm what the test already believed.
"""

from __future__ import annotations

import shutil
import sys
import tomllib
from pathlib import Path

import pytest

from spanweave_zoo import cli
from tests.test_replay import Clock, _misplaced_copy, crafted, head_octets

# Not `pytest.importorskip` at module level: that skips the whole module at
# collection, before `-m` deselects anything, so the skip lands in every
# marker-selected run's report -- and `collector-check`, which fails on any
# skip, failed on f60f69c's `collector` leg. A per-item `skipif` is applied
# only to items that were selected, so a deselected test reports nothing.
try:
    from spanweave_zoo import audit
except ImportError:  # the `audit` extra is not installed
    audit = None  # type: ignore[assignment]

pytestmark = [
    pytest.mark.needs_audit,
    pytest.mark.skipif(
        audit is None,
        reason="needs the audit extra (uv sync --extra dev --extra audit)",
    ),
]

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "capture"
RECORDED = REPO / "captures" / "z4" / "2026-10-12-recorded"

OWNERS = {"spanweave", "spanweave-live", "agentgolden"}


def pyproject_pins() -> dict[str, str]:
    """The three shas as `pyproject.toml` writes them -- read independently of
    the audit, which reads them from the installed metadata."""
    document = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pins = {}
    for requirement in document["project"]["optional-dependencies"]["audit"]:
        name, _, url = requirement.partition(" @ ")
        pins[name.strip()] = url.rsplit("@", 1)[1]
    return pins


@pytest.fixture(scope="module")
def fixture_audit(tmp_path_factory):
    out = tmp_path_factory.mktemp("audit")
    result = audit.audit(FIXTURE, out=out)
    return result, result.path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def recorded_audit(tmp_path_factory):
    # Z4's `recorded` capture, committed under captures/: a stranger's trace,
    # read and never changed. The fixture capture's one hand-built span is
    # claimed by no adapter, so it yields no graph; this one does.
    out = tmp_path_factory.mktemp("audit")
    result = audit.audit(RECORDED, out=out)
    return result, result.path.read_text(encoding="utf-8")


# --- the committed fixture capture, audited ----------------------------------


def test_the_fixture_capture_is_audited_and_the_report_written(fixture_audit):
    result, text = fixture_audit
    assert result.exit == 0, result.incomplete
    assert result.path.name == "fixtures-capture.md"
    for heading in (
        "## Method",
        "## Findings",
        "## Step 1",
        "## Step 2",
        "## Step 3",
        "## Step 4",
        "## Step 5",
    ):
        assert heading in text, heading


def test_the_report_header_records_all_three_pinned_shas(fixture_audit):
    _, text = fixture_audit
    pins = pyproject_pins()
    assert set(pins) == OWNERS
    for name, sha in pins.items():
        assert f"| {name} |" in text
        # Pinned and installed: the same sha twice on the library's row.
        row = next(line for line in text.splitlines() if line.startswith(f"| {name} |"))
        assert row.count(sha) == 2, row


def test_a_415_on_protobuf_is_a_finding_owned_by_spanweave_live(fixture_audit):
    result, _ = fixture_audit
    [refused] = [f for f in result.findings if f.step == 1]
    assert refused.owner == "spanweave-live"
    assert "415" in refused.title
    assert "unsupported_media_type" in refused.observed
    assert str(FIXTURE) in refused.capture


def test_every_finding_names_one_of_the_three_owners_and_carries_a_command(
    fixture_audit,
):
    result, _ = fixture_audit
    assert result.findings
    for finding in result.findings:
        assert finding.owner in OWNERS
        assert finding.commands
        assert finding.observed
        assert finding.expected


def test_the_live_graph_equals_the_batch_graph_byte_for_byte(recorded_audit):
    # Prefix consistency on a stranger's trace (spanweave's SPEC.md 10.1).
    # Every identified trace serve wrote has a partition, and its three
    # serializations agree.
    result, _ = recorded_audit
    identified = [p for p in result.partitions if p.trace_id is not None]
    assert identified
    for partition in identified:
        assert partition.live is not None
        assert partition.live == partition.batch == partition.incremental
    assert not [f for f in result.findings if "differ" in f.title]


def test_steps_four_and_five_ran_on_every_written_graph(recorded_audit):
    result, text = recorded_audit
    assert [p for p in result.partitions if p.live is not None]
    for partition in result.partitions:
        if partition.live is None:
            continue
        assert partition.inspect_exit == 0
        assert partition.inspect_output.startswith("trace: ")
        assert partition.signature_steps is not None
    assert "spanweave inspect graphs/" in text


def test_the_method_section_states_the_completion_once(fixture_audit):
    _, text = fixture_audit
    assert text.count("Run.finish()") == 1
    assert "--requests" in text


# --- the owner rules (SPEC.md section 7.4) ------------------------------------


@pytest.mark.parametrize(
    ("live", "batch", "incremental", "owner"),
    [
        (b"a", b"a", b"a", None),
        (b"a", b"b", b"b", "spanweave-live"),
        (b"a", b"b", b"c", "spanweave"),
        (b"a", b"a", b"c", "spanweave"),
        (b"a", None, b"a", "spanweave"),
        (b"a", b"a", None, "spanweave"),
    ],
)
def test_a_divergence_is_owned_by_the_library_whose_graph_moved(
    live, batch, incremental, owner
):
    assert audit.divergence_owner(live, batch, incremental) == owner


# The real receiver, run as it is run, and then one byte appended to every graph
# file it wrote: a live graph that is not the batch graph while spanweave's own
# two builds still agree. The tampering is in the receiver's stand-in, outside
# the zoo, so the audit is exercised exactly as it runs; nothing under captures/
# is touched.
DIVERGING_SERVE = (
    sys.executable,
    "-c",
    "import runpy, sys\n"
    "from pathlib import Path\n"
    "sys.argv = ['spanweave-live', *sys.argv[1:]]\n"
    "code = 0\n"
    "try:\n"
    "    runpy.run_module('spanweave_live.cli', run_name='__main__')\n"
    "except SystemExit as stop:\n"
    "    code = stop.code\n"
    "for graph in sorted(Path('graphs').glob('*.json')):\n"
    "    graph.write_bytes(graph.read_bytes() + b'\\n')\n"
    "sys.exit(code)\n",
)


def test_a_live_batch_divergence_reaches_the_report_with_its_owner(tmp_path):
    # SPEC.md section 7.4: live != batch where incremental = batch is
    # spanweave-live's. `divergence_owner` is tested directly above; this is
    # the path from it to a finding and to the report (REVIEW-2026-10-12 R-1).
    result = audit.audit(RECORDED, out=tmp_path, serve_command=DIVERGING_SERVE)
    assert result.exit == 0, result.incomplete
    identified = [p for p in result.partitions if p.trace_id is not None]
    assert identified
    diverged = [f for f in result.findings if f.step == 3 and "differ" in f.title]
    assert len(diverged) == len(identified)
    text = result.path.read_text(encoding="utf-8")
    for partition in identified:
        assert partition.live != partition.batch
        assert partition.batch == partition.incremental
        owner = audit.divergence_owner(
            partition.live, partition.batch, partition.incremental
        )
        assert owner == "spanweave-live"
        [finding] = [f for f in diverged if partition.trace_id in f.title]
        assert finding.owner == owner
        assert str(RECORDED) in finding.capture
        heading = f"live and batch graphs differ for {partition.trace_id}"
        assert f"{heading} -- owner: {owner}" in text
        assert f"| `{partition.trace_id}` |" in text
        assert f"differs ({owner})" in text


def test_a_signature_that_raises_is_a_finding_owned_by_agentgolden(tmp_path):
    def raising(graph):
        raise RuntimeError("planted")

    result = audit.audit(RECORDED, out=tmp_path, signature=raising)
    [smoke] = [f for f in result.findings if f.step == 5]
    assert smoke.owner == "agentgolden"
    assert "RuntimeError: planted" in smoke.observed
    assert result.exit == 0


# --- a stranger's trace: the committed Z4 capture ----------------------------


def test_a_record_no_adapter_claims_is_two_findings_with_two_owners(
    recorded_audit,
):
    # Z4's root span carries no attribute any adapter reads: classify claims it
    # for nobody (spanweave), so the receiver routes it to its no-trace
    # builder, which is never written (spanweave-live).
    result, _ = recorded_audit
    assert result.exit == 0, result.incomplete
    owners = {f.owner for f in result.findings if f.step == 3}
    assert owners == {"spanweave", "spanweave-live"}
    [lost] = [p for p in result.partitions if p.trace_id is None]
    assert lost.live is None
    assert lost.records == 1


# --- degenerate captures, and refusals ----------------------------------------


def test_a_capture_with_no_json_body_is_audited_as_far_as_it_goes(tmp_path):
    # The Collector never ran, so json/ is empty (SPEC.md section 2.4): step 1
    # runs, steps 2 to 5 cannot, and the exit says the audit is incomplete.
    clock = Clock("2026-10-09T13:00:00+00:00", "2026-10-09T13:00:01+00:00")
    body = b'{"resourceSpans": []}'
    run = crafted(
        tmp_path / "zx" / "no-json",
        [(lambda port: head_octets(port, body), body)],
        clock,
    )
    result = audit.audit(run, out=tmp_path / "audit")
    assert result.exit == 1
    assert any("json/" in reason for reason in result.incomplete)
    text = result.path.read_text(encoding="utf-8")
    assert "## Step 1" in text
    assert "not run" in text


def test_a_serve_that_never_starts_leaves_the_audit_incomplete(tmp_path):
    failing = (sys.executable, "-c", "import sys; sys.exit(3)")
    result = audit.audit(FIXTURE, out=tmp_path, serve_command=failing)
    assert result.exit == 1
    assert any("listening" in reason for reason in result.incomplete)


def test_a_serve_command_that_cannot_be_executed_still_writes_the_report(
    tmp_path, monkeypatch
):
    # SPEC.md sections 7.5 and 7.6: `Popen` raising `OSError` is `serve did
    # not start`, an incomplete step -- the report is still written and the
    # exit is 1, not a traceback and no report (Qodo Q5, B6 (b)).
    missing = (str(tmp_path / "no-such-serve"),)
    out = tmp_path / "audit"
    result = audit.audit(FIXTURE, out=out, serve_command=missing)
    assert result.exit == 1
    started = [r for r in result.incomplete if "serve did not start: " in r]
    assert [r.split(":", 1)[0] for r in started] == ["step 1", "step 2"]
    assert result.findings == []
    text = result.path.read_text(encoding="utf-8")
    assert "Incomplete: serve did not start: " in text
    for number in (3, 4, 5):
        section = text.split(f"## Step {number} ", 1)[1]
        assert section.split("\n\n", 2)[1].startswith("Not run: "), number
    # And through the CLI, which passes no seam: exit 1, the report written.
    monkeypatch.setitem(audit.audit.__kwdefaults__, "serve_command", missing)
    again = tmp_path / "cli"
    assert cli.main(["audit", str(FIXTURE), "--out", str(again)]) == 1
    assert (again / "fixtures-capture.md").is_file()


def test_a_reread_that_does_not_match_serve_runs_no_step_after_it(tmp_path):
    # SPEC.md section 7.3: the reconstruction is checked before it is
    # believed, and when it does not match what serve reported step 3 is
    # incomplete -- no partition is compared, steps 4 and 5 are not run, and
    # no finding is made from any of them (Qodo Q4, B6 (a)). The mismatch is
    # driven through the `reread` seam (section 7.6), on the Z4 capture whose
    # honest audit has step-3 findings and runs steps 4 and 5.
    def short(run, files):
        found = audit.reread(run, files)
        found.statuses = [599 for _ in found.statuses]
        return found

    result = audit.audit(RECORDED, out=tmp_path, reread=short)
    assert result.exit == 1
    [mismatch] = [r for r in result.incomplete if r.startswith("step 3")]
    assert "does not match serve" in mismatch
    assert [f for f in result.findings if f.step >= 3] == []
    assert result.partitions == []
    text = result.path.read_text(encoding="utf-8")
    for number in (3, 4, 5):
        section = text.split(f"## Step {number} ", 1)[1]
        assert section.split("\n\n", 2)[1].startswith("Not run: "), number
    assert "spanweave inspect graphs/" not in text
    assert "does not match serve" in text.split("## Step 3 ", 1)[1]


def test_a_routed_count_that_does_not_match_is_the_same_refusal(tmp_path):
    # The other half of the check: statuses equal, one record fewer than
    # serve's `routed`.
    def fewer(run, files):
        found = audit.reread(run, files)
        found.partitions[0].feed.pop()
        found.partitions[0].origins.pop()
        return found

    result = audit.audit(RECORDED, out=tmp_path, reread=fewer)
    assert result.exit == 1
    assert any("routed" in r for r in result.incomplete if r.startswith("step 3"))
    assert [f for f in result.findings if f.step >= 3] == []


def test_a_capture_that_does_not_verify_is_refused(tmp_path, capsys):
    run = tmp_path / "fixtures" / "capture"
    shutil.copytree(FIXTURE, run)
    body = run / "raw" / "0001.body"
    body.write_bytes(body.read_bytes() + b"\x00")
    out = tmp_path / "audit"
    assert cli.main(["audit", str(run), "--out", str(out)]) == 2
    assert "does not verify" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("case", ["raw-absolute", "raw-dotdot"])
def test_a_manifest_path_outside_the_run_is_refused_naming_it(tmp_path, capsys, case):
    # B4a (`OPEN_QUESTIONS.md` §7, option 1): such a run does not verify
    # (`SPEC.md` §5.4, §5.6), so the audit refuses it before reading anything
    # (§7.2) -- exit 2, no report -- and the refusal names the entry.
    run, entry = _misplaced_copy(tmp_path, case)
    out = tmp_path / "audit"
    assert cli.main(["audit", str(run), "--out", str(out)]) == 2
    err = capsys.readouterr().err
    assert "does not verify" in err
    assert repr(entry) in err, err
    assert not out.exists()


def test_a_path_that_is_not_a_run_is_refused(tmp_path, capsys):
    out = tmp_path / "audit"
    assert cli.main(["audit", str(tmp_path / "nothing"), "--out", str(out)]) == 2
    assert str(tmp_path / "nothing") in capsys.readouterr().err
    assert not out.exists()


def test_an_installed_sha_that_is_not_the_pin_is_refused(tmp_path):
    with pytest.raises(audit.AuditRefused, match="spanweave"):
        audit.audit(FIXTURE, out=tmp_path, installed=lambda name: "0" * 40)
    assert not list(tmp_path.iterdir())
