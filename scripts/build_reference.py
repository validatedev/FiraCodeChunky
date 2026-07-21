#!/usr/bin/env python3
"""Build the upstream-faithful reference VF used by fidelity integration tests.

Upstream tag 6.2 (``build/upstream``, see ``scripts/fetch.sh``) does not ship
a compiled variable font under ``distr/``, so ``tests/integration/test_fidelity.py``
compares against a locally-built reference. This script reproduces it:

1. Convert ``build/upstream/FiraCode.glyphs`` to master UFOs + a designspace
   via glyphs2ufo (the same ``commands.glyphs2ufo_command`` the real
   ``chunky-build`` pipeline uses in ``pipeline.convert_upstream``) -- into
   ``build/reference/masters``, deliberately separate from
   ``build/master_ufo`` (which the real pipeline patches in place) so the
   reference stays byte-for-byte upstream, un-"chunky"-fied.
2. Apply ``features.sanitize_features`` to each master's ``features.fea`` on
   disk -- same fix as ``pipeline.prepare_designspace`` applies in memory
   before compiling, but written back to disk here because fontmake is
   invoked as a subprocess (see below) and reads the UFO from disk rather
   than an in-memory ufoLib2 object.
3. Run ``fontmake -o variable`` on that designspace to produce
   ``build/reference/FiraCode-VF.ttf``.

Usage:
    uv run python scripts/build_reference.py

This intentionally shells out with ``subprocess`` directly (as
``scripts/proof.py`` does) rather than going through
``fira_code_chunky.runner.Runner``: ``scripts/`` sits outside the
Runner-protocol core (which exists so ``pipeline.py`` can be tested with a
fake runner) -- one-off scripts have no test double to satisfy and running
real subprocesses directly is the simpler, honest choice here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fira_code_chunky import commands, features

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_GLYPHS = ROOT / "build/upstream/FiraCode.glyphs"
MASTER_DIR = ROOT / "build/reference/masters"
DESIGNSPACE = MASTER_DIR / "FiraCode.designspace"
OUT_DIR = ROOT / "build/reference"
VF_OUT = OUT_DIR / "FiraCode-VF.ttf"


def convert_masters() -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        commands.glyphs2ufo_command(UPSTREAM_GLYPHS, MASTER_DIR, DESIGNSPACE),
        check=True,
    )


def sanitize_masters() -> None:
    for ufo in sorted(MASTER_DIR.glob("*.ufo")):
        fea_path = ufo / "features.fea"
        if not fea_path.exists():
            continue
        text = fea_path.read_text()
        fea_path.write_text(features.sanitize_features(text))


def compile_variable() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        commands.fontmake_variable_command(DESIGNSPACE, OUT_DIR),
        check=True,
    )
    # fontmake names the VF after the designspace's family name; normalize.
    produced = [path for path in OUT_DIR.glob("*.ttf") if path != VF_OUT]
    if produced:
        produced[0].replace(VF_OUT)


def main() -> int:
    if not UPSTREAM_GLYPHS.exists():
        print(f"missing {UPSTREAM_GLYPHS}; run scripts/fetch.sh first", file=sys.stderr)
        return 1
    convert_masters()
    sanitize_masters()
    compile_variable()
    if not VF_OUT.exists():
        print(f"fontmake did not produce {VF_OUT}", file=sys.stderr)
        return 1
    print(f"wrote {VF_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
