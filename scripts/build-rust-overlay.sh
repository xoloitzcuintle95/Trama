#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
# Refuse a different upstream ABI baseline. Header layout checked separately.
expected=f97d1e392816503282d20a0804c3ce3fd2943767
[[ "$(git -C third_party/gpu-screen-recorder rev-parse HEAD)" == "$expected" ]] || {
    printf 'GSR cambió de commit; revisa la ABI antes de compilar Rust.\n' >&2; exit 1;
}
git -C third_party/gpu-screen-recorder diff --exit-code HEAD -- plugin/plugin.h src/plugins.c src/recorder/recorder.c
export CARGO_TARGET_DIR="$root/build/rust-target"
export CARGO_ENCODED_RUSTFLAGS="$(python3 - <<'PY'
import os, shlex
from pathlib import Path
flags = (os.environ['CARGO_ENCODED_RUSTFLAGS'].split('\x1f')
         if os.environ.get('CARGO_ENCODED_RUSTFLAGS') else shlex.split(os.environ.get('RUSTFLAGS','')))
flags += [f'--remap-path-prefix={Path.home()}=home',
          f'--remap-path-prefix={Path.cwd()}=project']
print('\x1f'.join(flags),end='')
PY
)"
cargo build --manifest-path rust/Cargo.toml --release --offline --locked
cc -std=c11 -Wall -Wextra -Werror tests/rust_abi.c -o build/rust-abi-c
build/rust-abi-c > build/rust-abi-c.txt
"$CARGO_TARGET_DIR/release/abi-layout" > build/rust-abi-rust.txt
diff -u build/rust-abi-c.txt build/rust-abi-rust.txt
# Separate artifact: never overwrite build/overlay.so (C reference).
cp "$CARGO_TARGET_DIR/release/libgsr_overlay_rust.so" build/overlay-rust.so
python3 - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
def sha(name): return hashlib.sha256(Path(name).read_bytes()).hexdigest()
Path('build/overlay-rust.build.json').write_text(json.dumps({
    'gsr_commit': subprocess.check_output(['git','-C','third_party/gpu-screen-recorder','rev-parse','HEAD'],text=True).strip(),
    'gsr_sha256': sha('third_party/gpu-screen-recorder/build/gpu-screen-recorder'),
    'header_sha256': sha('third_party/gpu-screen-recorder/plugin/plugin.h'),
    'plugin_sha256': sha('build/overlay-rust.so'),
    'cargo_lock_sha256': sha('rust/Cargo.lock'),
    'test_hooks': False,
}, indent=2)+'\n')
PY
printf 'ABI C/Rust coincidente. Plugin: %s/build/overlay-rust.so\n' "$root"
