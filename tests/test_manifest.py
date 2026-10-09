"""`MANIFEST.json`'s fields, and what `zoo verify` refuses (`SPEC.md` §5, A3).

These tests build a capture by hand -- a body file, its headers file, and the
manifest written through `manifest.label` / `append_body` / `finish` -- rather
than by running a sink. What they are about is the *manifest* and the re-hash:
the fields §5 names, and the two things `zoo verify` must refuse. That a real
POST really does leave its content type in `NNNN.headers.json` is
`test_capture.py`'s job, through the sink, over a socket.

A1 left "a body present on disk but absent from the manifest" deliberately
unimplemented (`SPEC.md` §5) so that this file's test would not be
pre-satisfied. It is implemented here, and iterating the *directory* rather
than the manifest is the whole of why it can be: a check that walks the
manifest can never notice a file the manifest does not mention.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spanweave_zoo import __version__, cli, manifest

# What `EXPORT-CONTRACT.md` §1 tells a pet project to write, which the zoo
# copies verbatim and never parses a field of. The values are a plausible
# shape, not a schema: nothing in `spanweave_zoo/` reads one of these keys.
PROJECT_MANIFEST = {
    "contract_version": "1.1",
    "endpoint": "http://localhost:4318",
    "framework": "openai",
    "framework_version": "2.6.1",
    "instrumentation": ["openinference-instrumentation-openai==0.1.33"],
    "mode": "real",
    "model": "gpt-4.1-mini",
    "platform": "Linux-7.0.0-28-generic-x86_64",
    "python": "3.14.0",
    "sdk": {
        "exporter": "opentelemetry-exporter-otlp-proto-http==1.37.0",
        "opentelemetry-sdk": "1.37.0",
    },
    "started_at": "2026-10-09T11:59:00+00:00",
}

BODY = b"bytes the zoo does not look at"
STARTED = "2026-10-09T12:00:00+00:00"
ENDED = "2026-10-09T12:00:09+00:00"


def hand_written_capture(
    tmp_path: Path,
    *,
    kind: str = "real",
    headers: list[list[str]] | None = None,
) -> Path:
    """One run directory with one body, labelled and finished."""
    run = tmp_path / "captures" / "z4" / "run-1"
    raw = run / "raw"
    raw.mkdir(parents=True)
    (raw / "0001.body").write_bytes(BODY)
    manifest.write_json(
        raw / ("0001" + manifest.HEADERS_SUFFIX),
        {
            "bytes": len(BODY),
            "headers": headers
            if headers is not None
            else [
                ["Content-Type", "application/x-protobuf"],
                ["Content-Encoding", "gzip"],
            ],
            "method": "POST",
            "path": "/v1/traces",
            "received_at": "2026-10-09T12:00:01+00:00",
        },
    )
    manifest.label(
        run,
        kind=kind,
        collector_version="0.162.0",
        project_manifest=PROJECT_MANIFEST,
        started_at=STARTED,
    )
    manifest.append_body(
        run,
        manifest.BodyEntry(
            file="raw/0001.body", sha256=manifest.digest(BODY), bytes=len(BODY)
        ),
    )
    manifest.finish(run, ended_at=ENDED)
    return run


# --- the fields `SPEC.md` §5 names ------------------------------------------


def test_the_manifest_carries_every_field_section_5_names(tmp_path):
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    assert document[manifest.PROJECT_MANIFEST] == PROJECT_MANIFEST
    assert document[manifest.SINK_VERSION] == __version__
    assert document[manifest.COLLECTOR_VERSION] == "0.162.0"
    assert document[manifest.KIND] == "real"
    assert document[manifest.STARTED_AT] == STARTED
    assert document[manifest.ENDED_AT] == ENDED
    assert cli.verify(tmp_path / "captures") == 0


def test_a_body_entry_carries_the_content_headers_the_request_declared(tmp_path):
    # Carried across from `NNNN.headers.json`, where they are already verbatim
    # (`SPEC.md` §5): the manifest writer copies two values the record already
    # holds, and nothing inspects a payload to get them.
    run = hand_written_capture(tmp_path)
    [entry] = manifest.read(run)[manifest.BODIES]
    assert entry["content_type"] == "application/x-protobuf"
    assert entry["content_encoding"] == "gzip"
    # A1's three keys are untouched: there is still one home for a digest.
    assert entry["file"] == "raw/0001.body"
    assert entry["sha256"] == manifest.digest(BODY)
    assert entry["bytes"] == len(BODY)


def test_a_request_that_declared_neither_carries_null_for_both(tmp_path):
    # Degenerate, and the honest answer: the sink has no content type of its
    # own to invent (`SPEC.md` §3.3), so neither has the manifest.
    run = hand_written_capture(tmp_path, headers=[["User-Agent", "curl/8.5.0"]])
    [entry] = manifest.read(run)[manifest.BODIES]
    assert entry["content_type"] is None
    assert entry["content_encoding"] is None
    assert cli.verify(tmp_path / "captures") == 0


def test_a_repeated_content_type_is_carried_once_and_the_record_keeps_both(tmp_path):
    # A header may legally repeat, which is why `headers.json` is a list of
    # pairs (`SPEC.md` §3.2). The manifest carries one value -- the first as
    # received -- and the record of the repeat stays where it was.
    run = hand_written_capture(
        tmp_path,
        headers=[
            ["Content-Type", "application/x-protobuf"],
            ["Content-Type", "application/json"],
        ],
    )
    [entry] = manifest.read(run)[manifest.BODIES]
    assert entry["content_type"] == "application/x-protobuf"


# --- `kind` is required -----------------------------------------------------


@pytest.mark.parametrize("kind", ["", "REAL", "live", "recorded?", None])
def test_a_capture_cannot_be_labelled_with_a_kind_the_spec_does_not_name(
    tmp_path, kind
):
    # `SPEC.md` §5: `recorded` or `real`, no default and no inference. A
    # `recorded` capture and a `real` capture differ only by this declaration,
    # and the audit keys off it, so a guess here would be a lie there.
    run = tmp_path / "captures" / "z4" / "run-1"
    run.mkdir(parents=True)
    with pytest.raises(ValueError) as refused:
        manifest.label(
            run,
            kind=kind,
            collector_version="0.162.0",
            project_manifest=PROJECT_MANIFEST,
            started_at=STARTED,
        )
    assert "recorded" in str(refused.value) and "real" in str(refused.value)
    assert not (run / manifest.MANIFEST_NAME).exists()


def test_both_kinds_the_spec_names_are_accepted_and_recorded_verbatim(tmp_path):
    for kind in ("recorded", "real"):
        run = hand_written_capture(tmp_path / kind, kind=kind)
        assert manifest.read(run)[manifest.KIND] == kind


def test_the_kind_is_never_inferred_from_the_projects_own_manifest(tmp_path):
    # The project's manifest says `"mode": "real"` (`EXPORT-CONTRACT.md` §1)
    # and this capture declares `recorded`. The zoo copies and does not
    # reconcile (`SPEC.md` §1.3): both declarations are in the record, which
    # is what a record is for.
    run = hand_written_capture(tmp_path, kind="recorded")
    document = manifest.read(run)
    assert document[manifest.KIND] == "recorded"
    assert document[manifest.PROJECT_MANIFEST]["mode"] == "real"


# --- the project's own manifest is copied, not parsed -----------------------


def test_the_projects_manifest_is_read_verbatim_from_the_path_given(tmp_path):
    path = tmp_path / "streaming-concierge" / "MANIFEST.json"
    path.parent.mkdir(parents=True)
    manifest.write_json(path, PROJECT_MANIFEST)
    assert manifest.read_project_manifest(path) == PROJECT_MANIFEST


def test_a_project_manifest_that_is_absent_is_a_loud_refusal(tmp_path):
    with pytest.raises(manifest.ProjectManifestUnreadable) as refused:
        manifest.read_project_manifest(tmp_path / "nowhere" / "MANIFEST.json")
    assert "MANIFEST.json" in str(refused.value)


def test_a_project_manifest_that_is_not_a_json_document_is_a_loud_refusal(tmp_path):
    path = tmp_path / "MANIFEST.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(manifest.ProjectManifestUnreadable) as refused:
        manifest.read_project_manifest(path)
    assert str(path) in str(refused.value)


# --- `zoo verify`: a stale hash, and a body nobody listed -------------------


def test_a_manifest_with_a_stale_hash_fails_verify(tmp_path, capsys):
    # The A3 row's first acceptance test. The *manifest* is what went stale
    # here, not the body: a digest recorded for bytes that are not these
    # bytes is the same failure from the other side, and a verify that
    # compared lengths would miss it -- the length still agrees.
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    stale = manifest.digest(BODY + b"!")
    document[manifest.BODIES][0]["sha256"] = stale
    manifest.write_json(run / manifest.MANIFEST_NAME, document)

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "raw/0001.body" in out
    assert stale in out


def test_a_body_on_disk_that_the_manifest_does_not_list_fails_verify(tmp_path, capsys):
    # The A3 row's second acceptance test, which A1 deliberately left
    # unimplemented so that it would be red here. A capture is the bytes that
    # were recorded; a body nobody recorded is not part of it, and a verify
    # that iterated the manifest would never see it.
    run = hand_written_capture(tmp_path)
    (run / "raw" / "0002.body").write_bytes(b"recorded by nobody")

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "raw/0002.body" in out
    assert "MANIFEST.json" in out


def test_a_listed_body_dropped_from_the_manifest_fails_verify(tmp_path, capsys):
    # The same failure reached by editing the manifest instead of the tree.
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    document[manifest.BODIES] = []
    manifest.write_json(run / manifest.MANIFEST_NAME, document)

    assert cli.verify(tmp_path / "captures") == 1
    assert "raw/0001.body" in capsys.readouterr().out


def test_a_headers_file_whose_body_is_not_listed_fails_verify(tmp_path, capsys):
    # Headers are part of the capture, not metadata about it (`SPEC.md` §2.3),
    # so a headers file beside no listed body is a body that went missing from
    # the manifest -- reported, not shrugged at.
    run = hand_written_capture(tmp_path)
    manifest.write_json(run / "raw" / ("0002" + manifest.HEADERS_SUFFIX), {})

    assert cli.verify(tmp_path / "captures") == 1
    assert "0002" + manifest.HEADERS_SUFFIX in capsys.readouterr().out


def test_verify_of_one_run_directory_re_hashes_that_run(tmp_path, capsys):
    # What the README tells an operator to type after a real run. A path that
    # is itself a run directory must be re-hashed rather than globbed for
    # projects two levels down -- which would find nothing and say so with a
    # zero exit, the one reassuring pass this command exists to refuse.
    run = hand_written_capture(tmp_path)
    assert cli.verify(run) == 0
    assert "1 body" in capsys.readouterr().out

    (run / "raw" / "0001.body").write_bytes(b"different bytes entirely")
    assert cli.verify(run) == 1
    assert "sha256" in capsys.readouterr().out
