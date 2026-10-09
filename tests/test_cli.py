"""The entry point exists and `zoo verify` is honest about what it checked."""

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


def test_verify_refuses_a_capture_it_cannot_yet_re_hash(tmp_path, capsys):
    # Until A3 implements SPEC.md section 5, a capture on disk must make this
    # command fail rather than report an unchecked capture as verified.
    run = tmp_path / "captures" / "z4" / "2026-10-09T00-00-00Z"
    (run / "raw").mkdir(parents=True)
    assert cli.verify(tmp_path / "captures") == 1
    out = capsys.readouterr().out
    assert str(run) in out
    assert "Refusing" in out
