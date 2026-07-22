# Fira Code Chunky

FiraCode, but every weight is one notch chunkier. Standard weight metadata
(300-700) backed by outlines 50 design-units heavier, so apps that select
"Regular 400" get upstream FiraCode's Retina (450) design.

| Style | Metadata | Renders upstream design |
|---|---|---|
| Light | 300 | 350 |
| Regular | 400 | **450 (Retina)** |
| Medium | 500 | 550 |
| SemiBold | 600 | 650 |
| Bold | 700 | 750 (extrapolated) |

## Build

    uv sync
    ./scripts/fetch.sh          # FiraCode @ 6.2, hash-pinned
    uv run chunky-build         # dist/ gets ttf, otf, woff2, variable

## Nerd Font variants

As an optional second stage, patch the five static TTFs with the official
[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) `font-patcher` into
`dist/nerd/`. This produces the three stock variants upstream Nerd Fonts ships
(15 files total, 5 weights × 3 variants).

    ./scripts/fetch_nerd_fonts.sh          # FontPatcher.zip @ v3.4.0, sha256-pinned
    brew install fontforge                 # macOS only. Not installable via uv/PyPI
    uv run python scripts/build_nerd.py    # dist/nerd/FiraCodeChunkyNerdFont*-*.ttf

**Prerequisite.** FontForge with Python bindings (`fontforge` on `PATH`).
On macOS, run `brew install fontforge`. On Debian/Ubuntu, run
`sudo apt install fontforge python3-fontforge`.

| Variant | Family | Filename | Use when |
|---|---|---|---|
| Plain | `FiraCodeChunky Nerd Font` | `FiraCodeChunkyNerdFont-<Style>.ttf` | Most modern terminals/editors, icons overhang the cell (advance stays 1 cell, outline draws wider). |
| Mono | `FiraCodeChunky Nerd Font Mono` | `FiraCodeChunkyNerdFontMono-<Style>.ttf` | Strict terminals that require every glyph, icons included, to occupy exactly one cell. |
| Propo | `FiraCodeChunky Nerd Font Propo` | `FiraCodeChunkyNerdFontPropo-<Style>.ttf` | GUI apps / statuslines where icons should render at their natural proportional width. |

Weight metadata (300-700) is preserved in all three variants. Variable font
is **not** patched. font-patcher emits a CRITICAL warning for VFs and the
result is not a reliable VF.

Integration checks run with `uv run pytest --no-cov -m integration tests/integration/test_nerd.py`.
Skip behavior works as follows. The whole module is skipped only when `dist/nerd` has no
`.ttf` files at all. Individual parametrized (variant, style) rows skip when
that specific `dist/nerd` output is absent. But once any output exists, the
completeness test (checking all 15 files and their PostScript names) hard
**fails** if the full set isn't present. A partial `dist/nerd` counts as a
build defect and fails the test.

## Package a release

After building the stock and Nerd Font outputs, create deterministic release
archives and their checksums:

    uv run python scripts/package_release.py

The archives and `SHA256SUMS` are written to `release/`.

## Install with Homebrew

    brew tap validatedev/tap
    brew install --cask font-fira-code-chunky
    brew install --cask font-fira-code-chunky-nerd-font

## Install (macOS)

Copy `dist/ttf/*.ttf` to `~/Library/Fonts`. Coexists with regular Fira Code.
For Nerd Font variants, copy `dist/nerd/*.ttf` to `~/Library/Fonts` the same way.
If a stale build seems installed, run `sudo atsutil databases -remove` and re-login.

## Credits & License

Derived from [Fira Code](https://github.com/tonsky/FiraCode) by Nikita
Prokopov (tonsky) et al. SIL Open Font License 1.1, see LICENSE. Not
affiliated with or endorsed by upstream.
