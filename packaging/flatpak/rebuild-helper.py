#!/usr/bin/env python3
"""Rebuild only the unprivileged helper artifact inside the recorded SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def rebuild(source_root,output):
    source_root,output=source_root.resolve(),output.resolve()
    if output.exists():
        raise ValueError('Output already exists; choose a new directory')
    info=json.loads((source_root/'BUILD-INFO.json').read_text())
    recipe=json.loads((source_root/'io.github.xoloitzcuintle95.Trama.offline.json').read_text())
    sdk_manifest=Path('/usr/manifest.json')
    expected=source_root/'SDK-SOURCE-MANIFEST.json'
    if not sdk_manifest.exists() or sha(sdk_manifest)!=sha(expected):
        raise ValueError('Rebuild must run inside the recorded SDK')
    inputs={}
    for module in ('libdrm-static','gpu-screen-recorder'):
        item=next(i for i in info['modules'] if i['module']==module and i['source']['type'] in ('git','archive'))
        name=item['archive']
        if Path(name).name!=name:
            raise ValueError('Invalid archive filename')
        archive=source_root/'upstream'/name
        if sha(archive)!=item['sha256']:
            raise ValueError('Source archive hash mismatch')
        inputs[module]=archive
    output.mkdir(parents=True)
    for module,archive in inputs.items():
        target=output/module
        target.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(target,filter='data')
    libdrm=output/'libdrm-static'
    engine=output/'gpu-screen-recorder'
    if not (libdrm/'meson.build').exists() or not (engine/'kms/server/kms_server.c').exists():
        raise ValueError('Unexpected source layout; review before building')
    config=next(m for m in recipe['modules'] if m['name']=='libdrm-static')['config-opts']
    subprocess.run(['meson','setup',str(output/'libdrm-build'),str(libdrm),
                    '--prefix='+str(output/'prefix'),'--wrap-mode=nodownload',*config],check=True)
    subprocess.run(['meson','compile','-C',str(output/'libdrm-build')],check=True)
    subprocess.run(['meson','install','-C',str(output/'libdrm-build')],check=True)
    binary=output/'gsr-kms-server'
    # The same source and flags as the pinned Flatpak recipe. No install/root action.
    subprocess.run(['gcc',str(engine/'kms/server/kms_server.c'),'-o',str(binary),
                    str(output/'prefix/lib/libdrm.a'),'-I'+str(output/'prefix/include/libdrm'),
                    '-fstack-protector-all','-O3','-s','-flto','-Wall','-Wextra','-Werror',
                    '-DNDEBUG','-static','-static-libgcc','-fno-link-libatomic',
                    '-Wl,-Map='+str(output/'helper-link.map')],check=True)
    dynamic=subprocess.check_output(['readelf','-d',str(binary)],text=True)
    if '(NEEDED)' in dynamic:
        raise ValueError('Helper unexpectedly has shared-library dependencies')
    report={'original_helper_sha256':info['build']['gsr_helper_sha256'],
            'rebuilt_helper_sha256':sha(binary),'sdk_manifest_sha256':sha(sdk_manifest),
            'source_archives':{p.name:sha(p) for p in inputs.values()},
            'static_linkage_checked':True}
    (output/'HELPER-REBUILD.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Rebuilt helper SHA-256:',sha(binary))
    print('Original helper SHA-256:',info['build']['gsr_helper_sha256'])
    print('Binary identity is not promised. No installed helper was changed or executed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try: rebuild(args.source_root,args.output)
    except (OSError,ValueError,KeyError,StopIteration,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Helper rebuild failed: {error}\n')
