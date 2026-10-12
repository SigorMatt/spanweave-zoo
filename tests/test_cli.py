"""The entry point exists and `zoo verify` is honest about what it checked."""

from pathlib import Path

from spanweave_zoo import __version__, cli


def test_help_exits_zero_and_names_the_command(capsys):
    assert cli.main([]) == 0
    assert "zoo" in capsys.readouterr().out


def test_version_is_the_package_version(capsys):
    # `--version` is argparse's own action, which exits.
    try:
        cli.main(["--version"])
    except SystemExit as exit_:
        assert exit_.code == 0
    assert capsys.readouterr().out.strip() == f"zoo {__version__}"


def test_verify_of_an_absent_capture_root_is_clean(tmp_path, capsys):
    # `make verify` runs on a repository with no captures at all, and that is
    # nothing to re-hash rather than an error.
    assert cli.verify(tmp_path / "captures") == 0
    assert "nothing to re-hash" in capsys.readouterr().out


def test_verify_of_an_empty_capture_root_is_clean(tmp_path, capsys):
    (tmp_path / "captures").mkdir()
    assert cli.verify(tmp_path / "captures") == 0
    assert "nothing to re-hash" in capsys.readouterr().out


def test_verify_of_a_named_path_that_is_not_a_capture_refuses(tmp_path, capsys):
    # SPEC.md section 5.6: a path the operator typed is a claim that a capture
    # is there. Nothing there means the command checked nothing, so it exits 2
    # naming the path -- a zero would be the reassuring pass over a capture
    # nobody checked that this command exists to prevent (CLAUDE.md).
    absent = tmp_path / "captures" / "z4" / "typo"
    assert cli.main(["verify", str(absent)]) == 2
    assert str(absent) in capsys.readouterr().err


def test_verify_of_a_named_file_refuses(tmp_path, capsys):
    # A path that is not a directory at all: the same refusal, not a crash and
    # not "nothing to re-hash".
    not_a_directory = tmp_path / "MANIFEST.json"
    not_a_directory.write_text("{}", encoding="utf-8")
    assert cli.main(["verify", str(not_a_directory)]) == 2
    assert str(not_a_directory) in capsys.readouterr().err


def test_verify_of_a_named_directory_holding_no_run_refuses(tmp_path, capsys):
    # The directory exists and holds files, but no `MANIFEST.json`, no `raw/`
    # and no `<project>/<run-id>` under it. Being a directory is not being a
    # capture.
    named = tmp_path / "somewhere"
    named.mkdir()
    (named / "notes.txt").write_text("not a capture\n", encoding="utf-8")
    assert cli.main(["verify", str(named)]) == 2
    assert str(named) in capsys.readouterr().err


def test_verify_with_no_path_tolerates_a_repository_with_no_captures(
    tmp_path, monkeypatch, capsys
):
    # The default root is the one path that may legitimately hold nothing: a
    # repository that has recorded no captures yet is nothing to re-hash, and
    # `make verify` runs there (SPEC.md section 5.6).
    monkeypatch.chdir(tmp_path)
    assert cli.main(["verify"]) == 0
    assert "nothing to re-hash" in capsys.readouterr().out


def test_verify_refuses_a_capture_with_no_manifest(tmp_path, capsys):
    # A1 replaced A0's blanket refusal with the real re-hash (SPEC.md section
    # 3.5), but a run with no readable MANIFEST.json has nothing to re-hash
    # against -- and must still fail rather than report it verified.
    run = tmp_path / "captures" / "z4" / "2026-10-09T00-00-00Z"
    (run / "raw").mkdir(parents=True)
    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert str(run) in out
    assert "no readable MANIFEST.json" in out


def test_the_only_clock_in_the_package_is_the_sinks_now_seam(tmp_path):
    # SPEC.md section 3.6: the sink takes `now` as an argument, and `cli.py` is
    # the one place the real clock enters the package. Asserted here rather
    # than trusted: a second clock read elsewhere makes a capture's timestamp
    # something no test chose.
    import ast

    from spanweave_zoo import cli as cli_module

    reads_the_world = {
        "now",
        "utcnow",
        "time",
        "monotonic",
        "perf_counter",
        "sleep",
        "random",
        "uuid4",
        "urandom",
    }
    package = Path(cli_module.__file__).parent
    offenders = []
    for module in sorted(package.rglob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in reads_the_world:
                offenders.append(f"{module.name}:{node.lineno} .{node.attr}")
    # `cli.py` holds the seam's one implementation (`_system_clock`); any other
    # module reading the world is the failure this test exists to catch.
    assert [o for o in offenders if not o.startswith("cli.py")] == [], offenders
    assert offenders, "the clock seam's implementation went missing from cli.py"
