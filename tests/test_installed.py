"""Installed-runtime acceptance with temporary profiles; no real capture or sudo."""
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
RUNTIME=Path('/usr/lib/trama')
DEB=ROOT/'build/packages/trama_0.1.0~alpha1_amd64.deb'
sys.path.insert(0,str(ROOT/'scripts'))
from compositor_profile import load_profile,save_profile


@unittest.skipUnless((RUNTIME/'scripts/trama_tui.py').is_file(),'Trama is not installed')
class InstalledTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='trama-installed-test-')
        self.base=Path(self.tmp.name)
        self.env=os.environ|{'HOME':str(self.base),'XDG_CONFIG_HOME':str(self.base/'config'),
            'XDG_STATE_HOME':str(self.base/'state'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8',
            'LC_ALL':'C.UTF-8','LC_MESSAGES':'C.UTF-8'}
        self.profile=load_profile(ROOT/'examples/perfil.toml')
        self.profile['recording'].update(screen='TEST-DISPLAY',output=str(self.base/'recordings/{timestamp}.mkv'))
        self.path=self.base/'test-profile.toml'
    def tearDown(self): self.tmp.cleanup()

    def command(self,args):
        return subprocess.run(args,capture_output=True,text=True,env=self.env,cwd=self.base,timeout=20)

    def python(self,code,*args):
        return self.command([sys.executable,'-c','import sys;sys.path.insert(0,'+repr(str(RUNTIME/'scripts'))+');'+code,*map(str,args)])

    def check_profile(self):
        save_profile(self.profile,self.path)
        return self.command([sys.executable,str(RUNTIME/'scripts/compositor.py'),'check',str(self.path),'--assets-only'])

    @unittest.skipUnless(DEB.is_file(),'No local package for comparison')
    def test_installed_executable_and_runtime_match_the_package(self):
        data=subprocess.check_output(['dpkg-deb','--fsys-tarfile',str(DEB)])
        count=0
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for member in tar:
                if member.isfile() and (member.name.startswith('./usr/lib/trama/') or member.name=='./usr/bin/trama'):
                    installed=Path('/')/member.name.removeprefix('./')
                    self.assertEqual(hashlib.sha256(installed.read_bytes()).digest(),
                                     hashlib.sha256(tar.extractfile(member).read()).digest(),member.name)
                    count+=1
        self.assertGreater(count,10)

    def test_actual_launcher_help_uses_isolated_configuration(self):
        for language,text in [('en','Interface language'),('es','Idioma de la interfaz')]:
            result=self.command(['/usr/bin/trama','--lang',language,'--help'])
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(text,result.stdout)
        self.assertFalse((self.base/'config').exists())
        self.assertFalse((self.base/'state').exists())

    def test_clean_state_starts_a_new_profile_and_defaults_to_english(self):
        code='''import json
from trama_model import initial_path,Model
from trama_i18n import read_preference,select_language,language
path=initial_path();model=Model(path)
select_language(read_preference())
print(json.dumps({'path':str(path),'new':model.is_new,'layers':model.profile['layers'],'language':language()}))
'''
        result=self.python(code)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data,{'path':str(self.base/'perfil.toml'),'new':True,'layers':[],'language':'en'})
        self.assertFalse((self.base/'perfil.toml').exists())

    def test_installed_decoder_loads_examples_without_changing_profile(self):
        result=self.check_profile()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('0.50 MiB',result.stdout)
        before=self.path.read_bytes()
        second=self.command([sys.executable,str(RUNTIME/'scripts/compositor.py'),'check',str(self.path),'--assets-only'])
        self.assertEqual(second.returncode,0,second.stderr)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse((self.base/'recordings').exists())

    def test_installed_layers_formats_corners_visibility_order_and_roundtrip(self):
        from PIL import Image
        jpeg=self.base/'sample.jpg'
        Image.new('RGB',(80,40),(40,100,160)).save(jpeg)
        save_profile(self.profile,self.path)
        code='''from pathlib import Path
from trama_model import Model
model=Model(Path(sys.argv[1]))
model.screens={'TEST-DISPLAY':(1920,1080)}
files=[Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4])]
for i,path in enumerate(files):
 model.add_layer({'name':'Temporary layer '+str(i),'kind':'graphic','path':str(path),'width':256})
 model.geometry(model.selected)
model.place(model.selected,0,256,20)
assert (model.profile['layers'][model.selected]['x'],model.profile['layers'][model.selected]['y'])==(20,20)
model.place(model.selected,3,256,20)
assert (model.profile['layers'][model.selected]['x'],model.profile['layers'][model.selected]['y'])==(1644,804)
model.set_layer(model.selected,'visible',False)
model.move_layer(model.selected,-1)
assert not model.profile['layers'][model.selected]['visible']
model.save()
loaded=Model(Path(sys.argv[1]))
assert loaded.profile==model.profile
model.remove_layer(model.selected)
model.save()
assert len(model.profile['layers'])==3
assert all(p.is_file() for p in files)
print('PNG/JPG/GIF, corners, hidden, ordering and roundtrip OK')
'''
        examples=Path('/usr/share/doc/trama/examples/assets')
        result=self.python(code,self.path,examples/'overlay.png',jpeg,examples/'idle.gif')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('roundtrip OK',result.stdout)

    def test_missing_gif_reports_the_field_without_starting_recording(self):
        self.profile['layers'][0]['idle']=str(self.base/'missing.gif')
        result=self.check_profile()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('layers[1].idle',result.stderr)
        self.assertIn('missing.gif',result.stderr)
        self.assertFalse((self.base/'recordings').exists())

    def test_invalid_gif_is_rejected_even_when_hidden(self):
        bad=self.base/'invalid.gif';bad.write_bytes(b'not an image')
        self.profile['layers'][0].update(idle=str(bad),visible=False)
        result=self.check_profile()
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.base/'recordings').exists())

    def test_missing_explicit_microphone_uses_real_device_validation(self):
        self.profile['recording']['microphone']='test-microphone-that-is-gone'
        save_profile(self.profile,self.path)
        code='''from compositor import validate
from compositor_profile import load_profile
from compositor_devices import Devices
class TestDevices(Devices):
 def capabilities(self): pass
 def screens(self): return {'TEST-DISPLAY':(1920,1080)}
 def audio(self): return {'default_output':'Test game audio'},{}
validate(load_profile(sys.argv[1]),TestDevices())
'''
        result=self.python(code,self.path)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('recording.microphone',result.stderr)
        self.assertIn('test-microphone-that-is-gone',result.stderr)
        self.assertFalse((self.base/'recordings').exists())


if __name__=='__main__': unittest.main()
