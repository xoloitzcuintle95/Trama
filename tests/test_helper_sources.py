#!/usr/bin/env python3
"""Verify exact-source collection without network, root or actual SDK builds."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('helper',ROOT/'scripts/prepare-helper-sources.py')
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
COMMIT='a'*40
SDK='b'*64
SOURCE='c'*40
REF='glibc-2.44-49-g'+COMMIT


def manifest():
    return {'modules':[{'name':'bootstrap/glibc.bst','sources':[
        {'type':'git','url':helper.GLIBC_URL,'commit':REF},
        {'type':'patch','path':helper.PATCH}]}]}


def archive(path,files):
    with tarfile.open(path,'w:xz') as tar:
        for name,data in files.items():
            member=tarfile.TarInfo(name);member.size=len(data)
            tar.addfile(member,io.BytesIO(data))


class HelperSourceTests(unittest.TestCase):
    def test_reviewed_sdk_cache_reuses_commit_without_fetch_and_has_source_include(self):
        cache=ROOT/'build/helper-source-cache'
        if not (cache/'freedesktop-sdk').exists():
            self.skipTest('optional reviewed SDK source cache absent')
        revision='114ae909ec9881958bd507c8b4414aa33f758d2b'
        original_run=helper.subprocess.run
        def offline_run(args,**kwargs):
            self.assertNotIn('fetch',args,'An existing exact commit must work offline')
            return original_run(args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'sdk.tar.xz'
            with mock.patch.object(helper.subprocess,'run',side_effect=offline_run):
                info=helper.archive_git('freedesktop-sdk',helper.SDK_URL,revision,target,cache)
            element=helper.read_member(target,'elements/bootstrap/glibc.bst').decode()
            definition=helper.read_member(target,helper.GLIBC_INCLUDE).decode()
            self.assertIn(helper.GLIBC_INCLUDE,element)
            self.assertNotIn('glibc-2.44-49-g6b48c0',element)
            self.assertIn('ref: glibc-2.44-49-g6b48c0b29c359dfa84c09c32373a48c8f663c304',definition)
            self.assertEqual(info['commit'],revision)

    def fixture(self,folder):
        sdk_manifest=folder/'SDK-SOURCE-MANIFEST.json'
        sdk_manifest.write_text(json.dumps(manifest()))
        (folder/'SDK-GLIBC-INPUT.json').write_text(json.dumps(helper.glibc_input(manifest())))
        patch=b'Exact SDK patch\n'
        archive(folder/'sdk.tar.xz',{'elements/bootstrap/glibc.bst':helper.GLIBC_INCLUDE.encode(),helper.GLIBC_INCLUDE:('ref: '+REF+'\n').encode(),helper.PATCH:patch})
        archive(folder/'glibc.tar.xz',{'README':b'GNU C Library source'})
        info={'sdk_commit':SDK,'sdk_manifest_sha256':helper.sha(sdk_manifest),
              'sdk_source_commit':SOURCE,'glibc_patch_sha256':hashlib.sha256(patch).hexdigest(),
              'archives':[{'name':'glibc','url':helper.GLIBC_URL,'commit':COMMIT,'file':'glibc.tar.xz',
                           'sha256':helper.sha(folder/'glibc.tar.xz')},
                          {'name':'freedesktop-sdk','url':helper.SDK_URL,'commit':SOURCE,'file':'sdk.tar.xz',
                           'sha256':helper.sha(folder/'sdk.tar.xz')}]}
        (folder/'HELPER-SOURCES.json').write_text(json.dumps(info))
        return info

    def test_extract_exact_ref_and_accept_repeated_sdk_entries(self):
        data=manifest()
        data['modules']*=2
        self.assertEqual(helper.glibc_input(data)['commit'],COMMIT)

    def test_changed_sources_are_rejected(self):
        for mutation in ('url','commit','patch','extra'):
            data=manifest();sources=data['modules'][0]['sources']
            if mutation=='url':sources[0]['url']='https://example.invalid/glibc'
            if mutation=='commit':sources[0]['commit']='master'
            if mutation=='patch':sources[1]['path']='other.patch'
            if mutation=='extra':sources.append({'type':'patch','path':'extra.patch'})
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                helper.glibc_input(data)

    def test_verify_exact_archives_patch_and_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);info=self.fixture(folder)
            self.assertEqual(helper.verify(folder,SDK,info['sdk_manifest_sha256']),info)
            with self.assertRaisesRegex(ValueError,'different SDK'):
                helper.verify(folder,'d'*64,info['sdk_manifest_sha256'])

    def test_changed_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);info=self.fixture(folder)
            (folder/'glibc.tar.xz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                helper.verify(folder,SDK,info['sdk_manifest_sha256'])

    def test_wrong_patch_or_recipe_is_rejected_even_with_valid_archive_hash(self):
        for changed in ('patch','recipe'):
            with tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);info=self.fixture(folder)
                files={'elements/bootstrap/glibc.bst':helper.GLIBC_INCLUDE.encode(),helper.GLIBC_INCLUDE:('ref: '+REF+'\n').encode(),helper.PATCH:b'Exact SDK patch\n'}
                if changed=='patch':files[helper.PATCH]=b'changed'
                else:files[helper.GLIBC_INCLUDE]=b'ref: other-version\n'
                archive(folder/'sdk.tar.xz',files)
                info['archives'][1]['sha256']=helper.sha(folder/'sdk.tar.xz')
                (folder/'HELPER-SOURCES.json').write_text(json.dumps(info))
                with self.subTest(changed=changed),self.assertRaises(ValueError):
                    helper.verify(folder,SDK,info['sdk_manifest_sha256'])

    def test_escaping_archive_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);info=self.fixture(folder)
            info['archives'][0]['file']='../glibc.tar.xz'
            (folder/'HELPER-SOURCES.json').write_text(json.dumps(info))
            with self.assertRaises(ValueError):helper.verify(folder,SDK,info['sdk_manifest_sha256'])

if __name__=='__main__': unittest.main()
