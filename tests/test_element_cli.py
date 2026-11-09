"""Real CLI/preflight tests, without opening the capture device."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class ElementCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.png = Path(cls.temporary.name) / "image with spaces.png"
        Image.new("RGBA", (12,10), (40,80,120,128)).save(cls.png)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_check(self, *flags, environment=None, media=None):
        env = {k:v for k,v in os.environ.items() if not k.startswith("GSR_OVERLAY_")}
        env.update(environment or {})
        return subprocess.run([sys.executable,str(ROOT/"scripts/record-element.py"),
            "--media",str(media or self.png),"--check",*flags],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)

    def checked(self, *flags, **kwargs):
        result = self.run_check(*flags,**kwargs)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_defaults_and_no_capture(self):
        before = set((ROOT/"build/recordings-element").glob("*"))
        values = self.checked()
        self.assertEqual((values["x"],values["y"],values["width"]),(32,32,320))
        self.assertAlmostEqual(values["height"],320*10/12,places=3)
        self.assertTrue(values["visible"] and values["keep_aspect"])
        self.assertEqual(before,set((ROOT/"build/recordings-element").glob("*")))

    def test_dimensions_contain_and_stretch(self):
        for flags in [("--height","20"),("--width","24","--height","30")]:
            values = self.checked(*flags)
            self.assertEqual((values["width"],values["height"]),(24,20))
        values = self.checked("--width","24","--height","10","--stretch")
        self.assertEqual((values["width"],values["height"]),(24,10))
        self.assertFalse(values["keep_aspect"])

    def test_visibility_position_and_precedence(self):
        self.assertFalse(self.checked("--hidden")["visible"])
        values = self.checked("--visible","--x","-4",environment={
            "GSR_OVERLAY_VISIBLE":"false","GSR_OVERLAY_Y":"15","GSR_OVERLAY_WIDTH":"12"})
        self.assertTrue(values["visible"])
        self.assertEqual((values["x"],values["y"],values["width"],values["height"]),(-4,15,12,10))

    def test_invalid_and_unsupported_rejected_even_when_hidden(self):
        for flags in [("--height","0"),("--width","20","--stretch"),("--x","-20000")]:
            self.assertEqual(self.run_check(*flags).returncode,2)
        jpg = Path(self.temporary.name)/"unsupported.bmp"
        Image.new("RGB",(12,10),"red").save(jpg)
        self.assertEqual(self.run_check("--hidden",media=jpg).returncode,2)

    def test_c_reference_comparison_rejects_unequal_layout(self):
        env = {k:v for k,v in os.environ.items() if not k.startswith("GSR_OVERLAY_")}
        env["GSR_OVERLAY_HEIGHT"] = "200"
        result = subprocess.run([sys.executable,str(ROOT/"scripts/measure-gif.py"),"--workload","test"],
                                cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertIn("referencia C solo admite",result.stderr)


if __name__ == "__main__":
    unittest.main()
