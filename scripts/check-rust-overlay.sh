#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
bash scripts/check-overlay.sh
bash scripts/build-rust-overlay.sh
CARGO_TARGET_DIR="$root/build/rust-target" cargo test --manifest-path rust/Cargo.toml --release --offline --locked
python3 tests/rust_gl_host.py
python3 tests/check_rust_gif.py
python3 tests/test_element_cli.py
python3 tests/test_compositor.py
# Test-only artifact lives separately; cannot overwrite production release.
CARGO_TARGET_DIR="$root/build/rust-test-target" cargo build --manifest-path rust/Cargo.toml \
    --release --offline --locked --features test-hooks --lib
python3 tests/rust_gl_host.py --test-hooks --plugin build/rust-test-target/release/libgsr_overlay_rust.so
python3 scripts/check-source.py
