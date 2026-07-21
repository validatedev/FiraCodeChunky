import contextlib
import io
import logging
import shutil
import subprocess as _subprocess
from pathlib import Path

import pytest
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument

from fira_code_chunky.runner import RunnerError

FIXTURES = Path(__file__).parent / "fixtures" / "micro"


def _compile_micro(tmp_path_factory, output):
    from fontmake.font_project import FontProject

    out = tmp_path_factory.mktemp(f"compiled-{output}")
    previous_logging_level = logging.root.manager.disable
    try:
        logging.disable(logging.CRITICAL)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            FontProject().run_from_ufos(
                [str(FIXTURES / "MicroLight.ufo")],
                output=(output,),
                output_dir=str(out),
            )
    finally:
        logging.disable(previous_logging_level)
    return next(out.glob(f"*.{output}"))


@pytest.fixture(scope="session")
def micro_ttf_path(tmp_path_factory):
    return _compile_micro(tmp_path_factory, "ttf")


@pytest.fixture
def micro_ttf(micro_ttf_path, tmp_path):
    from fontTools.ttLib import TTFont

    path = tmp_path / micro_ttf_path.name
    shutil.copy(micro_ttf_path, path)
    return TTFont(path)


@pytest.fixture(scope="session")
def micro_otf_path(tmp_path_factory):
    return _compile_micro(tmp_path_factory, "otf")


@pytest.fixture
def micro_otf(micro_otf_path, tmp_path):
    from fontTools.ttLib import TTFont

    path = tmp_path / micro_otf_path.name
    shutil.copy(micro_otf_path, path)
    return TTFont(path)


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
