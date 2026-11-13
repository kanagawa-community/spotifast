#!/usr/bin/env bash
# Install the Kanagawa palettes and skins for Spotifast: every variant, or only the ones named.
# ./uninstall.sh takes the same arguments and removes them again.
#
# Usage: ./install.sh [all|wave|dragon|lotus ...]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
case "$(uname -s)" in
  Darwin) config="$HOME/Library/Application Support/me.paolino.spotifast" ;;
  MINGW* | MSYS* | CYGWIN*) config="$APPDATA/paolino/spotifast/config" ;;
  *) config="${XDG_CONFIG_HOME:-$HOME/.config}/spotifast" ;;
esac
# "wave" -> "Kanagawa Wave". macOS ships bash 3.2, which has no ${1^}.
title() { printf "Kanagawa %s%s" "$(printf %s "${1:0:1}" | tr '[:lower:]' '[:upper:]')" "${1:1}"; }
# Print "<file in this repository>\t<folder it goes in>" for one variant.
items() {
  local name
  name="$(title "$1")"
  printf "themes/%s.json\t%s\n" "$name" "$config/themes"
  printf "skins/%s.wsz\t%s\n" "$name" "$config/skins"
  printf "skins/%s Tall.wmz\t%s\n" "$name" "$config/skins"
  printf "skins/%s Wide.wmz\t%s\n" "$name" "$config/skins"
}
# Linux sees new palettes by itself. macOS and Windows need a reload.
after() {
  if [[ "$uninstall" == false && "$(uname -s)" != Linux ]]; then
    echo "Run 'spotifast reload-themes' if Spotifast is open."
  fi
}

uninstall=false
if [[ "${1:-}" == --uninstall ]]; then
  uninstall=true
  shift
fi
selected=""
add() { case " $selected " in *" $1 "*) ;; *) selected="$selected $1" ;; esac; }
for arg in "${@:-all}"; do
  case "$arg" in
    all) add wave; add dragon; add lotus ;;
    wave | dragon | lotus) add "$arg" ;;
    *) echo "usage: $0 [all|wave|dragon|lotus ...]" >&2; exit 2 ;;
  esac
done

for v in $selected; do
  # Remove first, so a reinstall drops files the repository no longer has.
  while IFS=$'\t' read -r src dir; do
    rm -rf "${dir:?}/$(basename "$src")"
    if [[ "$uninstall" == false ]]; then
      mkdir -p "$dir"
      cp -R "$src" "$dir/"
    fi
  done < <(items "$v")
  if [[ "$uninstall" == true ]]; then echo "Removed $(title "$v")"; else echo "Installed $(title "$v")"; fi
done
after
