#!/usr/bin/env python3
"""Stage only public inputs and locked Cargo sources for a local Flatpak build."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
MODULES = ('compositor', 'compositor_devices', 'compositor_profile', 'rust_runtime',
           'measure', 'trama_model', 'trama_tui', 'trama_view', 'trama_i18n')

def prepare(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Never copy the working directory wholesale: profiles/builds/.git are private.
    stage = output/'trama-source'
    if stage.exists():
        raise ValueError(f'{stage} already exists; use a new --output folder')
    stage.mkdir()
    paths = [ROOT/f'scripts/{name}.py' for name in MODULES]
    paths += [ROOT/'LICENSE', ROOT/'rust/Cargo.toml', ROOT/'rust/Cargo.lock',
              ROOT/'packaging/copyright', ROOT/'packaging/trama.desktop', ROOT/'assets/brand/icon.png']
    for folder in ('rust/src', 'examples', 'packaging/flatpak'):
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for source in paths:
        target = stage/source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    subprocess.run(['cargo', 'vendor', '--offline', '--locked', '--versioned-dirs',
                    '--manifest-path', str(ROOT/'rust/Cargo.toml'), str(stage/'rust/vendor')], check=True)
    config = stage/'rust/.cargo/config.toml'
    config.parent.mkdir()
    config.write_text('[source.crates-io]\nreplace-with = "vendored-sources"\n'
                      '[source.vendored-sources]\ndirectory = "vendor"\n')
    for name in ('adapt-app-id.py', 'launch-kms.sh'):
        shutil.copyfile(ROOT/'packaging/flatpak'/name, output/name)
    manifest = json.loads((ROOT/'packaging/flatpak/io.github.xoloitzcuintle95.Trama.json').read_text())
    manifest['modules'][-1]['sources'] = [{'type': 'dir', 'path': 'trama-source'}]
    target = output/'io.github.xoloitzcuintle95.Trama.json'
    target.write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Manifest: {target}')
    print('Prepared only; not built, installed or published.')
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/flatpak-input')
    args = parser.parse_args()
    try:
        prepare(args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Preparation failed: {exc}\n')
