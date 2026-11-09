#!/usr/bin/env python3
"""Review public source inputs for personal paths/devices and generated media."""
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
TEXT_SUFFIXES={'.md','.py','.rs','.toml','.lock','.sh','.c','.h','.txt'}
GENERATED_SUFFIXES={'.mp4','.mkv','.webm','.mov','.wav','.flac','.log','.jsonl','.so','.o','.a','.zip','.gz'}


def main():
    problems=[]
    files=[ROOT/name for name in ('README.md','AGENTS.md','.gitignore','trama','LICENSE')]
    for folder in ('scripts','tests','docs','examples','assets','packaging','src','rust'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                     and not any(part in ('target','__pycache__') for part in p.relative_to(ROOT/folder).parts))
    home=str(Path.home()).encode()
    for file in files:
        relative=file.relative_to(ROOT)
        if file.suffix in GENERATED_SUFFIXES:
            problems.append(f'{relative}: artefacto generado dentro de las fuentes')
        if file.suffix in TEXT_SUFFIXES or file.name in ('trama','.gitignore'):
            data=file.read_bytes()
            if len(home)>1 and home in data:
                problems.append(f'{relative}: contiene una ruta personal absoluta')
            if re.search(rb'alsa_input\.[A-Za-z0-9_.-]+',data):
                problems.append(f'{relative}: contiene un identificador concreto de entrada de audio')
    for path in ROOT.glob('*.toml'):
        problems.append(f'{path.name}: perfil local fuera de examples/')
    if (ROOT/'gifs').exists():
        problems.append('gifs/: recursos privados todavía dentro del proyecto')
    if problems:
        print('\n'.join(problems),file=sys.stderr)
        return 1
    print(f'Fuentes revisadas: {len(files)} archivos; sin rutas personales, dispositivos reales ni capturas.')
    print('El chequeo no sustituye la revisión manual; build/ y third_party/ son artefactos locales excluidos.')
    return 0


if __name__=='__main__': sys.exit(main())
