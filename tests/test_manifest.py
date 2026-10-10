"""`MANIFEST.json`'s fields, and what `zoo verify` refuses (`SPEC.md` §5, A3).

These tests build a capture by hand -- a body file, its headers file, and the
manifest written through `manifest.label` / `journal_body` / `finish` -- rather
than by running a sink. What they are about is the *manifest* and the re-hash:
the fields §5 names, and everything `zoo verify` must refuse. That a real
POST really does leave its content type in `NNNN.headers.json` is
`test_capture.py`'s job, through the sink, over a socket.

A1 left "a body present on disk but absent from the manifest" deliberately
unimplemented (`SPEC.md` §5) so that this file's test would not be
pre-satisfied. It is implemented here, and iterating the *directory* rather
than the manifest is the whole of why it can be: a check that walks the
manifest can never notice a file the manifest does not mention.

A3b finished that thought (`SPEC.md` §5.6): every file in a run directory has
a digest of its own, so rewriting a *headers* file fails verify too, and a
capture that was never completed or that recorded a problem does not pass a
check whose whole job is trust.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from spanweave_zoo import __version__, cli, manifest, sink

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
    # After the capture's own `started_at` below, because that is the order a
    # run happens in: the operator brings the capture up, then runs the project
    # (`README.md`, "Running a pet project's real run"), and the project writes
    # this document as it runs (`EXPORT-CONTRACT.md` §1). A document older than
    # the capture is an earlier run's, which is what A3b's check is about.
    "started_at": "2026-10-09T12:00:04+00:00",
}

BODY = b"bytes the zoo does not look at"

# The head that carried `BODY`, as the sink records it (`SPEC.md` §2.3): the
# request line and the header block, CRLFs intact, up to the blank line.
HEAD = (
    b"POST /v1/traces HTTP/1.1\r\n"
    b"Content-Type: application/x-protobuf\r\n"
    b"Content-Encoding: gzip\r\n"
    b"Content-Length: %d\r\n"
    b"\r\n"
) % len(BODY)

STARTED = "2026-10-09T12:00:00+00:00"
ENDED = "2026-10-09T12:00:09+00:00"


def project_manifest_file(tmp_path: Path, document: object = None) -> Path:
    """The path `--project-manifest` names, with a document at it."""
    path = tmp_path / "streaming-concierge" / "MANIFEST.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_json(path, PROJECT_MANIFEST if document is None else document)
    return path


def hand_written_capture(
    tmp_path: Path,
    *,
    kind: str = "real",
    headers: list[list[str]] | None = None,
    project_manifest: Path | None = None,
) -> Path:
    """One run directory with one body, labelled, journalled and finished."""
    run = tmp_path / "captures" / "z4" / "run-1"
    raw = run / "raw"
    raw.mkdir(parents=True)
    (raw / "0001.body").write_bytes(BODY)
    (raw / ("0001" + sink.HEADERS_RAW_SUFFIX)).write_bytes(HEAD)
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
    manifest.label(run, kind=kind, collector_version="0.162.0", started_at=STARTED)
    manifest.journal_body(
        run,
        manifest.BodyEntry(
            file="raw/0001.body", sha256=manifest.digest(BODY), bytes=len(BODY)
        ),
    )
    manifest.finish(
        run,
        ended_at=ENDED,
        project_manifest=project_manifest
        if project_manifest is not None
        else project_manifest_file(tmp_path),
        started_at=STARTED,
    )
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


# --- A3b: the manifest covers every file (`SPEC.md` §5.6) -------------------


def test_every_file_in_the_run_directory_has_a_digest(tmp_path):
    # The A3b row: a sha256 entry for every file in the run directory except
    # `MANIFEST.json`. The bodies are in `bodies`, everything else -- the
    # headers file, the journal -- is in `files`, each file exactly once, so
    # there is still one home for a digest.
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    accounted = {entry["file"] for entry in document[manifest.BODIES]} | {
        entry["file"] for entry in document[manifest.FILES]
    }
    on_disk = {
        path.relative_to(run).as_posix()
        for path in run.rglob("*")
        if path.is_file() and path.name != manifest.MANIFEST_NAME
    }
    assert accounted == on_disk
    assert "raw/0001" + manifest.HEADERS_SUFFIX in accounted
    assert manifest.JOURNAL_NAME in accounted
    for entry in document[manifest.FILES]:
        data = (run / entry["file"]).read_bytes()
        assert entry["sha256"] == manifest.digest(data)
        assert entry["bytes"] == len(data)


def test_a_rewritten_content_type_in_headers_json_fails_verify(tmp_path, capsys):
    # The A3b row's third acceptance test, and the whole point of covering
    # every file: the headers are the record of what the exporter claimed
    # about its own bytes (`SPEC.md` §2.3). Rewriting `Content-Type` in the
    # record changes what the capture says the request was, while every body
    # still hashes to what it hashed to.
    run = hand_written_capture(tmp_path)
    headers_file = run / "raw" / ("0001" + manifest.HEADERS_SUFFIX)
    document = json.loads(headers_file.read_text(encoding="utf-8"))
    document["headers"] = [["Content-Type", "application/json"]]
    manifest.write_json(headers_file, document)

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "raw/0001" + manifest.HEADERS_SUFFIX in out
    assert "sha256" in out
    # The body itself is untouched -- which is why a verify that only re-hashed
    # bodies reported this capture as verified.
    assert (run / "raw" / "0001.body").read_bytes() == BODY


def test_a_rewritten_head_in_headers_raw_fails_verify(tmp_path, capsys):
    # A3c's file is covered by the same walk, and for the same reason: the
    # octets of the head are the unmodified record of the request (`SPEC.md`
    # §2.3), so tidying a bare CR out of them -- the one thing that file exists
    # to hold -- is a capture that no longer says what arrived.
    run = hand_written_capture(tmp_path)
    head_file = run / "raw" / ("0001" + sink.HEADERS_RAW_SUFFIX)
    head_file.write_bytes(HEAD.replace(b"gzip", b"identity"))

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "raw/0001" + sink.HEADERS_RAW_SUFFIX in out
    assert "sha256" in out


def test_a_kind_the_spec_does_not_name_fails_verify(tmp_path, capsys):
    # The A3b row's fourth acceptance test. `kind` is the one field the audit
    # reads as the truth about a run (`SPEC.md` §5.2), so a manifest declaring
    # something the spec does not name is a capture `verify` refuses rather
    # than a capture with an odd string in it.
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    document[manifest.KIND] = "almost-real"
    manifest.write_json(run / manifest.MANIFEST_NAME, document)

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "almost-real" in out
    assert "recorded" in out and "real" in out


def test_a_capture_with_no_ended_at_fails_verify_and_says_how_to_remove_it(
    tmp_path, capsys
):
    # A capture whose run was killed between its first body and its last line.
    # Nothing says the manifest covers what is on disk, so it is not verified
    # -- and the fix is another capture, never an edited one.
    run = hand_written_capture(tmp_path)
    document = manifest.read(run)
    del document[manifest.ENDED_AT]
    manifest.write_json(run / manifest.MANIFEST_NAME, document)

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert manifest.ENDED_AT in out
    assert f"rm -rf {run}" in out


def test_a_problem_recorded_during_the_run_fails_verify(tmp_path, capsys):
    # A3a writes `problems` when something goes wrong that the capture cannot
    # fix -- a Collector that exited -- and A3b is where `zoo verify` starts
    # reading it (`SPEC.md` §4.6). A capture is never silently fine.
    run = hand_written_capture(tmp_path)
    manifest.append_problem(run, "collector exited: 137")

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert "collector exited: 137" in out


def test_a_journal_line_that_cannot_be_read_is_a_problem_not_a_dropped_body(
    tmp_path, capsys
):
    # Degenerate, and the honest answer. A run killed mid-write leaves half a
    # line in `bodies.jsonl`; the body it recorded is on disk with no entry of
    # its own. The capture says so -- a problem naming the journal -- and the
    # body is still hashed as a file, so nothing on disk is unaccounted for and
    # nothing is quietly listed as a recorded body either.
    run = tmp_path / "captures" / "z4" / "run-1"
    (run / "raw").mkdir(parents=True)
    (run / "raw" / "0001.body").write_bytes(BODY)
    manifest.label(run, kind="real", collector_version="0.162.0", started_at=STARTED)
    with (run / manifest.JOURNAL_NAME).open("a", encoding="utf-8") as journal:
        journal.write('{"bytes": 30, "file": "raw/0001.bo')

    found = manifest.finish(run, ended_at=ENDED)
    assert [problem for problem in found if manifest.JOURNAL_NAME in problem]
    document = manifest.read(run)
    assert document[manifest.BODIES] == []
    # Covered, but as a file rather than as a recorded body: nothing is lost
    # and nothing is claimed.
    assert "raw/0001.body" in {entry["file"] for entry in document[manifest.FILES]}

    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert manifest.JOURNAL_NAME in out
    assert "is not a JSON object" in out


# --- A3b: the project's own manifest is copied at the end (`SPEC.md` §5.3) --


def test_the_project_manifest_is_copied_as_it_stands_when_the_run_ends(tmp_path):
    run = hand_written_capture(tmp_path)
    assert manifest.read(run)[manifest.PROJECT_MANIFEST] == PROJECT_MANIFEST


def test_a_project_manifest_older_than_the_capture_is_a_problem_and_not_copied(
    tmp_path, capsys
):
    # The A3b row's second acceptance test, and the manifest-timing decision:
    # the project writes its manifest while it runs, so a document written
    # before this capture existed is an earlier run's. Carrying it would be the
    # capture claiming something about the run it recorded that is not true.
    stale = dict(PROJECT_MANIFEST, started_at="2026-10-09T11:00:00+00:00")
    run = hand_written_capture(
        tmp_path, project_manifest=project_manifest_file(tmp_path, stale)
    )
    document = manifest.read(run)
    assert document[manifest.PROJECT_MANIFEST] is None
    [problem] = document[manifest.PROBLEMS]
    assert "11:00:00" in problem and STARTED in problem

    assert cli.verify(tmp_path / "captures") == 1
    assert "11:00:00" in capsys.readouterr().out


def test_a_project_manifest_that_is_gone_by_the_end_is_a_problem_and_null(
    tmp_path, capsys
):
    path = project_manifest_file(tmp_path)
    path.unlink()
    run = hand_written_capture(tmp_path, project_manifest=path)
    document = manifest.read(run)
    assert document[manifest.PROJECT_MANIFEST] is None
    assert str(path) in document[manifest.PROBLEMS][0]
    assert cli.verify(tmp_path / "captures") == 1
    assert "does not carry one" in capsys.readouterr().out


def test_a_project_manifest_the_zoo_cannot_date_is_copied_with_a_problem(
    tmp_path, capsys
):
    # Degenerate: `EXPORT-CONTRACT.md` §1 asks for a `started_at` and this
    # project wrote none, so nothing here says whether the document is the
    # recorded run's. The document is kept -- the zoo does not drop a record it
    # was handed -- and the capture says it could not date it.
    undated = {
        key: value for key, value in PROJECT_MANIFEST.items() if key != "started_at"
    }
    run = hand_written_capture(
        tmp_path, project_manifest=project_manifest_file(tmp_path, undated)
    )
    document = manifest.read(run)
    assert document[manifest.PROJECT_MANIFEST] == undated
    assert "started_at" in document[manifest.PROBLEMS][0]
    assert cli.verify(tmp_path / "captures") == 1
    capsys.readouterr()


# --- A3b: 1,600 bodies cost the same each (`SPEC.md` §3.5) ------------------

BODIES = 1600
SAMPLE = 100
# Generous on purpose, and still nowhere near what it catches. What is under
# test is that the cost of recording a body does not GROW with the length of
# the run: the first hundred bodies of a run and its last hundred are timed,
# and a manifest rewritten after every POST makes the last hundred cost many
# times the first because each one re-serializes a document with fifteen
# hundred entries in it. Journalling makes the two the same within noise, so
# the bound has to hold on a machine running four other jobs in CI -- not to be
# tight.
BOUND = 2.0

HEADERS = [("Content-Type", "application/x-protobuf"), ("Content-Length", "9")]


def _record(recorder: sink.Recorder, first: int, last: int) -> float:
    """Record bodies `first`..`last` and return the seconds it took."""
    started = time.perf_counter()
    for number in range(first, last):
        recorder.record(
            method="POST",
            path="/v1/traces",
            headers=HEADERS,
            head=HEAD,
            body=b"body %04d" % number,
            accepted=True,
        )
    return time.perf_counter() - started


def test_sixteen_hundred_bodies_cost_the_same_each(tmp_path):
    # The A3b row's fifth acceptance test. Writing the run directory is the
    # only expensive thing a capture does per POST, so the measurement is of
    # the recorder itself: one 1,600-body run, with its first hundred bodies
    # and its last hundred timed.
    recorder = sink.Recorder(
        tmp_path / "captures" / "z4" / "run-1" / "raw", now=lambda: STARTED
    )
    first = _record(recorder, 0, SAMPLE) / SAMPLE * 1e6
    _record(recorder, SAMPLE, BODIES - SAMPLE)
    last = _record(recorder, BODIES - SAMPLE, BODIES) / SAMPLE * 1e6
    print(
        f"\n{BODIES} bodies: first {SAMPLE} {first:.0f} us/body, "
        f"last {SAMPLE} {last:.0f} us/body, ratio {last / first:.2f}"
    )
    assert last < BOUND * first, (
        f"per-body cost grew with the run: {first:.0f} us/body over the first "
        f"{SAMPLE} bodies, {last:.0f} us/body over the last {SAMPLE} of 1,600"
    )
    # And the digests are all there, in the journal, waiting for the end of the
    # run: nothing was traded away for the cost.
    assert manifest.body_count(recorder.run) == 0, "nothing is in the manifest yet"
    manifest.finish(recorder.run, ended_at=ENDED)
    assert manifest.body_count(recorder.run) == BODIES
