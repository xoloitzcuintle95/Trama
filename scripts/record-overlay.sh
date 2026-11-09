#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
if [[ $# -lt 1 || $# -gt 2 ]]; then
    printf 'Uso: bash scripts/record-overlay.sh imagen.gif [salida.mp4]\n' >&2
    exit 2
fi
media=$(realpath -- "$1")
output=$(realpath -m -- "${2:-build/overlay-test.mp4}")
gsr=/usr/local/bin/gpu-screen-recorder
[[ -f "$media" ]] || { printf 'No existe la imagen: %s\n' "$media" >&2; exit 1; }
[[ -x "$gsr" ]] || { printf 'Falta instalar GSR en /usr/local (ver README.md).\n' >&2; exit 1; }
[[ -f build/overlay.so ]] || { printf 'Ejecuta bash scripts/build-overlay.sh.\n' >&2; exit 1; }
[[ ! -e "$output" ]] || { printf 'La salida ya existe; elige otro nombre: %s\n' "$output" >&2; exit 1; }
[[ -d "$(dirname -- "$output")" ]] || { printf 'No existe el directorio de salida.\n' >&2; exit 1; }
export GSR_OVERLAY_FILE="$media"
printf 'Grabando monitor por KMS con overlay: %s\nSalida: %s\nEspera al menos 12 segundos y pulsa Ctrl+C para guardar.\n' "$media" "$output"
exec "$gsr" -w screen -f 30 -fm cfr -k h264 \
    -p "$root/build/overlay.so" -o "$output"
