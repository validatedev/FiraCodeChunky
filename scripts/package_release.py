#!/usr/bin/env python3
"""Validate built fonts and package deterministic release archives."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
import zipfile
from pathlib import Path
from typing import Any, cast

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
STYLES = ("Light", "Regular", "Medium", "SemiBold", "Bold")
WEIGHTS = dict(zip(STYLES, (300, 400, 500, 600, 700), strict=True))
STOCK_FAMILY = "Fira Code Chunky"
STOCK_VERSION = "Version 6.002"
NERD_VERSION = "Nerd Fonts 3.4.0"

STOCK_RELATIVE_PATHS = (
    *(f"ttf/FiraCodeChunky-{style}.ttf" for style in STYLES),
    *(f"otf/FiraCodeChunky-{style}.otf" for style in STYLES),
    *(f"woff2/FiraCodeChunky-{style}.woff2" for style in STYLES),
    "woff2/FiraCodeChunky-VF.woff2",
    "variable/FiraCodeChunky-VF.ttf",
)
NERD_FILENAMES = tuple(
    f"FiraCodeChunkyNerdFont{variant}-{style}.ttf"
    for variant in ("", "Mono", "Propo")
    for style in STYLES
)
NERD_FAMILIES = {
    "": "FiraCodeChunky Nerd Font",
    "Mono": "FiraCodeChunky Nerd Font Mono",
    "Propo": "FiraCodeChunky Nerd Font Propo",
}


def require_exact_files(directory: Path, expected: set[str], suffix: str) -> None:
    actual = {path.name for path in directory.glob(f"*{suffix}")}
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(f"{directory}: missing={missing}, unexpected={unexpected}")


def _name_records(font: TTFont, name_id: int) -> list[str]:
    values = []
    for record in cast(Any, font["name"]).names:
        if record.nameID != name_id:
            continue
        try:
            values.append(record.toUnicode())
        except UnicodeDecodeError:
            continue
    return values


def _version_record_matches(record: str, versions: tuple[str, ...]) -> bool:
    if versions == (STOCK_VERSION,):
        return record == STOCK_VERSION
    components = {component.strip() for component in record.split(";")}
    return all(version in components for version in versions)


def validate_font(
    path: Path,
    *,
    family: str,
    style: str | None,
    weight: int | None,
    versions: tuple[str, ...],
) -> None:
    font = TTFont(path, lazy=True)
    try:
        names = cast(Any, font["name"])
        actual_family = names.getBestFamilyName()
        if actual_family != family:
            raise ValueError(f"{path}: family={actual_family!r}, expected {family!r}")

        if style is not None:
            actual_style = names.getBestSubFamilyName()
            if actual_style != style:
                raise ValueError(f"{path}: style={actual_style!r}, expected {style!r}")

        if weight is not None:
            actual_weight = cast(Any, font["OS/2"]).usWeightClass
            if actual_weight != weight:
                raise ValueError(f"{path}: weight={actual_weight}, expected {weight}")

        version_records = _name_records(font, 5)
        if not version_records or not all(
            _version_record_matches(record, versions) for record in version_records
        ):
            raise ValueError(
                f"{path}: version records={version_records!r}, expected {versions!r}"
            )
    finally:
        font.close()


def _validate_manifest(dist_dir: Path) -> None:
    for directory, suffix in (
        ("ttf", ".ttf"),
        ("otf", ".otf"),
        ("woff2", ".woff2"),
        ("variable", ".ttf"),
    ):
        expected = {
            Path(relative_path).name
            for relative_path in STOCK_RELATIVE_PATHS
            if Path(relative_path).parts[0] == directory
        }
        require_exact_files(dist_dir / directory, expected, suffix)
    require_exact_files(dist_dir / "nerd", set(NERD_FILENAMES), ".ttf")


def _validate_metadata(dist_dir: Path) -> None:
    for relative_path in STOCK_RELATIVE_PATHS:
        path = dist_dir / relative_path
        is_variable = path.stem == "FiraCodeChunky-VF"
        style = None if is_variable else path.stem.removeprefix("FiraCodeChunky-")
        validate_font(
            path,
            family=STOCK_FAMILY,
            style=style,
            weight=None if style is None else WEIGHTS[style],
            versions=(STOCK_VERSION,),
        )

    for variant, family in NERD_FAMILIES.items():
        for style in STYLES:
            validate_font(
                dist_dir / "nerd" / f"FiraCodeChunkyNerdFont{variant}-{style}.ttf",
                family=family,
                style=style,
                weight=WEIGHTS[style],
                versions=(STOCK_VERSION, NERD_VERSION),
            )


def _readme(version: str, nerd: bool) -> bytes:
    title = "Fira Code Chunky Nerd Fonts" if nerd else "Fira Code Chunky"
    return (
        f"{title} v{version}\n\n"
        "See LICENSE for the SIL Open Font License 1.1.\n"
        "Install the font files using your operating system's font manager.\n"
    ).encode()


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for archive_name in sorted(members):
            info = zipfile.ZipInfo(archive_name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, members[archive_name], compresslevel=9)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_release(
    dist_dir: Path, output_dir: Path, version: str
) -> tuple[Path, Path, Path]:
    _validate_manifest(dist_dir)
    _validate_metadata(dist_dir)

    license_path = dist_dir.parent / "LICENSE"
    if not license_path.is_file():
        raise ValueError(f"missing {license_path}")
    license_bytes = license_path.read_bytes()

    stock_members = {
        "LICENSE": license_bytes,
        "README.txt": _readme(version, nerd=False),
    }
    for relative_path in STOCK_RELATIVE_PATHS:
        archive_name = relative_path
        if relative_path == "variable/FiraCodeChunky-VF.ttf":
            archive_name = "variable_ttf/FiraCodeChunky-VF.ttf"
        stock_members[archive_name] = (dist_dir / relative_path).read_bytes()

    nerd_members = {
        "LICENSE": license_bytes,
        "README.txt": _readme(version, nerd=True),
        **{
            filename: (dist_dir / "nerd" / filename).read_bytes()
            for filename in NERD_FILENAMES
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    stock_path = output_dir / f"Fira_Code_Chunky_v{version}.zip"
    nerd_path = output_dir / f"Fira_Code_Chunky_Nerd_Fonts_v{version}.zip"
    checksums_path = output_dir / "SHA256SUMS"
    _write_zip(stock_path, stock_members)
    _write_zip(nerd_path, nerd_members)
    checksums_path.write_text(
        f"{_sha256(stock_path)}  {stock_path.name}\n"
        f"{_sha256(nerd_path)}  {nerd_path.name}\n"
    )
    return stock_path, nerd_path, checksums_path


def read_release_version(project_file: Path) -> str:
    project = tomllib.loads(project_file.read_text())["project"]
    version = project["version"]
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts) or parts[2] != "0":
        raise ValueError(f"project version must be X.Y.0, got {version!r}")
    return f"{parts[0]}.{parts[1]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version", nargs="?", help="optional release version, for example 6.2"
    )
    args = parser.parse_args()

    try:
        project_version = read_release_version(ROOT / "pyproject.toml")
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    if args.version is not None and args.version != project_version:
        print(
            f"version mismatch: CLI={args.version!r}, project={project_version!r}",
            file=sys.stderr,
        )
        return 2

    try:
        package_release(ROOT / "dist", ROOT / "release", project_version)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
