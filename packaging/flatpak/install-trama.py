#!/usr/bin/env python3
"""Executed inside flatpak-builder, after engine/plugin compilation."""
import hashlib
import json
from pathlib import Path
import shutil
from build_icon import install_icon

root = Path('/app/lib/trama')
def copy(source, destination, mode=0o644):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode)
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

for path in Path('scripts').glob('*.py'):
    copy(path, root/'scripts'/path.name)
for name in ('gpu-screen-recorder', 'gsr-kms-server'):
    copy(Path('/app/bin')/name, root/'engine'/name, 0o755)
copy('rust/target/release/libgsr_overlay_rust.so', root/'build/overlay-rust.so', 0o755)
copy('rust/target/release/scene-check', root/'build/rust-target/release/scene-check', 0o755)
manifest = {
    'gsr_commit': 'f97d1e392816503282d20a0804c3ce3fd2943767',
    'test_hooks': False,
    'gsr_sha256': sha(root/'engine/gpu-screen-recorder'),
    'gsr_helper_sha256': sha(root/'engine/gsr-kms-server'),
    'plugin_sha256': sha(root/'build/overlay-rust.so'),
    'scene_checker_sha256': sha(root/'build/rust-target/release/scene-check'),
    'cargo_lock_sha256': sha('rust/Cargo.lock'),
    'header_sha256': sha('/app/share/trama/plugin.h'),
    'packaging': 'flatpak-local-experimental',
}
(root/'build/overlay-rust.build.json').write_text(json.dumps(manifest, indent=2)+'\n')
launcher = Path('/app/bin/trama')
launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 /app/lib/trama/scripts/trama_tui.py "$@"\n')
launcher.chmod(0o755)
app_id = 'io.github.xoloitzcuintle95.Trama'
desktop = Path('packaging/trama.desktop').read_text().replace('Icon=trama', f'Icon={app_id}')
target = Path('/app/share/applications')/f'{app_id}.desktop'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(desktop)
install_icon('assets/brand/icon.png', Path('/app/share/icons/hicolor/512x512/apps')/f'{app_id}.png')
for path in Path('examples').rglob('*'):
    if path.is_file():
        copy(path, Path('/app/share/trama/examples')/path.relative_to('examples'))
copy('LICENSE', Path('/app/share/licenses/trama/LICENSE'))
copy('packaging/copyright', Path('/app/share/licenses/trama/copyright'))
