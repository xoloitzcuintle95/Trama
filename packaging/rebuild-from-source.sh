#!/usr/bin/env bash
# Run from the extracted accompanying sources. No sudo/install/network.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
meson setup third_party/gpu-screen-recorder/build third_party/gpu-screen-recorder \
  --buildtype=release --prefix=/usr/local -Dffmpeg_static=false -Dportal=false \
  -Dapp_audio=false -Dplugin_examples=false -Dsystemd=false \
  -Dnvidia_suspend_fix=false -Dcapabilities=false
meson compile -C third_party/gpu-screen-recorder/build
export CARGO_TARGET_DIR="$root/build/rust-target"
export CARGO_ENCODED_RUSTFLAGS="--remap-path-prefix=$root=project"
cargo build --manifest-path rust/Cargo.toml --offline --locked --release
mkdir -p build
cp "$CARGO_TARGET_DIR/release/libgsr_overlay_rust.so" build/overlay-rust.so
python3 - <<'PY'
import hashlib,json
from pathlib import Path
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
Path('build/overlay-rust.build.json').write_text(json.dumps({
 'gsr_commit':'f97d1e392816503282d20a0804c3ce3fd2943767',
 'gsr_sha256':sha('third_party/gpu-screen-recorder/build/gpu-screen-recorder'),
 'header_sha256':sha('third_party/gpu-screen-recorder/plugin/plugin.h'),
 'plugin_sha256':sha('build/overlay-rust.so'),
 'cargo_lock_sha256':sha('rust/Cargo.lock'), 'test_hooks':False},indent=2)+'\n')
PY
printf '%s\n' 'Build local listo. No se instaló ningún archivo del sistema.'
