#!/usr/bin/env python3
"""Assemble a local candidate from tested binaries; never install or publish."""
import argparse
import importlib.util
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
APP = 'io.github.xoloitzcuintle95.Trama'
VERSION = '0.1.0-alpha1'


def sha(path, algorithm='sha256'):
    digest = hashlib.new(algorithm)
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def run(args):
    return subprocess.check_output([str(x) for x in args], text=True).strip()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o644)


def notice_name(name):
    return re.match(r'^(LICENSE|LICENCE|COPYING|COPYRIGHT|NOTICE|AUTHORS)([._-]|$)',
                    name, re.IGNORECASE) is not None


def archive_notices(archive, destination, headers=False):
    """Read notice files only; never extract links or paths from an archive."""
    count = 0
    with tarfile.open(archive) as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts:
                continue
            if member.size > 2*1024*1024:
                continue
            if notice_name(path.name):
                data = tar.extractfile(member).read()
            elif headers and path.suffix in ('.c', '.h'):
                text = tar.extractfile(member).read(32768).decode('utf-8', errors='replace')
                # libdrm distributes its notices in individual file headers.
                match = re.match(r'\s*(/\*.*?\*/)', text, re.DOTALL)
                if not match or not re.search('copyright|permission', match[1], re.IGNORECASE):
                    continue
                data = (match[1]+'\n').encode()
                path = PurePosixPath(str(path)+'.notice')
            else:
                continue
            target = destination/str(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o644)
            count += 1
    if not count:
        raise ValueError(f'No notices found in {archive.name}')
    return count


def rust_notices(vendor, destination):
    inventory = []
    for crate in sorted(vendor.iterdir()):
        if not crate.is_dir():
            continue
        import tomllib
        package = tomllib.loads((crate/'Cargo.toml').read_text())['package']
        inventory.append({k: package.get(k) for k in ('name','version','license','license-file')})
        files = [p for p in crate.rglob('*') if p.is_file() and notice_name(p.name)]
        target = destination/crate.name
        for path in files:
            copy(path, target/path.relative_to(crate))
        if not files:
            if crate.name not in ('zune-core-0.4.12','zune-jpeg-0.4.21'):
                raise ValueError(f'Missing Rust notices: {crate.name}')
            copy(crate/'Cargo.toml',target/'Cargo.toml')
            header = (crate/'src/lib.rs').read_text().split('*/',1)[0]+'*/\n'
            (target/'NOTICE-source-header.txt').write_text(header)
            copy('/usr/share/common-licenses/Apache-2.0',target/'LICENSE-APACHE-2.0')
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    return inventory


