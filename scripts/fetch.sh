#!/usr/bin/env bash
set -euo pipefail
TAG="6.2"
# For the first run, leave this empty. The script prints the hash. Then paste it here and rerun to verify.
EXPECTED_COMMIT="eee6db993696aba61ff4eef03698e2987d79910c"
DIR="build/upstream"

if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 --branch "$TAG" https://github.com/tonsky/FiraCode "$DIR"
fi
COMMIT=$(git -C "$DIR" rev-parse HEAD)
echo "$COMMIT" > build/upstream_commit.txt
echo "upstream at $COMMIT"
if [ -n "$EXPECTED_COMMIT" ] && [ "$COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "ERROR: expected $EXPECTED_COMMIT" >&2
  exit 1
fi
