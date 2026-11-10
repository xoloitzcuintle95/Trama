#!/usr/bin/env python3
"""Build a local preliminary .deb plus matching sources; never install or setcap."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent
VERSION='0.1.0~alpha1'
GSR_COMMIT='f97d1e392816503282d20a0804c3ce3fd2943767'
MODULES=('compositor','compositor_devices','compositor_profile','rust_runtime','measure',
         'trama_model','trama_tui','trama_view','trama_i18n')
SOURCE_DIRS=('scripts','rust','src','tests','docs','examples','assets','packaging')


def run(args,**kwargs):
    return subprocess.check_output([str(x) for x in args],text=True,**kwargs)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy(source,target,mode=0o644):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    target.chmod(mode)


def dependencies(binaries,work):
    # Debian's ELF resolver obtains versions from the libraries actually linked.
    (work/'debian').mkdir(exist_ok=True)
    (work/'debian/control').write_text('Source: trama\nSection: video\nPriority: optional\nMaintainer: Trama local build <noreply@localhost>\n\nPackage: trama\nArchitecture: any\nDescription: Local preliminary build\n')
    output=run(['dpkg-shlibdeps','-O',*[f'-e{p.relative_to(work)}' for p in binaries]],cwd=work)
    linked=next(line.split('=',1)[1] for line in output.splitlines() if line.startswith('shlibs:Depends='))
    # GSR also loads these graphics libraries dynamically. Driver choice is local.
    return ', '.join(dict.fromkeys(('python3 (>= 3.11), ffmpeg, pulseaudio-utils, pkexec, libegl1, libgl1, libglx0, libgbm1, '+linked).split(', ')))


def source_file(path):
    return (path.is_file() and not any(part in ('target','vendor','__pycache__') for part in path.parts)
            and path.suffix not in ('.pyc','.so','.o','.a','.mkv','.mp4','.log'))


def build(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    engine=ROOT/'third_party/gpu-screen-recorder'
    if run(['git','-C',engine,'rev-parse','HEAD']).strip()!=GSR_COMMIT:
        raise ValueError('GSR commit does not match the reviewed ABI baseline')
    subprocess.run(['git','-C',str(engine),'diff','--exit-code','HEAD'],check=True,stdout=subprocess.DEVNULL)
    manifest=json.loads((ROOT/'build/overlay-rust.build.json').read_text())
    required={'gsr_sha256':engine/'build/gpu-screen-recorder',
              'plugin_sha256':ROOT/'build/overlay-rust.so',
              'header_sha256':engine/'plugin/plugin.h',
              'cargo_lock_sha256':ROOT/'rust/Cargo.lock'}
    if manifest['test_hooks'] or manifest['gsr_commit']!=GSR_COMMIT:
        raise ValueError('Production manifest required; test-hooks are not distributable')
    for key,path in required.items():
        if sha(path)!=manifest[key]: raise ValueError(f'{key}: artifact differs from verified build')
    arch=run(['dpkg','--print-architecture']).strip()
    if arch!='amd64': raise ValueError('This preliminary build is verified only for amd64')
    stem=f'trama_{VERSION}_{arch}'
    with tempfile.TemporaryDirectory(prefix='trama-package-',dir=output) as tmp:
        work=Path(tmp);stage=work/'debian/trama';runtime=stage/'usr/lib/trama'
        for module in MODULES:
            copy(ROOT/f'scripts/{module}.py',runtime/f'scripts/{module}.py')
        for name in ('gpu-screen-recorder','gsr-kms-server'):
            copy(engine/'build'/name,runtime/'engine'/name,0o755)
        copy(ROOT/'build/overlay-rust.so',runtime/'build/overlay-rust.so',0o755)
        checker=runtime/'build/rust-target/release/scene-check'
        copy(ROOT/'build/rust-target/release/scene-check',checker,0o755)
        manifest['gsr_helper_sha256']=sha(runtime/'engine/gsr-kms-server')
        manifest['scene_checker_sha256']=sha(checker)
        (runtime/'build/overlay-rust.build.json').write_text(json.dumps(manifest,indent=2)+'\n')
        launcher=stage/'usr/bin/trama';launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/lib/trama/scripts/trama_tui.py "$@"\n');launcher.chmod(0o755)
        copy(ROOT/'assets/brand/icon.png',stage/'usr/share/pixmaps/trama.png')
        copy(ROOT/'packaging/trama.desktop',stage/'usr/share/applications/trama.desktop')
        doc=stage/'usr/share/doc/trama'
        for name in ('README.md','docs/tui.md','docs/desarrollo.md'):
            copy(ROOT/name,doc/Path(name).name)
        copy(ROOT/'packaging/copyright',doc/'copyright')
        copy(ROOT/'LICENSE',doc/'licenses/Trama-GPL-3.0.txt')
        copy(engine/'LICENSE',doc/'licenses/GSR-GPL-3.0.txt')
        for path in (ROOT/'examples').rglob('*'):
            if path.is_file(): copy(path,doc/'examples'/path.relative_to(ROOT/'examples'))
        # Corresponding source snapshot and lockfile dependencies remain separate
        # from the installed runtime and retain their original notices.
        sources=work/stem;sources.mkdir()
        for folder in SOURCE_DIRS:
            for path in (ROOT/folder).rglob('*'):
                if source_file(path): copy(path,sources/path.relative_to(ROOT),0o755 if os.access(path,os.X_OK) else 0o644)
        for name in ('trama','README.md','AGENTS.md','.gitignore','LICENSE'):
            copy(ROOT/name,sources/name,0o755 if name=='trama' else 0o644)
        upstream=sources/'third_party/gpu-screen-recorder';upstream.mkdir(parents=True)
        archive=subprocess.check_output(['git','-C',str(engine),'archive',GSR_COMMIT])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(upstream,filter='data')
        metadata=json.loads(run(['cargo','metadata','--manifest-path',ROOT/'rust/Cargo.toml','--offline','--locked','--format-version','1']))
        registry=[p for p in metadata['packages'] if p['source']]
        notices=[]
        for package in registry:
            source=Path(package['manifest_path']).parent
            identifier=package['name']+'-'+package['version']
            notices.append({key:package[key] for key in ('name','version','license','source')})
            license_files=[p for p in source.rglob('*') if p.is_file() and
                           (p.name.upper().startswith(('LICENSE','COPYING','NOTICE')) or p.name=='COPYRIGHT')]
            if not license_files:
                # These exact crates publish license declarations in Cargo.toml
                # and source headers, but omit separate license text files.
                if identifier not in ('zune-core-0.4.12','zune-jpeg-0.4.21'):
                    raise ValueError(f'Missing dependency notices: {identifier}')
                destination=doc/'licenses/rust'/identifier
                copy(source/'Cargo.toml',destination/'Cargo.toml')
                header=(source/'src/lib.rs').read_text().split('*/',1)[0]+'*/\n'
                (destination/'NOTICE-source-header.txt').write_text(header)
                copy(Path('/usr/share/common-licenses/Apache-2.0'),destination/'LICENSE-APACHE-2.0')
            for path in license_files: copy(path,doc/'licenses/rust'/identifier/path.relative_to(source))
        (doc/'licenses/rust/inventory.json').write_text(json.dumps(notices,indent=2)+'\n')
        run(['cargo','vendor','--offline','--locked','--versioned-dirs','--manifest-path',ROOT/'rust/Cargo.toml',sources/'rust/vendor'],stderr=subprocess.DEVNULL)
        config=sources/'.cargo/config.toml';config.parent.mkdir()
        config.write_text('[source.crates-io]\nreplace-with = "vendored-sources"\n[source.vendored-sources]\ndirectory = "rust/vendor"\n')
        (sources/'BUILD-INFO.json').write_text(json.dumps({'gsr_commit':GSR_COMMIT,'version':VERSION,'architecture':arch,
            'artifacts':manifest,'rustc':run(['rustc','--version']).strip()},indent=2)+'\n')
        binary_files=[runtime/'engine/gpu-screen-recorder',runtime/'engine/gsr-kms-server',runtime/'build/overlay-rust.so',checker]
        depends=dependencies(binary_files,work)
        size=sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
        control=stage/'DEBIAN/control';control.parent.mkdir()
        control.write_text(f'Package: trama\nVersion: {VERSION}\nArchitecture: {arch}\nSection: video\nPriority: optional\nMaintainer: Trama local build <noreply@localhost>\nInstalled-Size: {(size+1023)//1024}\nDepends: {depends}\nDescription: Trama local preliminary TUI recorder with pinned GSR engine\n Terminal interface for screen capture, overlays and microphone-reactive avatars.\n Local evaluation build; hardware installation and capture validation are pending.\n')
        (stage/'DEBIAN/md5sums').write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(stage))+'\n'
            for p in sorted(stage.rglob('*')) if p.is_file() and 'DEBIAN' not in p.relative_to(stage).parts))
        deb=output/(stem+'.deb')
        subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','--build',str(stage),str(deb)],check=True)
        source_archive=output/(stem+'-sources.tar.xz')
        with tarfile.open(source_archive,'w:xz') as tar:
            tar.add(sources,arcname=stem)
        (output/(stem+'.sha256')).write_text(''.join(sha(p)+'  '+p.name+'\n' for p in (deb,source_archive)))
        print(f'DEB: {deb} ({deb.stat().st_size/1024/1024:.2f} MiB)')
        print(f'Sources: {source_archive} ({source_archive.stat().st_size/1024/1024:.2f} MiB)')
        print('Not installed. No capabilities or system files were changed.')
    return deb


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/packages')
    args=parser.parse_args()
    try: build(args.output)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc: parser.exit(1,f'Build failed: {exc}\n')
