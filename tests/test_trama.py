"""TUI state and shared capture lifecycle. No real monitor/audio is captured."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from compositor_profile import new_profile, save_profile, load_profile
from trama_model import Model, corner_position, initial_path, remember, browser_entries
from trama_tui import App


class TramaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.png=self.base/"wide image.png"
        Image.new("RGBA",(200,100),(40,80,120,128)).save(self.png)
        profile=new_profile(self.base)
        profile["recording"]["screen"]="TEST-DISPLAY"
        profile["layers"]=[{"name":"Graphic","kind":"graphic","path":str(self.png),"width":300}]
        self.path=self.base/"profile.toml"
        save_profile(profile,self.path)
        self.model=Model(self.path,self.base/"state.json")
        self.model.screens={"TEST-DISPLAY":(1920,1080)}
    def tearDown(self): self.temp.cleanup()

    def test_trama_launcher_and_unchanged_session_storage(self):
        from trama_model import session_path
        self.assertTrue((ROOT/'trama').is_file())
        self.assertFalse((ROOT/'xolo').exists())
        with patch.dict(os.environ,{'XDG_STATE_HOME':str(self.base)}):
            self.assertEqual(session_path(),self.base/'xolo/session.json')

    def test_effective_aspect_and_all_corners_use_rust_loader(self):
        expected=[(20,20),(1600,20),(20,910),(1600,910)]
        for corner,xy in enumerate(expected):
            geometry=self.model.place(0,corner,300,20)
            layer=self.model.profile["layers"][0]
            self.assertEqual((layer["x"],layer["y"]),xy)
            self.assertEqual((geometry["width"],geometry["height"]),(300,150))
            self.assertEqual(self.model.placement_hint(0),(corner,300,20))
        self.assertTrue(self.model.dirty)

    def test_avatar_and_existing_profile_stay_compatible(self):
        original=ROOT/"examples/perfil.toml"
        before=hashlib.sha256(original.read_bytes()).hexdigest()
        profile=load_profile(original)
        profile["recording"]["screen"] = profile["recording"]["screen"] or "TEST-DISPLAY"
        target=self.base/"user-copy.toml"
        save_profile(profile,target)
        model=Model(target,self.base/"last.json")
        model.screens={model.profile["recording"]["screen"]:(1920,1080)}
        index=next(i for i,l in enumerate(model.profile["layers"]) if l["kind"]=="avatar")
        model.place(index,0,300)
        self.assertEqual((model.profile["layers"][index]["x"],model.profile["layers"][index]["y"]),(20,20))
        model.place(index,3,300)
        self.assertEqual((model.profile["layers"][index]["x"],model.profile["layers"][index]["y"]),(1600,760))
        model.save()
        self.assertFalse(model.dirty)
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),before)
        self.assertEqual(load_profile(target)["schema_version"],2)

    def test_folder_and_filename_are_separate_and_roundtrip_old_output(self):
        folder=self.base/"videos with spaces"
        self.model.set_folder(folder)
        self.model.set_name("minecraft-{timestamp}.mkv")
        self.assertEqual(self.model.output_folder,folder)
        self.assertEqual(self.model.output_name,"minecraft-{timestamp}.mkv")
        self.model.save()
        loaded=load_profile(self.path)
        self.assertEqual(loaded["recording"]["output"],str(folder/"minecraft-{timestamp}.mkv"))
        self.assertNotIn("folder",loaded["recording"])
        self.assertNotIn("filename",loaded["recording"])
        with self.assertRaises(ValueError): self.model.set_name("other/video.mkv")
        with self.assertRaises(ValueError): self.model.set_name("video.mp4")
        with self.assertRaises(ValueError): self.model.set_folder("{timestamp}/videos")

    def test_edit_one_field_hide_order_remove_and_clear_dimension(self):
        before=copy.deepcopy(self.model.profile)
        self.model.set_layer(0,"x",70)
        expected=copy.deepcopy(before); expected["layers"][0]["x"]=70
        self.assertEqual(self.model.profile,expected)
        self.model.set_layer(0,"height",200)
        self.model.set_layer(0,"height",None)
        self.assertNotIn("height",self.model.profile["layers"][0])
        self.model.add_layer({"name":"Other","path":str(self.png)})
        self.model.set_layer(1,"visible",False)
        self.model.move_layer(1,-1)
        self.assertEqual(self.model.profile["layers"][0]["name"],"Other")
        self.assertFalse(self.model.profile["layers"][0]["visible"])
        self.model.remove_layer(0)
        self.assertEqual(self.model.profile["layers"][0]["name"],"Graphic")

    def test_missing_file_rejects_change_and_error_stays_by_field(self):
        app=App(None,self.model,None)
        before=copy.deepcopy(self.model.profile)
        def bad():
            self.model.set_layer(0,"path",str(self.base/"missing.gif"))
            self.model.geometry(0)
        self.assertFalse(app.attempt("layer.path",bad))
        self.assertEqual(self.model.profile,before)
        self.assertIn("layer.path",self.model.errors)
        self.assertFalse(self.model.dirty)

    def test_too_large_position_missing_screen_and_fractional_bounds(self):
        with self.assertRaisesRegex(ValueError,"no cabe"): self.model.place(0,3,4000)
        self.model.screens={}
        with self.assertRaisesRegex(ValueError,"Pantalla"): self.model.place(0,0,300)
        self.assertEqual(corner_position((1920,1080),(300,150.5),3,20),(1600,909))

    def test_last_profile_and_save_as_keep_real_asset_targets(self):
        remember(self.path,self.base/"state.json")
        self.assertEqual(initial_path(state_file=self.base/"state.json"),self.path)
        self.assertEqual(initial_path(self.base/"explicit.toml",state_file=self.base/"state.json"),self.base/"explicit.toml")
        output=self.model.profile["recording"]["output"]
        self.model.save(self.base/"profiles/new.toml")
        self.assertEqual(self.model.profile["recording"]["output"],output)
        self.assertEqual(self.model.profile["layers"][0]["path"],str(self.png))
        self.assertFalse(self.model.dirty)
        self.assertEqual(self.model.profile["_base"],self.base/"profiles")

    def test_browser_and_unsaved_exit(self):
        (self.base/"folder").mkdir()
        (self.base/"not-image.txt").write_text("x")
        entries=browser_entries(self.base,{".png"})
        self.assertTrue(entries[0].is_dir())
        self.assertIn(self.png,entries)
        self.assertNotIn(self.base/"not-image.txt",entries)
        app=App(None,self.model,None)
        self.model.set_layer(0,"x",42)
        with patch.object(app,"menu",return_value="cancel"):
            self.assertFalse(app.may_discard())
        with patch.object(app,"menu",return_value="discard"):
            self.assertTrue(app.may_discard())
        with patch.object(app,"menu",return_value="save"):
            self.assertTrue(app.may_discard())
        self.assertFalse(self.model.dirty)

    def test_first_run_wizard_uses_one_avatar_and_can_save_without_recording(self):
        app=App(None,self.model,None)
        with patch.object(app,"choose_screen",return_value=True), patch.object(app,"choose_mic",return_value=True), \
             patch.object(app,"browse",side_effect=[ROOT/"examples/assets/idle.gif",ROOT/"examples/assets/talking.gif"]), \
             patch.object(app,"menu",side_effect=[0,"save"]):
            app.wizard()
        loaded=load_profile(self.path)
        avatar=next(layer for layer in loaded["layers"] if layer["kind"]=="avatar")
        self.assertEqual((avatar["x"],avatar["y"]),(20,20))
        self.assertFalse(self.model.dirty)

    def test_field_editor_clears_only_requested_dimension(self):
        app=App(None,self.model,None)
        before=copy.deepcopy(self.model.profile)
        with patch.object(app,"menu",side_effect=["width",None]), patch.object(app,"text",return_value="-"):
            app.edit_layer()
        expected=copy.deepcopy(before); expected["layers"][0].pop("width")
        self.assertEqual(self.model.profile,expected)


if __name__=="__main__": unittest.main()
