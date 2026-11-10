#!/usr/bin/env python3
"""Release-assembly checks; no installation, authorization or capture."""
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('release',ROOT/'scripts/release-flatpak.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def test_archive_notices_reject_paths_and_links_and_keep_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=root/'source.tar'
            with tarfile.open(archive,'w') as tar:
                for name,data in [('source/LICENSE',b'Original license'),
                                  ('source/include/test.h',b'/* Copyright Owner. Permission granted. */\nint x;'),
                                  ('../LICENSE',b'escape'),('/LICENSE',b'absolute')]:
                    entry=tarfile.TarInfo(name);entry.size=len(data)
                    tar.addfile(entry,io.BytesIO(data))
                entry=tarfile.TarInfo('source/NOTICE');entry.type=tarfile.SYMTYPE;entry.linkname='/etc/passwd'
                tar.addfile(entry)
            destination=root/'notices'
            self.assertEqual(release.archive_notices(archive,destination,headers=True),2)
            self.assertEqual((destination/'source/LICENSE').read_text(),'Original license')
            self.assertEqual((destination/'source/include/test.h.notice').read_text(),
                             '/* Copyright Owner. Permission granted. */\n')
            self.assertFalse((destination/'source/NOTICE').exists())
            self.assertFalse((root/'LICENSE').exists())

    def test_missing_notices_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'empty.tar'
            with tarfile.open(archive,'w'):
                pass
            with self.assertRaisesRegex(ValueError,'No notices'):
                release.archive_notices(archive,Path(tmp)/'notices')

    def test_metadata_matches_package(self):
        path=ROOT/f'packaging/flatpak/{release.APP}.metainfo.xml'
        component=ET.parse(path).getroot()
        self.assertEqual(component.findtext('id'),release.APP)
        self.assertEqual(component.findtext('project_license'),'GPL-3.0-only')
        self.assertEqual(component.findtext('launchable'),release.APP+'.desktop')
        self.assertEqual(component.find('releases/release').get('version'),release.VERSION)

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'keep').write_text('existing')
            with self.assertRaisesRegex(ValueError,'already exists'):
                release.release(root/'absent',root/'absent',root)
            self.assertEqual((root/'keep').read_text(),'existing')

    def test_candidate_hashes_when_generated(self):
        output=ROOT/'build/releases/0.1.0-alpha1'
        checksum=output/f'trama-{release.VERSION}-x86_64.sha256'
        if not checksum.exists():
            self.skipTest('local candidate not assembled')
        result=subprocess.run(['sha256sum','-c',checksum.name],cwd=output,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        source=output/f'trama-{release.VERSION}-x86_64-sources.tar.xz'
        with tarfile.open(source) as tar:
            names=tar.getnames()
            self.assertFalse(any('/.git/' in n or n.endswith('/perfil.toml') and '/examples/' not in n for n in names))
            self.assertTrue(any(n.endswith('/SDK-SOURCE-MANIFEST.json') for n in names))

if __name__=='__main__':
    unittest.main()
