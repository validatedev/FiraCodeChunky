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

    brew install ttfautohint
    uv sync
    ./scripts/fetch.sh          # FiraCode @ 6.2, hash-pinned
    uv run chunky-build         # dist/: ttf, otf, woff2, variable

## Install (macOS)

Copy `dist/ttf/*.ttf` to `~/Library/Fonts`. Coexists with regular Fira Code.
If a stale build seems installed: `sudo atsutil databases -remove` and re-login.

## Credits & License

Derived from [Fira Code](https://github.com/tonsky/FiraCode) by Nikita
Prokopov (tonsky) et al. SIL Open Font License 1.1 — see LICENSE. Not
affiliated with or endorsed by upstream.
