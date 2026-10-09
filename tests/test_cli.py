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
