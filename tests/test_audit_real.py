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

pytest.importorskip("spanweave")
pytest.importorskip("spanweave_live")
pytest.importorskip("agentgolden")

from spanweave_zoo import audit, cli
from tests.test_replay import Clock, crafted, head_octets

pytestmark = pytest.mark.needs_audit

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


def test_a_capture_that_does_not_verify_is_refused(tmp_path, capsys):
    run = tmp_path / "fixtures" / "capture"
    shutil.copytree(FIXTURE, run)
    body = run / "raw" / "0001.body"
    body.write_bytes(body.read_bytes() + b"\x00")
    out = tmp_path / "audit"
    assert cli.main(["audit", str(run), "--out", str(out)]) == 2
    assert "does not verify" in capsys.readouterr().err
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
