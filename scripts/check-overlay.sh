#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
bash scripts/build-overlay.sh
cc -std=c11 -O2 -Wall -Wextra -Werror -ffile-prefix-map="$root"=. tests/media_dump.c src/media.c \
    -o build/media-dump $(pkg-config --cflags --libs libavformat libavcodec libavutil libswscale) -lm
python3 tests/check_media.py
python3 tests/check_gl.py
