#!/usr/bin/env python3
"""Fetch exact glibc/SDK source trees for the static helper; no installation."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent
SDK_URL='https://gitlab.com/freedesktop-sdk/freedesktop-sdk.git'
GLIBC_URL='https://sourceware.org/git/glibc.git'
PATCH='patches/glibc/fix-dl-dst-lib.patch'
GLIBC_INCLUDE='elements/bootstrap/include/glibc-source.yml'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def glibc_input(manifest):
    modules=[m for m in manifest['modules'] if m['name']=='bootstrap/glibc.bst']
    if not modules or any(m!=modules[0] for m in modules):
        raise ValueError('Missing or inconsistent SDK glibc inputs')
    sources=modules[0]['sources']
    git=[s for s in sources if s['type']=='git']
    patches=[s for s in sources if s['type']=='patch']
    if len(git)!=1 or git[0]['url']!=GLIBC_URL or [s['path'] for s in patches]!=[PATCH]:
        raise ValueError('Review changed SDK glibc source/patch layout')
    match=re.search(r'-g([0-9a-f]{40})$',git[0]['commit'])
    if not match or len(sources)!=2:
        raise ValueError('Expected an exact SDK glibc Git describe ref')
    return {'url':GLIBC_URL,'commit':match[1],'sdk_ref':git[0]['commit'],'patch':PATCH}


def read_member(archive,name):
    with tarfile.open(archive) as tar:
        member=tar.getmember(name)
        if not member.isfile() or member.size>2*1024*1024:
            raise ValueError('Unexpected source metadata member')
        return tar.extractfile(member).read()


def verify(folder,expected_sdk,expected_manifest):
    folder=Path(folder)
    info=json.loads((folder/'HELPER-SOURCES.json').read_text())
    if info['sdk_commit']!=expected_sdk or info['sdk_manifest_sha256']!=expected_manifest:
        raise ValueError('Helper sources belong to a different SDK')
    for item in info['archives']:
        if Path(item['file']).name!=item['file'] or sha(folder/item['file'])!=item['sha256']:
            raise ValueError('Helper source archive hash mismatch')
    if {x['name'] for x in info['archives']}!={'glibc','freedesktop-sdk'}:
        raise ValueError('Expected both exact SDK and glibc source archives')
    glibc=next(x for x in info['archives'] if x['name']=='glibc')
    sdk=next(x for x in info['archives'] if x['name']=='freedesktop-sdk')
    glibc_metadata=json.loads((folder/'SDK-GLIBC-INPUT.json').read_text())
    if glibc_input(json.loads((folder/'SDK-SOURCE-MANIFEST.json').read_text()))!=glibc_metadata:
        raise ValueError('SDK manifest and glibc source record disagree')
    if sha(folder/'SDK-SOURCE-MANIFEST.json')!=expected_manifest:
        raise ValueError('SDK source manifest hash mismatch')
    if (glibc['commit']!=glibc_metadata['commit'] or glibc['url']!=GLIBC_URL
        or sdk['url']!=SDK_URL or sdk['commit']!=info['sdk_source_commit']):
        raise ValueError('Source identity mismatch')
    element=read_member(folder/sdk['file'],'elements/bootstrap/glibc.bst').decode()
    if GLIBC_INCLUDE not in element:
        raise ValueError('SDK glibc recipe does not include its expected source file')
    source_definition=read_member(folder/sdk['file'],GLIBC_INCLUDE).decode()
    refs=re.findall(r'^\s*ref:\s*(\S+)\s*$',source_definition,re.MULTILINE)
    if refs!=[glibc_metadata['sdk_ref']]:
        raise ValueError('SDK source recipe does not match installed glibc ref')
    patch=read_member(folder/sdk['file'],PATCH)
    if hashlib.sha256(patch).hexdigest()!=info['glibc_patch_sha256']:
        raise ValueError('SDK glibc patch mismatch')
    if b'GNU C Library' not in read_member(folder/glibc['file'],'README'):
        raise ValueError('Unexpected glibc source tree')
    return info


def capture(args):
    return subprocess.check_output([str(x) for x in args],text=True).strip()


def archive_git(name,url,commit,target,cache):
    repository=cache/name
    if not repository.exists():
        repository.mkdir(parents=True)
        subprocess.run(['git','init','--bare','--initial-branch=main',str(repository)],check=True,stdout=subprocess.DEVNULL)
    cached=subprocess.run(['git','-C',str(repository),'cat-file','-e',commit+'^{commit}'],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not cached:
        subprocess.run(['git','-C',str(repository),'fetch','--depth=1',url,commit],check=True)
    if capture(['git','-C',repository,'rev-parse',commit+'^{commit}'])!=commit:
        raise ValueError('Fetched source does not match pinned commit')
    raw=target.with_suffix('.tar')
    try:
        subprocess.run(['git','-C',str(repository),'archive','--format=tar','--output',str(raw),commit],check=True)
        with raw.open('rb') as source,lzma.open(target,'wb',preset=1) as destination:
            shutil.copyfileobj(source,destination)
    finally:
        raw.unlink(missing_ok=True)
    return {'name':name,'url':url,'commit':commit,'file':target.name,'sha256':sha(target)}


def prepare(build,output):
    build,output=build.resolve(),output.resolve()
    if output.exists():
        raise ValueError('Output already exists; use a new --output')
    app=json.loads((build/'files/manifest.json').read_text())
    sdk_commit=capture(['flatpak','info','--show-commit','org.freedesktop.Sdk//26.08'])
    if sdk_commit!=app['sdk-commit']:
        raise ValueError('Installed SDK differs from the original build; retain/install the matching SDK first')
    sdk=Path(capture(['flatpak','info','--show-location','org.freedesktop.Sdk//26.08']))/'files'
    source_manifest=sdk/'manifest.json'
    glibc=glibc_input(json.loads(source_manifest.read_text()))
    # SDK commits use their BuildStream source revision as the signed OSTree subject.
    repository=next((parent/'repo' for parent in sdk.parents if (parent/'repo').is_dir()),None)
    if repository is None:
        # System and user installations have the same runtime/.../commit layout.
        raise ValueError('Cannot locate SDK OSTree repository')
    evidence=capture(['ostree','--repo='+str(repository),'show',sdk_commit])
    revisions=re.findall(r'^    ([0-9a-f]{40})$',evidence,re.MULTILINE)
    if len(revisions)!=1:
        raise ValueError('Review SDK commit subject before selecting its source revision')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='helper-sources-',dir=output.parent) as tmp:
        stage=Path(tmp)
        shutil.copyfile(source_manifest,stage/'SDK-SOURCE-MANIFEST.json')
        (stage/'SDK-GLIBC-INPUT.json').write_text(json.dumps(glibc,indent=2)+'\n')
        (stage/'SDK-OSTREE.txt').write_text(evidence+'\n')
        cache=ROOT/'build/helper-source-cache'
        archives=[archive_git('freedesktop-sdk',SDK_URL,revisions[0],stage/'freedesktop-sdk.tar.xz',cache),
                  archive_git('glibc',GLIBC_URL,glibc['commit'],stage/'glibc.tar.xz',cache)]
        patch=read_member(stage/'freedesktop-sdk.tar.xz',PATCH)
        info={'sdk_commit':sdk_commit,'sdk_manifest_sha256':sha(source_manifest),
              'sdk_source_commit':revisions[0],'glibc_patch_sha256':hashlib.sha256(patch).hexdigest(),
              'archives':archives}
        (stage/'HELPER-SOURCES.json').write_text(json.dumps(info,indent=2)+'\n')
        verify(stage,sdk_commit,sha(source_manifest))
        shutil.copytree(stage,output)
    print(f'Verified helper sources: {output}')
    print('Downloaded source only. Nothing installed or published.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=ROOT/'build/flatpak-app-v4')
    parser.add_argument('--output',type=Path,default=ROOT/'build/helper-sources')
    args=parser.parse_args()
    try: prepare(args.build,args.output)
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Helper source preparation failed: {error}\n')
