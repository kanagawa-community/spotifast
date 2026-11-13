# Window hook for .github/scripts/capture-windows.sh: Spotifast in demo mode, with
# sample data and no account, shows a playlist in each palette. Album-art tint is
# off, so the page shows only Kanagawa colors.
# Requires: Rust and Cargo, to build upstream/ with the demo feature.
# shellcheck shell=bash
name=Spotifast
size=1240x800

setup() {
  cargo build --quiet --release --features demo --manifest-path "$root/upstream/Cargo.toml"
  bin="$root/upstream/target/release/spotifast"
}

# Custom palettes load in demo mode only from an explicit --demo-data folder.
# After the main window, the classic skin's mini player is captured, at twice its size.
capture() {
  local title data
  title="Kanagawa $(printf %s "${1:0:1}" | tr '[:lower:]' '[:upper:]')${1:1}"
  data="$work/spotifast-$1"
  mkdir -p "$data/config/themes"
  cp "$root/themes/$title.json" "$data/config/themes/"
  printf '{"custom_theme": "%s.json", "accent_from_art": false}\n' "$title" >"$data/config/settings.json"
  start_sway ""
  WAYLAND_DISPLAY=$socket "$bin" --demo --demo-data "$data" --demo-page playlist:pl1 \
    --demo-size "$size" --demo-shot "$2"
  stop_display
  start_sway ""
  WAYLAND_DISPLAY=$socket "$bin" --demo --demo-data "$data" --demo-show "wmp-skin=$root/skins/$title.wsz" \
    --demo-shot "$work/mini-$1.png"
  stop_display
  magick "$work/mini-$1.png" -filter point -resize 200% "$root/assets/screenshots/$1-mini.png"
}