def release(build, snapshot, output, helper_sources=None, helper_rebuild=None):
    build, snapshot, output = (p.resolve() for p in (build,snapshot,output))
    if output.exists():
        raise ValueError('Output already exists; choose a new directory')
    recipe = json.loads((snapshot/f'{APP}.json').read_text())
    provenance = json.loads((build/'files/manifest.json').read_text())
    manifest = json.loads((build/'files/lib/trama/build/overlay-rust.build.json').read_text())
    if manifest.get('test_hooks') or 'static' not in manifest.get('ffmpeg',''):
        raise ValueError('Expected verified static FFmpeg production build')
    private = build/'files/lib/trama'
    binaries = {'gsr_sha256':private/'engine/gpu-screen-recorder',
                'gsr_helper_sha256':private/'engine/gsr-kms-server',
                'plugin_sha256':private/'build/overlay-rust.so',
                'scene_checker_sha256':private/'build/rust-target/release/scene-check'}
    for key,path in binaries.items():
        if sha(path)!=manifest[key]:
            raise ValueError(f'Build integrity mismatch: {key}')
    stage = snapshot/'trama-source'
    for path in (stage/'scripts').glob('*.py'):
        if sha(path)!=sha(private/'scripts'/path.name):
            raise ValueError(f'Snapshot does not match tested runtime: {path.name}')
    if sha(stage/'rust/Cargo.lock')!=manifest['cargo_lock_sha256']:
        raise ValueError('Snapshot Cargo.lock mismatch')
    if [m['name'] for m in recipe['modules']] != [m['name'] for m in provenance['modules']]:
        raise ValueError('Build/recipe module mismatch')
    for planned,actual in zip(recipe['modules'],provenance['modules']):
        if planned.get('build-commands',[]) != actual.get('build-commands',[]):
            raise ValueError(f'Build command mismatch: {planned["name"]}')
        planned_sources,actual_sources = planned.get('sources',[]),actual.get('sources',[])
        if len(planned_sources)!=len(actual_sources):
            raise ValueError('Source count mismatch')
        for expected,used in zip(planned_sources,actual_sources):
            for key in ('type','url','commit','sha256','sha512','dest','dest-filename'):
                if expected.get(key)!=used.get(key):
                    raise ValueError(f'Build source mismatch: {planned["name"]}/{key}')
    output.mkdir(parents=True)
    stem = f'trama-{VERSION}-x86_64'
    with tempfile.TemporaryDirectory(prefix='trama-release-',dir=output) as tmp:
        work = Path(tmp)
        candidate = work/'app'
        # Preserve tested binaries, modes and sandbox metadata. No installed files change.
        shutil.copytree(build,candidate,symlinks=True)
        # libdrm headers, pkg-config data and static archives are build inputs.
        for folder in ('include','lib/pkgconfig'):
            shutil.rmtree(candidate/'files'/folder,ignore_errors=True)
        for name in ('libdrm.a','libdrm_intel.a'):
            (candidate/'files/lib'/name).unlink(missing_ok=True)
        sources = work/stem
        sources.mkdir()
        shutil.copytree(stage,sources/'trama-source')
        for name in ('adapt-app-id.py','launch-kms.sh',f'{APP}.json'):
            copy(snapshot/name,sources/name)
        copy(ROOT/'scripts/release-flatpak.py',sources/'release-flatpak.py')
        copy(ROOT/'scripts/prepare-helper-sources.py',sources/'prepare-helper-sources.py')
        copy(ROOT/'packaging/flatpak/rebuild-helper.py',sources/'rebuild-helper.py')
        source_archives = sources/'upstream'
        source_archives.mkdir()
        notices = candidate/'files/share/licenses'
        inventory = []
        for module in recipe['modules']:
            for source in module.get('sources',[]):
                if 'url' not in source:
                    continue
                if source['type']=='git':
                    if module['name']!='libdrm-static':
                        raise ValueError('Review newly added Git source')
                    repository = ROOT/'build/flatpak-state/git/https_gitlab.freedesktop.org_mesa_drm.git'
                    archive = source_archives/'libdrm.tar'
                    with archive.open('wb') as stream:
                        subprocess.run(['git','-C',str(repository),'archive',source['commit']],stdout=stream,check=True)
                    count = archive_notices(archive,notices/'libdrm',headers=True)
                else:
                    algorithm = 'sha512' if 'sha512' in source else 'sha256'
                    digest = source[algorithm]
                    cached = ROOT/'build/flatpak-state/downloads'/digest
                    matches = [p for p in cached.iterdir() if p.is_file() and sha(p,algorithm)==digest]
                    if len(matches)!=1:
                        raise ValueError(f'Missing/ambiguous verified source: {source["url"]}')
                    archive = source_archives/matches[0].name
                    copy(matches[0],archive)
                    component = module['name']
                    if component=='gpu-screen-recorder':
                        component = 'gsr' if source['type']=='archive' else source['dest-filename'].split('-')[0]
                        if source.get('dest-filename','').startswith('nv-codec-headers'):
                            component = 'nv-codec-headers'
                    count = archive_notices(archive,notices/component,
                                            headers=component=='nv-codec-headers')
                inventory.append({'module':module['name'],'source':source,'archive':archive.name,
                                  'sha256':sha(archive),'notice_files':count})
        rust_inventory = rust_notices(stage/'rust/vendor',notices/'rust')
        copy(ROOT/'packaging/flatpak/NOTICE',notices/'NOTICE')
        copy(ROOT/'packaging/flatpak/NOTICE',notices/'trama/copyright')
        copy('/usr/share/common-licenses/CC0-1.0',notices/'trama/AppStream-CC0-1.0')
        metadata = ROOT/f'packaging/flatpak/{APP}.metainfo.xml'
        copy(metadata,candidate/f'files/share/metainfo/{APP}.metainfo.xml')
        copy(metadata,sources/f'trama-source/packaging/flatpak/{APP}.metainfo.xml')
        copy(ROOT/'packaging/flatpak/NOTICE',sources/'trama-source/packaging/flatpak/NOTICE')
        # Keep SDK provenance/notices for code linked into the static helper.
        sdk = Path(run(['flatpak','info','--show-location','org.freedesktop.Sdk//26.08']))/'files'
        if run(['flatpak','info','--show-commit','org.freedesktop.Sdk//26.08'])!=provenance.get('sdk-commit'):
            raise ValueError('Installed SDK differs from build provenance; do not substitute its notices or sources')
        copy(sdk/'manifest.json',sources/'SDK-SOURCE-MANIFEST.json')
        for component in ('glibc','gcc'):
            folder = sdk/'share/licenses/freedesktop-sdk'/component
            if folder.exists():
                for path in folder.rglob('*'):
                    original = path
                    if path.is_symlink():
                        link = path.readlink()
                        if not str(link).startswith('/usr/'):
                            raise ValueError('Review unexpected SDK license symlink')
                        original = sdk/str(link)[5:]
                    if original.is_file():
                        copy(original,notices/'sdk'/component/path.relative_to(folder))
        copy('/usr/share/common-licenses/LGPL-2.1',notices/'sdk/LGPL-2.1')
        copy('/usr/share/common-licenses/GPL-3',notices/'sdk/GPL-3')
        # Never imply a source URL list substitutes for static libc source obligations.
        blockers = ['Review/provide exact SDK glibc sources, SDK patch and static-helper relinking instructions before public distribution.',
                    'Check host helper ownership, capability state and process exit; retest final metadata/notices candidate.']
        url_types = {item.get('type') for item in ET.parse(metadata).getroot().findall('url')
                     if (item.text or '').strip()}
        if not {'homepage','vcs-browser','bugtracker'} <= url_types:
            blockers.append('Configure real public homepage/source/issue URLs in AppStream metadata; no placeholder URLs are supplied.')
        helper_info=None
        if helper_sources is not None:
            spec=importlib.util.spec_from_file_location('helper_sources',ROOT/'scripts/prepare-helper-sources.py')
            helper_module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper_module)
            helper_info=helper_module.verify(helper_sources,provenance['sdk-commit'],sha(sdk/'manifest.json'))
            helper_target=sources/'helper-sources'
            helper_target.mkdir()
            for name in ('HELPER-SOURCES.json','SDK-GLIBC-INPUT.json','SDK-SOURCE-MANIFEST.json','SDK-OSTREE.txt'):
                copy(Path(helper_sources)/name,helper_target/name)
            for item in helper_info['archives']:
                copy(Path(helper_sources)/item['file'],helper_target/item['file'])
            blockers[0]='Exact SDK/glibc sources included; verify the helper rebuild/relink procedure with the recorded SDK.'
            if helper_rebuild is not None:
                report=json.loads(helper_rebuild.read_text())
                if (report.get('original_helper_sha256')!=manifest['gsr_helper_sha256']
                    or report.get('sdk_manifest_sha256')!=sha(sdk/'manifest.json')
                    or report.get('static_linkage_checked') is not True
                    or report.get('rebuilt_helper_sha256')!=sha(helper_rebuild.parent/'gsr-kms-server')):
                    raise ValueError('Helper rebuild report does not match the original SDK/artifact')
                expected={i['archive']:i['sha256'] for i in inventory if i['module']=='libdrm-static'
                          or i['module']=='gpu-screen-recorder' and i['source']['type']=='archive'}
                if report.get('source_archives')!=expected:
                    raise ValueError('Helper rebuild source archive mismatch')
                copy(helper_rebuild,sources/'HELPER-REBUILD.json')
                blockers.pop(0)
        elif helper_rebuild is not None:
            raise ValueError('A rebuild report requires --helper-sources')
        info = {'version':VERSION,'branch':'experimental','build':manifest,
                'runtime_commit':provenance.get('runtime-commit'),'sdk_commit':provenance.get('sdk-commit'),
                'modules':inventory,'rust':rust_inventory,'helper_sources':helper_info,
                'publication_blockers':blockers}
        (sources/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
        copy(ROOT/'packaging/flatpak/REBUILD.md',sources/'REBUILD.md')
        # Reference local archive copies during rebuild; no third-party download needed.
        offline = json.loads(json.dumps(recipe))
        for module in offline['modules']:
            replacement = []
            for source in module.get('sources',[]):
                if 'url' not in source:
                    replacement.append(source)
                    continue
                item = next(i for i in inventory if i['source']==source)
                entry = {'type':source['type'],'path':'upstream/'+item['archive']}
                if source['type']=='git':
                    entry = {'type':'archive','path':'upstream/'+item['archive'],'strip-components':0}
                else:
                    for key in ('dest','dest-filename','strip-components','sha256','sha512'):
                        if key in source:
                            entry[key]=source[key]
                replacement.append(entry)
            module['sources']=replacement
        (sources/f'{APP}.offline.json').write_text(json.dumps(offline,indent=2)+'\n')
        (notices/'inventory.json').write_text(json.dumps(info,indent=2)+'\n')
        # Recheck the binaries after packaging-only additions.
        for key,path in binaries.items():
            if sha(candidate/path.relative_to(build))!=manifest[key]:
                raise ValueError('Candidate unexpectedly changed a tested binary')
        repository = output/'repo'
        subprocess.run(['flatpak','build-export','--disable-sandbox',str(repository),str(candidate),'experimental'],check=True)
        bundle = output/(stem+'.flatpak')
        subprocess.run(['flatpak','build-bundle','--arch=x86_64',
                        '--runtime-repo=https://flathub.org/repo/flathub.flatpakrepo',
                        str(repository),str(bundle),APP,'experimental'],check=True)
        source_file = output/(stem+'-sources.tar.xz')
        def clean_member(member):
            member.uid=member.gid=0
            member.uname=member.gname=''
            return member
        with tarfile.open(source_file,'w:xz') as tar:
            tar.add(sources,arcname=stem,filter=clean_member)
        (output/'RELEASE-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
        artifacts = (bundle,source_file,output/'RELEASE-INFO.json')
        (output/(stem+'.sha256')).write_text(''.join(sha(p)+'  '+p.name+'\n' for p in artifacts))
        for path in artifacts:
            print(f'{path.name}: {path.stat().st_size/1024/1024:.2f} MiB')
        print('Local candidate only; not installed/published. Publication blockers are in RELEASE-INFO.json.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=ROOT/'build/flatpak-app-v4')
    parser.add_argument('--snapshot',type=Path,default=ROOT/'build/flatpak-input-v4')
    parser.add_argument('--output',type=Path,default=ROOT/'build/releases/0.1.0-alpha1')
    parser.add_argument('--helper-sources',type=Path,help='Verified SDK/glibc source bundle from prepare-helper-sources.py')
    parser.add_argument('--helper-rebuild',type=Path,help='HELPER-REBUILD.json from the recorded SDK')
    args=parser.parse_args()
    try:
        release(args.build,args.snapshot,args.output,args.helper_sources,args.helper_rebuild)
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Release preparation failed: {error}\n')
