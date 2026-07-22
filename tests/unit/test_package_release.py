import hashlib
import importlib.util
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

_spec = importlib.util.spec_from_file_location(
    "package_release", SCRIPTS / "package_release.py"
)
assert _spec is not None and _spec.loader is not None
package_release = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = package_release
_spec.loader.exec_module(package_release)

STYLES = ("Light", "Regular", "Medium", "SemiBold", "Bold")
WEIGHTS = dict(zip(STYLES, (300, 400, 500, 600, 700), strict=True))
STOCK_MEMBERS = {
    "LICENSE",
    "README.txt",
    *(f"ttf/FiraCodeChunky-{style}.ttf" for style in STYLES),
    *(f"otf/FiraCodeChunky-{style}.otf" for style in STYLES),
    *(f"woff2/FiraCodeChunky-{style}.woff2" for style in STYLES),
    "woff2/FiraCodeChunky-VF.woff2",
    "variable_ttf/FiraCodeChunky-VF.ttf",
}
NERD_MEMBERS = {
    "LICENSE",
    "README.txt",
    *(
        f"FiraCodeChunkyNerdFont{variant}-{style}.ttf"
        for variant in ("", "Mono", "Propo")
        for style in STYLES
    ),
}


def _populate_dist(dist_dir: Path) -> None:
    for style in STYLES:
        for directory, suffix in (("ttf", ".ttf"), ("otf", ".otf")):
            path = dist_dir / directory / f"FiraCodeChunky-{style}{suffix}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{directory}-{style}".encode())

        woff2 = dist_dir / "woff2" / f"FiraCodeChunky-{style}.woff2"
        woff2.parent.mkdir(parents=True, exist_ok=True)
        woff2.write_bytes(f"woff2-{style}".encode())

        for variant in ("", "Mono", "Propo"):
            nerd = dist_dir / "nerd" / f"FiraCodeChunkyNerdFont{variant}-{style}.ttf"
            nerd.parent.mkdir(parents=True, exist_ok=True)
            nerd.write_bytes(f"nerd-{variant}-{style}".encode())

    variable_ttf = dist_dir / "variable" / "FiraCodeChunky-VF.ttf"
    variable_ttf.parent.mkdir(parents=True, exist_ok=True)
    variable_ttf.write_bytes(b"variable-ttf")
    (dist_dir / "woff2" / "FiraCodeChunky-VF.woff2").write_bytes(b"variable-woff2")
    (dist_dir.parent / "LICENSE").write_text("SIL Open Font License 1.1\n")


@pytest.fixture
def fake_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dist_dir = tmp_path / "dist"
    _populate_dist(dist_dir)
    monkeypatch.setattr(package_release, "validate_font", lambda *args, **kwargs: None)
    return dist_dir


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_package_release_writes_exact_manifests_and_zip_metadata(
    fake_dist: Path, tmp_path: Path
) -> None:
    stock, nerd, checksums = package_release.package_release(
        fake_dist, tmp_path / "release", "6.2"
    )

    assert (stock.name, nerd.name, checksums.name) == (
        "Fira_Code_Chunky_v6.2.zip",
        "Fira_Code_Chunky_Nerd_Fonts_v6.2.zip",
        "SHA256SUMS",
    )
    for archive, expected in ((stock, STOCK_MEMBERS), (nerd, NERD_MEMBERS)):
        with zipfile.ZipFile(archive) as zipped:
            assert zipped.namelist() == sorted(expected)
            for info in zipped.infolist():
                assert info.date_time == (1980, 1, 1, 0, 0, 0)
                assert info.create_system == 3
                assert info.external_attr == 0o100644 << 16
                assert info.compress_type == zipfile.ZIP_DEFLATED


def test_package_release_is_byte_deterministic_and_checksums_match(
    fake_dist: Path, tmp_path: Path
) -> None:
    first = package_release.package_release(fake_dist, tmp_path / "first", "6.2")
    second = package_release.package_release(fake_dist, tmp_path / "second", "6.2")

    assert [_sha256(path) for path in first[:2]] == [
        _sha256(path) for path in second[:2]
    ]
    assert first[2].read_text().splitlines() == [
        f"{_sha256(first[0])}  {first[0].name}",
        f"{_sha256(first[1])}  {first[1].name}",
    ]


def test_package_release_rejects_a_missing_font(
    fake_dist: Path, tmp_path: Path
) -> None:
    (fake_dist / "ttf" / "FiraCodeChunky-Light.ttf").unlink()

    with pytest.raises(ValueError, match=r"missing=\['FiraCodeChunky-Light.ttf'\]"):
        package_release.package_release(fake_dist, tmp_path / "release", "6.2")


def test_package_release_rejects_an_unexpected_font(
    fake_dist: Path, tmp_path: Path
) -> None:
    (fake_dist / "ttf" / "FiraCodeChunky-Retina.ttf").write_bytes(b"unexpected")

    with pytest.raises(ValueError, match=r"unexpected=\['FiraCodeChunky-Retina.ttf'\]"):
        package_release.package_release(fake_dist, tmp_path / "release", "6.2")


