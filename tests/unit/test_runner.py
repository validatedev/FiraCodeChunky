import subprocess

import pytest

from fira_code_chunky.runner import RunnerError, SubprocessRunner


def test_subprocess_runner_success():
    result = SubprocessRunner().run(["/usr/bin/true"])
    assert result.returncode == 0


def test_subprocess_runner_failure_wraps_error():
    with pytest.raises(RunnerError) as exc:
        SubprocessRunner().run(["/usr/bin/false"])
    assert "/usr/bin/false" in str(exc.value)


def test_subprocess_runner_captures_output():
    result = SubprocessRunner().run(["/bin/echo", "hi"])
    assert result.stdout.strip() == "hi"


def test_fake_runner(fake_runner):
    fake_runner.run(["fontmake", "-u", "x.ufo"])
    assert fake_runner.calls == [["fontmake", "-u", "x.ufo"]]
    fake_runner.fail_on.add("ttfautohint")
    with pytest.raises(RunnerError):
        fake_runner.run(["ttfautohint", "a", "b"])


def test_completed_process_type():
    assert isinstance(
        SubprocessRunner().run(["/usr/bin/true"]), subprocess.CompletedProcess
    )
