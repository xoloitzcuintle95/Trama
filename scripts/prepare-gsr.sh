#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
src="$root/third_party/gpu-screen-recorder"
mkdir -p "$root/third_party"
if [[ ! -e "$src" ]]; then
    git clone https://repo.dec05eba.com/gpu-screen-recorder "$src"
fi
git -C "$src" rev-parse HEAD
printf '%s\n' 'Revisa README.md, meson.build, meson_options.txt e install.sh antes de instalar.'
command -v meson >/dev/null || { printf '%s\n' 'Falta meson (ver docs/estado.md).' >&2; exit 1; }
# Compilación local; sin portal ni descargas de FFmpeg estático.
meson setup "$src/build" "$src" --buildtype=release --prefix=/usr/local \
    -Dffmpeg_static=false -Dportal=false -Dapp_audio=false \
    -Dplugin_examples=false -Dsystemd=false -Dnvidia_suspend_fix=false
meson compile -C "$src/build"
