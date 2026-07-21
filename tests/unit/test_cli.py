from pathlib import Path

from fira_code_chunky import cli
from fira_code_chunky.runner import SubprocessRunner


def test_main_returns_int(tmp_path, monkeypatch):
    seen = []

    def fake_run_build(root, runner):
        seen.append((root, runner))
        return 0

    monkeypatch.setattr(cli, "run_build", fake_run_build)

    assert cli.main(["--root", str(tmp_path)]) == 0
    assert seen[0][0] == tmp_path
    assert isinstance(seen[0][1], SubprocessRunner)


def test_main_default_root(monkeypatch):
    seen = {}

    def fake_run_build(root, runner):
        seen["root"] = root
        return 0

    monkeypatch.setattr(cli, "run_build", fake_run_build)

    assert cli.main([]) == 0
    assert seen["root"] == Path.cwd()