def test_package_release_submits_every_font_for_metadata_validation(
    fake_dist: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validated = []
    monkeypatch.setattr(
        package_release,
        "validate_font",
        lambda path, **kwargs: validated.append(path.relative_to(fake_dist).as_posix()),
    )

    package_release.package_release(fake_dist, tmp_path / "release", "6.2")

    expected_stock = {
        *(f"ttf/FiraCodeChunky-{style}.ttf" for style in STYLES),
        *(f"otf/FiraCodeChunky-{style}.otf" for style in STYLES),
        *(f"woff2/FiraCodeChunky-{style}.woff2" for style in STYLES),
        "woff2/FiraCodeChunky-VF.woff2",
        "variable/FiraCodeChunky-VF.ttf",
    }
    expected_nerd = {
        f"nerd/FiraCodeChunkyNerdFont{variant}-{style}.ttf"
        for variant in ("", "Mono", "Propo")
        for style in STYLES
    }
    assert len(validated) == 32
    assert set(validated) == expected_stock | expected_nerd


def _write_test_font(
    source: Path,
    destination: Path,
    *,
    family: str,
    style: str,
    weight: int,
    version: str,
) -> None:
    shutil.copy(source, destination)
    font = TTFont(destination)
    names = font["name"]
    for name_id in (1, 2, 5, 16, 17):
        names.removeNames(nameID=name_id)
    for name_id, value in (
        (1, family),
        (2, style),
        (5, version),
        (16, family),
        (17, style),
    ):
        names.setName(value, name_id, 3, 1, 0x409)
    cast(Any, font["OS/2"]).usWeightClass = weight
    font.save(destination)
    font.close()


def test_validate_font_accepts_exact_stock_and_nerd_metadata(
    micro_ttf_path: Path, tmp_path: Path
) -> None:
    stock = tmp_path / "FiraCodeChunky-Regular.ttf"
    nerd = tmp_path / "FiraCodeChunkyNerdFontMono-SemiBold.ttf"
    _write_test_font(
        micro_ttf_path,
        stock,
        family="Fira Code Chunky",
        style="Regular",
        weight=400,
        version="Version 6.002",
    )
    _write_test_font(
        micro_ttf_path,
        nerd,
        family="FiraCodeChunky Nerd Font Mono",
        style="SemiBold",
        weight=600,
        version="Version 6.002;Nerd Fonts 3.4.0",
    )

    package_release.validate_font(
        stock,
        family="Fira Code Chunky",
        style="Regular",
        weight=400,
        versions=("Version 6.002",),
    )
    package_release.validate_font(
        nerd,
        family="FiraCodeChunky Nerd Font Mono",
        style="SemiBold",
        weight=600,
        versions=("Version 6.002", "Nerd Fonts 3.4.0"),
    )


@pytest.mark.parametrize(
    ("family", "style", "weight", "version", "message"),
    [
        ("Wrong Family", "Regular", 400, "Version 6.002", "family"),
        ("Fira Code Chunky", "Bold", 400, "Version 6.002", "style"),
        ("Fira Code Chunky", "Regular", 450, "Version 6.002", "weight"),
        ("Fira Code Chunky", "Regular", 400, "Version 6.001", "version"),
    ],
)
def test_validate_font_rejects_incorrect_metadata(
    micro_ttf_path: Path,
    tmp_path: Path,
    family: str,
    style: str,
    weight: int,
    version: str,
    message: str,
) -> None:
    path = tmp_path / "FiraCodeChunky-Regular.ttf"
    _write_test_font(
        micro_ttf_path,
        path,
        family=family,
        style=style,
        weight=weight,
        version=version,
    )

    with pytest.raises(ValueError, match=message):
        package_release.validate_font(
            path,
            family="Fira Code Chunky",
            style="Regular",
            weight=400,
            versions=("Version 6.002",),
        )


@pytest.mark.parametrize(
    ("version", "required_versions"),
    [
        ("Version 6.0021", ("Version 6.002",)),
        (
            "Version 6.0021;Nerd Fonts 3.4.0",
            ("Version 6.002", "Nerd Fonts 3.4.0"),
        ),
        (
            "Version 6.002;Nerd Fonts 3.4.01",
            ("Version 6.002", "Nerd Fonts 3.4.0"),
        ),
    ],
)
def test_validate_font_rejects_version_substring_matches(
    micro_ttf_path: Path,
    tmp_path: Path,
    version: str,
    required_versions: tuple[str, ...],
) -> None:
    path = tmp_path / "FiraCodeChunky-Regular.ttf"
    _write_test_font(
        micro_ttf_path,
        path,
        family="Fira Code Chunky",
        style="Regular",
        weight=400,
        version=version,
    )

    with pytest.raises(ValueError, match="version"):
        package_release.validate_font(
            path,
            family="Fira Code Chunky",
            style="Regular",
            weight=400,
            versions=required_versions,
        )


def test_read_release_version_converts_project_semver(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nversion = "6.2.0"\n')

    assert package_release.read_release_version(project) == "6.2"


def test_main_rejects_cli_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "6.2.0"\n')
    monkeypatch.setattr(package_release, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["package_release.py", "6.1"])

    assert package_release.main() == 2
