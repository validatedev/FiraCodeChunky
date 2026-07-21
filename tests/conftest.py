import shutil
from pathlib import Path

import pytest
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument

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
