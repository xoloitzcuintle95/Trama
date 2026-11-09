"""Profile/menu/preflight/runner tests. Devices and capture are explicitly simulated."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import compositor as cli
from compositor_profile import new_profile, normalize, save_profile, load_profile
from compositor_devices import Devices


class FakeDevices:
    gsr = "/usr/local/bin/gpu-screen-recorder"
    def capabilities(self):
        pass
    def screens(self):
        return {"TEST-DISPLAY":(1920,1080)}
    def audio(self):
        return {"default_output":"Game","test.mic":"USB mic"},{"test.mic":"USB mic"}
    def resolve_mic(self,selected,audio=None):
        if selected=="default_input":
            return "test.mic"
        if selected not in self.audio()[1]:
            raise ValueError(f"recording.microphone: {selected} no está disponible")
        return selected


class CompositorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.media = self.base/"imagen á🚀.png"
        Image.new("RGBA",(12,10),(120,80,40,128)).save(self.media)
        self.profile = new_profile(self.base)
        self.profile["recording"]["screen"] = "TEST-DISPLAY"
        self.profile["layers"] = [{"name":"Gráfico","path":str(self.media),"width":24}]
        self.profile = normalize(self.profile,self.base)
    def tearDown(self):
        self.tmp.cleanup()
    def prepared(self,profile=None):
        with patch.object(cli,"probe_microphone") as probe:
            result = cli.validate(profile or self.profile,FakeDevices())
            if result["manifest"]["microphone"]:
                probe.assert_called_once_with("test.mic")
            return result

    def test_toml_save_reload_and_relative_paths(self):
        profile = self.base/"profiles/config.toml"
        original = copy.deepcopy(self.profile)
        saved = save_profile(self.profile,profile)
        self.assertEqual(load_profile(profile),saved)
        self.assertEqual(self.profile,original)
        self.assertIn('../imagen á🚀.png',profile.read_text())
        self.assertEqual(saved["_base"],profile.parent)
        result = self.prepared(saved)
        self.assertEqual(result["effective"]["layers"][0]["height"],20)
        self.assertEqual(result["manifest"]["microphone"],"test.mic")
        command = cli.recording_command(result)
        self.assertEqual(command[command.index("-w")+1],"TEST-DISPLAY")
        self.assertEqual(command[command.index("-a")+1],"default_output|device:test.mic")
        self.assertNotIn("shell",command)

    def test_missing_gif_before_capture(self):
        self.profile["layers"][0]["path"] = str(self.base/"missing.gif")
        with self.assertRaisesRegex(ValueError,r"layers\[1\].path.*missing.gif"):
            self.prepared()
        self.assertFalse((self.base/"recordings").exists())

    def test_missing_explicit_mic_never_falls_back(self):
        self.profile["recording"]["microphone"] = "disconnected.mic"
        with self.assertRaisesRegex(ValueError,"recording.microphone.*disconnected.mic"):
            self.prepared()
        devices = Devices()
        with patch.object(devices,"audio",return_value=FakeDevices().audio()):
            with self.assertRaisesRegex(ValueError,"no está disponible"):
                devices.resolve_mic("disconnected.mic")

    def test_v1_and_strict_invalid_values(self):
        old = self.base/"old.toml"
        old.write_text('schema_version = 1\n[element]\nmedia = "imagen á🚀.png"\nx = 10\nwidth = 40\nvisible = false\n')
        loaded = load_profile(old)
        self.assertEqual(loaded["schema_version"],2)
        self.assertEqual(loaded["layers"][0]["path"],str(self.media))
        self.assertFalse(loaded["layers"][0]["visible"])
        for change in ({"width":0},{"visible":"false"},{"kind":"text"},{"keep_aspect":False}):
            invalid = copy.deepcopy(self.profile)
            invalid["layers"][0].update(change)
            with self.assertRaises(ValueError):
                normalize(invalid,self.base)

    def test_avatar_limits_and_real_asset_preload(self):
        self.profile["layers"] = [{"kind":"avatar","name":"Avatar","idle":str(ROOT/"examples/assets/idle.gif"),
                                   "talking":str(ROOT/"examples/assets/talking.gif"),"x":1600,"y":760,"width":300,"threshold":0.05,"release_ms":200}]
        prepared = self.prepared()
        self.assertEqual(prepared["effective"]["rgba_bytes"],524288)
        self.assertTrue(prepared["effective"]["layers"][0]["avatar"])
        self.profile["layers"][0]["threshold"] = 0
        with self.assertRaisesRegex(ValueError,"threshold"):
            self.prepared()

    def test_interactive_edit_order_hide_save_load(self):
        path = self.base/"menu.toml"
        # Add second graphic, reorder it, hide first, save, reload, exit.
        answers = ["4","a",str(self.media),"Superior","4","5","24","-","s","s",
                   "r","2","1","o","1","0","5",str(path),"6",str(path),"0"]
        with patch("builtins.input",side_effect=answers), patch("sys.stdout",new=io.StringIO()):
            cli.edit(copy.deepcopy(self.profile),None,FakeDevices())
        loaded = load_profile(path)
        self.assertEqual([x["name"] for x in loaded["layers"]],["Superior","Gráfico"])
        self.assertFalse(loaded["layers"][0]["visible"])
        self.assertEqual(loaded["layers"][0]["x"],4)

    def test_record_runner_simulated_gsr_real_container(self):
        # This is NOT a screen/GSR integration test. It exercises process control,
        # output, log, probe and profile round-trip with a synthetic capture child.
        path = self.base/"capture.toml"
        save_profile(self.profile,path)
        prepared = self.prepared(load_profile(path))
        child = self.base/"fake-gsr"
        child.write_text('''#!/usr/bin/env python3
import signal,subprocess,sys,time
running=True
def stop(*args):
 global running
 running=False
signal.signal(signal.SIGINT,stop)
output=sys.argv[sys.argv.index('-o')+1]
print('loaded plugin: test, name: rust-media-overlay, version: 4',flush=True)
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=64x48:r=30','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','0.4','-c:v','libx264','-c:a','aac',output],check=True)
while running:
 time.sleep(0.02)
print('unloaded plugin: rust-media-overlay',flush=True)
''')
        child.chmod(0o700)
        prepared["gsr"] = str(child)
        with patch("sys.stdout",new=io.StringIO()):
            result = cli.record(prepared,1)
        self.assertTrue(result["completed"])
        self.assertTrue(Path(str(prepared["output"])+".report.json").is_file())
        self.assertEqual({s["codec_type"] for s in result["video"]["streams"]},{"video","audio"})
        with self.assertRaises(ValueError):
            cli.record(prepared,1)

    def test_assets_only_cli_missing_file(self):
        self.profile["layers"][0]["path"] = str(self.base/"missing.gif")
        path = self.base/"bad.toml"
        save_profile(self.profile,path)
        result = subprocess.run([sys.executable,str(ROOT/"scripts/compositor.py"),"check",str(path),"--assets-only"],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn("layers[1].path",result.stderr)

    def test_real_device_protocol_parsing_and_capability_rejection(self):
        devices = Devices()
        with patch("compositor_devices.run",return_value="window\nTEST-DISPLAY|1920x1080\nregion\n/dev/video0|640x480@30hz|nv12\nportal\n"):
            self.assertEqual(devices.screens(),{"TEST-DISPLAY":(1920,1080)})
        with patch("compositor_devices.run",return_value="section=video_codecs\nh264_software\nsection=containers\nmkv\n"):
            with self.assertRaisesRegex(ValueError,"H.264 GPU"):
                devices.capabilities()
        sources = [{"name":"test.mic","description":"USB mic","monitor_of_sink":None},
                   {"name":"test.monitor","description":"Game","monitor_of_sink":0}]
        with patch("compositor_devices.run",side_effect=["default_input|Default\ntest.mic|USB mic\ntest.monitor|Game\n",json.dumps(sources)]):
            audio = devices.audio()
        self.assertEqual(audio[1],{"test.mic":"USB mic"})
        with patch("compositor_devices.run",return_value="test.mic\n"):
            self.assertEqual(devices.resolve_mic("default_input",audio),"test.mic")

    def test_scene_total_budget_rejects_before_capture(self):
        large=self.base/"budget.png"
        Image.new("RGBA",(1280,1280),(40,80,120,255)).save(large)
        self.profile["layers"] = [{"name":f"Image {i}","kind":"graphic","path":str(large)} for i in range(11)]
        with self.assertRaisesRegex(ValueError,"64 MiB"):
            self.prepared()
        self.assertFalse((self.base/"recordings").exists())

    def test_jpg_static_modes_and_malformed_hidden_resource(self):
        jpg = self.base/"foto.jpg"
        self.profile["layers"][0].update(path=str(jpg),visible=False)
        for mode,color in (("RGB","red"),("L",100),("CMYK",(0,100,200,10))):
            Image.new(mode,(12,10),color).save(jpg,progressive=True)
            prepared = self.prepared()
            self.assertFalse(prepared["effective"]["layers"][0]["visible"])
            pixels = subprocess.check_output([str(ROOT/"build/rust-target/release/media-dump"),str(jpg),"0"])
            expected = Image.open(jpg).convert("RGBA").tobytes()
            self.assertLessEqual(max(abs(a-b) for a,b in zip(pixels,expected)),3,mode)
            self.assertEqual(pixels[3::4],bytes([255])*120)
        jpg.write_bytes(b"\xff\xd8bad header")
        with self.assertRaisesRegex(ValueError,"JPG"):
            self.prepared()


if __name__=="__main__":
    unittest.main()
