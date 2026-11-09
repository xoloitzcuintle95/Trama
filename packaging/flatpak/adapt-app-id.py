#!/usr/bin/env python3
"""Packaging-only adaptation of upstream's fixed system Flatpak app ID."""
from pathlib import Path
import sys

OLD = 'com.dec05eba.gpu_screen_recorder'
NEW = 'io.github.xoloitzcuintle95.Trama'

def adapt(root):
    changed = []
    for path in sorted(Path(root).rglob('*')):
        if path.is_file() and path.suffix in ('.c', '.h', '.sh'):
            text = path.read_text()
            if OLD in text:
                text = text.replace(OLD, NEW)
                path.write_text(text)
                changed.append(str(path.relative_to(root)))
    return changed

if __name__ == '__main__':
    changed = adapt(Path('.'))
    if sys.argv[1:] == ['--require-match'] and not changed:
        raise SystemExit('Upstream app-ID path changed; review the packaging adaptation')
    print('Flatpak app-ID substitutions:', ', '.join(changed) or 'none needed')
