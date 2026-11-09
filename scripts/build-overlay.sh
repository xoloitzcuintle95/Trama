#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
mkdir -p build/include/gsr
cp third_party/gpu-screen-recorder/plugin/plugin.h build/include/gsr/plugin.h
# No dependency on a globally installed GSR header. Same API as this checkout.
cc -std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared -Ibuild/include \
    -ffile-prefix-map="$root"=. \
    src/overlay.c src/media.c -o build/overlay.so \
    $(pkg-config --cflags --libs libavformat libavcodec libavutil libswscale gl) -lm
cc -O2 -shared -fPIC -Ibuild/include \
    third_party/gpu-screen-recorder/plugin/examples/hello_triangle/triangle.c \
    -o build/triangle.so $(pkg-config --cflags --libs gl) -lm
python3 - <<'PY'
import hashlib, json
from pathlib import Path
def sha(name): return hashlib.sha256(Path(name).read_bytes()).hexdigest()
sources=['src/overlay.c','src/media.c','src/media.h','third_party/gpu-screen-recorder/plugin/plugin.h']
Path('build/overlay-c.build.json').write_text(json.dumps({
    'plugin_sha256':sha('build/overlay.so'),
    'sources':{name:sha(name) for name in sources},
},indent=2)+'\n')
PY
