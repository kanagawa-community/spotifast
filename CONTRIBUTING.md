# Contributing to Kanagawa for Spotifast

Thanks for helping. This port follows the
[Kanagawa community contributing guide](https://github.com/kanagawa-community/.github/blob/main/.github/CONTRIBUTING.md),
which explains conventional commits, the checks every pull request runs, and how
changes are reviewed. This page covers only what is specific to this port.

## Where to report what

- Problems with the theme in Spotifast, such as wrong colors, poor
  contrast, or a missing variant, belong in this repository's
  [issue tracker](https://github.com/kanagawa-community/spotifast/issues).
- Problems in Spotifast itself belong with its maintainers, not here. Start
  from the [application's page](https://github.com/crmne/spotifast).
- Changes to the colors themselves belong in the
  [shared palette](https://github.com/kanagawa-community/.github/blob/main/docs/PALETTE.md),
  not in this port. Open an issue in the
  [.github repository](https://github.com/kanagawa-community/.github/issues)
  so every port stays in step.

## Colors

Take colors from the shared [palette](https://github.com/kanagawa-community/.github/blob/main/docs/PALETTE.md)
and follow the [style guide](https://github.com/kanagawa-community/.github/blob/main/docs/STYLE-GUIDE.md).
Do not sample colors from screenshots or add new ones. Every change must work in
Wave, Dragon, and Lotus.

To read the colors from a script, use the machine-readable
[palette.json](https://raw.githubusercontent.com/kanagawa-community/.github/main/palette.json).

## Working on this port

`scripts/generate.py` writes `themes/` and `skins/` from the shared palette by
role. Do not edit a generated file. To change a color:

1. Change the role mapping in `scripts/generate.py`.
2. Run `scripts/generate.py`. It needs Python 3 with Pillow, and the
   `upstream/` submodule. Clone with `--recurse-submodules`, or run
   `git submodule update --init`.
3. Commit its output.

The skins are recolors of the Spotifast skins in `upstream/`, a submodule pinned
to one Spotifast commit. `assets/great-wave.png` is the wave in the glass core of
the Windows Media Player skins. It is cut from the `great-wave-crest` wallpaper of
[Kanagawa for KDE](https://github.com/kanagawa-community/kde).

CI runs `scripts/generate.py --check`. It fails if a committed file differs from
the generator output. It compares the files in each skin and their pixels, not
the compressed bytes, because the bytes change with the zlib version.

To try a change, run `./install.sh`, then select the theme or the skin in
Spotifast.

The images in `assets/screenshots/` and `assets/showcase.png` are captured from
Spotifast in demo mode, with sample data and no account. After changing a
color, run this from the repository root and commit the new images:

```sh
bash <(curl -fsSL https://raw.githubusercontent.com/kanagawa-community/.github/main/scripts/capture-windows.sh)
```

It fetches the shared preview scripts from the
[.github repository](https://github.com/kanagawa-community/.github).
`scripts/window.sh` holds the port-specific part. It builds Spotifast from
`upstream/` with the `demo` feature, so it needs Rust and Cargo. See the
[preview standard](https://github.com/kanagawa-community/.github/blob/main/docs/PREVIEWS.md)
for the rest.

## Pull requests

- Keep each pull request to one change, and include a screenshot of each variant
  it affects.
- Update the README when installation or usage changes.
