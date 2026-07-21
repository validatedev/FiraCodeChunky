import shutil
import subprocess as _subprocess
from pathlib import Path

import pytest
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument

from fira_code_chunky.runner import RunnerError

FIXTURES = Path(__file__).parent / "fixtures" / "micro"


@pytest.fixture
def micro_dir(tmp_path):
    dest = tmp_path / "micro"
    shutil.copytree(FIXTURES, dest)
    return dest


@pytest.fixture
def micro_ds(micro_dir):
    ds = DesignSpaceDocument.fromfile(micro_dir / "Micro.designspace")
    ds.loadSourceFonts(ufoLib2.Font.open)
    return ds


@pytest.fixture
def micro_masters(micro_dir):
    return (
        ufoLib2.Font.open(micro_dir / "MicroLight.ufo"),
        ufoLib2.Font.open(micro_dir / "MicroBold.ufo"),
    )


class FakeRunner:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.fail_on: set[str] = set()

    def run(self, argv, cwd=None):
        argv = list(argv)
        self.calls.append(argv)
        if argv[0] in self.fail_on:
            raise RunnerError(f"{argv!r} failed (1): fake failure")
        return _subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


@pytest.fixture
def fake_runner():
    return FakeRunner()
