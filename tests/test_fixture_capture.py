"""The committed capture, and the gate that reads it (`SPEC.md` §5.6).

`make verify` is the gate behind the immutability claim, and until A3d it had
nothing to check: `captures/` was empty in this repository (until Z4's were
committed), so every CI run re-hashed zero bytes and said so. A gate that
passes over nothing is not a gate -- it is a line in a log.

So one real capture is committed under `tests/fixtures/capture/`: one OTLP
protobuf body through the real tee (`tests/otlp.py`'s hand-built export into
the raw sink, the stock Collector behind it, its JSON re-encoding into the json
sink), with both headers files on each side, both journals and the manifest the
run assembled. `make verify` re-hashes it on every `make check`, here and in
CI.

It is a capture, so nothing here repairs it. These tests read it, and a test
that wanted it changed would be asking for a capture to be edited, which is a
halt point (`CLAUDE.md`). It is deliberately **not** under
`captures/`: `captures/` is where the zoo's own recorded runs go, and a fixture
is not one of them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from spanweave_zoo import cli, manifest
from tests import otlp

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "capture"

# Every file one request through the tee leaves behind: the body, the head as
# octets and as the zoo's CRLF split of them, on the raw side and the json side
# alike, plus the two journals, the Collector's log and the manifest
# (`SPEC.md` §2, §4.2).
EXPECTED_FILES = (
    "MANIFEST.json",
    "bodies.jsonl",
    "collector.log",
    "forwards.jsonl",
    "json/0001.json",
    "json/0001.headers.json",
    "json/0001.headers.raw",
    "raw/0001.body",
    "raw/0001.headers.json",
    "raw/0001.headers.raw",
)


def files_on_disk() -> list[str]:
    return sorted(
        path.relative_to(FIXTURE).as_posix()
        for path in FIXTURE.rglob("*")
        if path.is_file()
    )


def test_the_fixture_capture_is_committed_whole():
    assert files_on_disk() == sorted(EXPECTED_FILES)


def test_zoo_verify_passes_over_the_committed_capture(capsys):
    # The named-path form, which is what `make verify` runs: one run
    # directory, re-hashed in both directions (`SPEC.md` §5.6).
    assert cli.main(["verify", str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert "kind=recorded" in out
    assert "every recorded body still hashes to what was recorded" in out


def test_the_manifest_accounts_for_both_headers_files_on_both_sides():
    document = manifest.read(FIXTURE)
    accounted = {entry["file"] for entry in document["bodies"]} | {
        entry["file"] for entry in document["files"]
    }
    assert accounted == {name for name in EXPECTED_FILES if name != "MANIFEST.json"}
    assert document["ended_at"]
    assert "problems" not in document


def test_the_raw_side_is_the_protobuf_the_exporter_sent():
    # Byte-identical to the export, and protobuf rather than JSON: this is the
    # record, and the zoo never improved it (`SPEC.md` §1).
    body = (FIXTURE / "raw" / "0001.body").read_bytes()
    assert body == otlp.export_trace_service_request()
    assert not body.startswith(b"{")
    head = (FIXTURE / "raw" / "0001.headers.raw").read_bytes()
    assert head.startswith(b"POST /v1/traces HTTP/1.1\r\n")
    assert b"Content-Type: application/x-protobuf\r\n" in head


def test_the_json_side_is_the_collectors_re_encoding_of_that_same_span():
    # Proof that this capture came through the real Collector and not out of a
    # test's imagination: the JSON beside the protobuf carries the trace and
    # span ids the protobuf carried, in the Collector's own encoding of them.
    document = json.loads((FIXTURE / "json" / "0001.json").read_bytes())
    spans = [
        span
        for resource in document["resourceSpans"]
        for scope in resource["scopeSpans"]
        for span in scope["spans"]
    ]
    assert [span["name"] for span in spans] == [otlp.SPAN_NAME]
    assert spans[0]["traceId"] == otlp.TRACE_ID.hex()
    assert spans[0]["spanId"] == otlp.SPAN_ID.hex()


def test_make_verify_reads_the_committed_capture():
    # The gate is only a gate if the harness runs it over something. `make
    # check` depends on `verify`, and CI runs `make check` on every leg, so
    # naming the fixture in this target is what makes CI re-hash a capture.
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    target = makefile.split("\nverify:", 1)[1].split("\n\n", 1)[0]
    assert "zoo verify tests/fixtures/capture" in target
    assert "verify" in makefile.split("\ncheck:", 1)[1].splitlines()[0]
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "run: make check" in workflow


def test_the_committed_capture_is_sealed():
    # A3f regenerated this capture through the real tee so that it carries a
    # seal: a seal cannot be added to a capture after it is taken (`SPEC.md`
    # §5.6). Computed here from the definition, not from the implementation.
    document = manifest.read(FIXTURE)
    unsealed = {key: value for key, value in document.items() if key != "seal"}
    text = json.dumps(
        unsealed, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert document["seal"] == hashlib.sha256(text.encode("ascii")).hexdigest()


def test_each_headers_json_is_the_crlf_split_of_its_headers_raw():
    # On both sides of the tee: what the json says the request carried is the
    # octets split on CRLF and on nothing else (`SPEC.md` §2.3).
    for side in ("raw", "json"):
        octets = (FIXTURE / side / "0001.headers.raw").read_bytes()
        lines = octets.decode("latin-1").split("\r\n")
        expected = [
            [name, value.strip(" \t")]
            for name, _, value in (line.partition(":") for line in lines[1:] if line)
        ]
        parsed = json.loads((FIXTURE / side / "0001.headers.json").read_bytes())
        assert parsed["headers"] == expected
        method, path = lines[0].split(" ")[:2]
        assert (parsed["method"], parsed["path"]) == (method, path)
        # The request line whole, HTTP version and all (the decision of
        # 2026-10-11, "header rule"; A3g regenerated this capture for it).
        assert parsed["request_line"] == lines[0]
