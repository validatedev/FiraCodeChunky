import tomllib
from pathlib import Path

from fira_code_chunky import DESIGN_SHIFT, FAMILY_NAME, WEIGHT_CLASSES


def test_constants():
    assert FAMILY_NAME == "Fira Code Chunky"
    assert DESIGN_SHIFT == 50
    assert WEIGHT_CLASSES["Regular"] == 400
    assert list(WEIGHT_CLASSES.values()) == [300, 400, 500, 600, 700]


def test_project_version_matches_upstream_release():
    data = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
    assert data["project"]["version"] == "6.2.0"
