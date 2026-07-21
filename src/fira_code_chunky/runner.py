"""Subprocess execution behind an injectable protocol."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class RunnerError(RuntimeError):
    """A subprocess exited non-zero."""


class Runner(Protocol):
    def run(
        self, argv: Sequence[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(
        self, argv: Sequence[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(argv), cwd=cwd, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            raise RunnerError(f"{argv!r} failed ({e.returncode}): {e.stderr}") from e
