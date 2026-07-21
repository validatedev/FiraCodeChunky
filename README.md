# Fira Code Chunky

FiraCode, but every weight is one notch chunkier. Standard weight metadata
(300–700) backed by outlines 50 design-units heavier — apps that select
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
    uv run chunky-build         # dist/: ttf, otf, woff2, variable

## Nerd Font variants

Optional second stage: patch the five static TTFs with the official
[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) `font-patcher`
(`--complete --mono`) into `dist/nerd/`.

    ./scripts/fetch_nerd_fonts.sh          # FontPatcher.zip @ v3.4.0, sha256-pinned
    brew install fontforge                 # macOS; not installable via uv/PyPI
    uv run python scripts/build_nerd.py    # dist/nerd/FiraCodeChunkyNerdFontMono-*.ttf

**Prerequisite:** FontForge with Python bindings (`fontforge` on `PATH`).
On macOS: `brew install fontforge`. On Debian/Ubuntu:
`sudo apt install fontforge python3-fontforge`.

Output family is `FiraCodeChunky Nerd Font Mono`; weight metadata
(300–700) is preserved. Variable font is **not** patched — font-patcher
emits a CRITICAL warning for VFs and the result is not a reliable VF.

Integration checks: `uv run pytest -m integration tests/integration/test_nerd.py`
(skipped when `dist/ttf` or `dist/nerd` is missing).

## Install (macOS)

Copy `dist/ttf/*.ttf` to `~/Library/Fonts`. Coexists with regular Fira Code.
Nerd Font Mono variants: copy `dist/nerd/*.ttf` the same way.
If a stale build seems installed: `sudo atsutil databases -remove` and re-login.

## Credits & License

Derived from [Fira Code](https://github.com/tonsky/FiraCode) by Nikita
Prokopov (tonsky) et al. SIL Open Font License 1.1 — see LICENSE. Not
affiliated with or endorsed by upstream.
