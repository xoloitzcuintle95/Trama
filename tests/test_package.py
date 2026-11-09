"""Inspect/extract the preliminary package; never install or grant privileges."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DEB=ROOT/'build/packages/trama_0.1.0~alpha1_amd64.deb'


@unittest.skipUnless(DEB.is_file(),'Build the local .deb with scripts/build-deb.py first')
class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        subprocess.run(['dpkg-deb','--extract',str(DEB),str(cls.base)],check=True)
        cls.runtime=cls.base/'usr/lib/trama'
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def command(self,args,**kwargs):
        return subprocess.run(args,capture_output=True,text=True,env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1'},**kwargs)

    def test_allowlisted_runtime_and_no_privileged_install_scripts(self):
        data=subprocess.check_output(['dpkg-deb','--fsys-tarfile',str(DEB)])
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            members=tar.getmembers()
        files=[m.name for m in members if m.isfile()]
        self.assertTrue(all(m.uid==0 and m.gid==0 for m in members))
        self.assertTrue(all(not m.mode & 0o6000 for m in members))
        self.assertEqual(sorted(p.name for p in (self.runtime/'engine').iterdir()),['gpu-screen-recorder','gsr-kms-server'])
        self.assertFalse(any('third_party' in p or '/tests/' in p or '__pycache__' in p or p.endswith(('.mkv','.mp4')) for p in files))
        self.assertNotIn('./usr/bin/gpu-screen-recorder',files)
        self.assertNotIn('./usr/bin/xolo',files)
        control=subprocess.check_output(['dpkg-deb','--ctrl-tarfile',str(DEB)])
        with tarfile.open(fileobj=io.BytesIO(control)) as tar:
            self.assertFalse(any(m.name.endswith(('postinst','preinst','postrm','prerm')) for m in tar.getmembers()))
        desktop=(self.base/'usr/share/applications/trama.desktop').read_text()
        self.assertIn('Terminal=true',desktop);self.assertIn('Exec=trama',desktop)

    def test_private_engine_and_manifest_work_after_relocation(self):
        code='''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from compositor_devices import Devices
from compositor import verified_build
engine=Devices().gsr
plugin,checker,manifest=verified_build(engine)
print(json.dumps({'engine':engine,'plugin':str(plugin),'checker':str(checker)}))
'''
        result=self.command([sys.executable,'-c',code,str(self.runtime/'scripts')])
        self.assertEqual(result.returncode,0,result.stderr)
        paths=json.loads(result.stdout)
        self.assertEqual(paths['engine'],str(self.runtime/'engine/gpu-screen-recorder'))
        self.assertTrue(all(str(self.runtime) in value for value in paths.values()))

    def test_packaged_help_and_production_asset_decoder(self):
        result=self.command([sys.executable,str(self.runtime/'scripts/trama_tui.py'),'--lang','en','--help'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Interface language',result.stdout)
        profile=self.base/'usr/share/doc/trama/examples/perfil.toml'
        result=self.command([sys.executable,str(self.runtime/'scripts/compositor.py'),'check',str(profile),'--assets-only'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('0.50 MiB',result.stdout)
        self.assertIn('SOLO RECURSOS',result.stdout)

    def test_tampered_helper_is_rejected_before_capture(self):
        helper=self.runtime/'engine/gsr-kms-server'
        original=helper.read_bytes()
        try:
            helper.write_bytes(original+b'changed')
            code='''import sys
sys.path.insert(0,sys.argv[1])
from compositor import verified_build
from compositor_devices import Devices
verified_build(Devices().gsr)
'''
            result=self.command([sys.executable,'-c',code,str(self.runtime/'scripts')])
            self.assertNotEqual(result.returncode,0)
            self.assertIn('helper/checker',result.stderr)
        finally: helper.write_bytes(original)

    def test_hashes_sources_and_notices_present(self):
        stem=DEB.stem
        checksums=(DEB.parent/(stem+'.sha256')).read_text().splitlines()
        for line in checksums:
            digest,name=line.split('  ',1)
            self.assertEqual(hashlib.sha256((DEB.parent/name).read_bytes()).hexdigest(),digest)
        with tarfile.open(DEB.parent/(stem+'-sources.tar.xz')) as tar:
            names=tar.getnames()
        self.assertTrue(any(n.endswith('/third_party/gpu-screen-recorder/LICENSE') for n in names))
        self.assertTrue(any('/rust/vendor/' in n and n.endswith('/Cargo.toml') for n in names))
        self.assertFalse(any('/.git/' in n or '/__pycache__/' in n for n in names))
        notices=self.base/'usr/share/doc/trama/licenses'
        self.assertTrue((notices/'GSR-GPL-3.0.txt').is_file())
        self.assertTrue((notices/'Trama-GPL-3.0.txt').is_file())
        copyright=(self.base/'usr/share/doc/trama/copyright').read_text()
        self.assertIn('icon, mascot and hero are covered by the same GPL-3.0-only',copyright)
        self.assertTrue((notices/'rust/inventory.json').is_file())


if __name__=='__main__': unittest.main()
