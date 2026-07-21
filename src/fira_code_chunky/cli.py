"""CLI shell: parse args, call one function, return exit code."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from fira_code_chunky.pipeline import run_build
from fira_code_chunky.runner import SubprocessRunner


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chunky-build")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    return run_build(args.root, SubprocessRunner())


if __name__ == "__main__":
    raise SystemExit(main())
