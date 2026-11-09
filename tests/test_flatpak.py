#!/usr/bin/env python3
"""Local recipe checks; not evidence of a sandbox build or GPU capture."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import hashlib
import shutil
import struct
import os
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('adapt', ROOT/'packaging/flatpak/adapt-app-id.py')
adapt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapt)

class RecipeTests(unittest.TestCase):
    def test_recipe_scope_and_integrity(self):
        manifest = json.loads((ROOT/'packaging/flatpak/io.github.xoloitzcuintle95.Trama.json').read_text())
        self.assertEqual(manifest['app-id'], adapt.NEW)
        self.assertFalse(manifest['build-options']['strip'])
        self.assertTrue(manifest['build-options']['no-debuginfo'])
        self.assertNotIn('--socket=x11', manifest['finish-args'])
        self.assertNotIn('--share=network', manifest['finish-args'])
        self.assertEqual([m['name'] for m in manifest['modules']],
                         ['libdrm-static','kms-server-proxy','gpu-screen-recorder','trama'])
        proxy = manifest['modules'][1]
        self.assertEqual(proxy['sources'], [{'type':'file','path':'launch-kms.sh'}])
        self.assertEqual(proxy['build-commands'], ['install -Dm755 launch-kms.sh /app/bin/kms-server-proxy'])
        engine = manifest['modules'][2]
        self.assertIn('f97d1e3', engine['sources'][0]['url'])
        self.assertIn('-Dcapabilities=false', engine['build-commands'][1])
        self.assertIn('--require-match', engine['build-commands'][0])
        helper = next(c for c in engine['build-commands'] if c.startswith('gcc kms/server/'))
        self.assertIn('-static', helper.split())
        self.assertIn('-fno-link-libatomic', helper.split())
        for module in manifest['modules']:
            for source in module['sources']:
                if source['type'] == 'archive':
                    self.assertEqual(len(source['sha512']),128)
                if source['type'] == 'git':
                    self.assertEqual(len(source['commit']),40)

    def test_generated_snapshot_is_self_contained(self):
        folder = ROOT/'build/flatpak-input-v3'
        if not folder.exists():
            self.skipTest('run source preparation first')
        manifest = json.loads((folder/'io.github.xoloitzcuintle95.Trama.json').read_text())
        for module in manifest['modules']:
            for source in module['sources']:
                if 'path' in source:
                    self.assertTrue((folder/source['path']).exists())
        stage = folder/'trama-source'
        self.assertFalse((stage/'.git').exists())
        self.assertFalse((stage/'build').exists())
        self.assertFalse((stage/'perfil.toml').exists())
        config = (stage/'rust/.cargo/config.toml').read_text()
        self.assertIn('directory = "vendor"', config)
        result = subprocess.run(['cargo','metadata','--offline','--locked','--format-version','1'],
                                cwd=stage/'rust',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        metadata = json.loads(result.stdout)
        self.assertGreater(len(metadata['packages']),1)
        for package in metadata['packages']:
            self.assertTrue(Path(package['manifest_path']).is_relative_to(stage))

    def test_fixed_paths_are_retargeted_without_pipeline_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = ROOT/'third_party/gpu-screen-recorder/kms/client/kms_client.c'
            if not source.exists():
                self.skipTest('optional upstream checkout absent')
            original = source.read_text()
            (root/'client.c').write_text(original)
            self.assertEqual(adapt.adapt(root), ['client.c'])
            patched = (root/'client.c').read_text()
            self.assertIn(f'/var/lib/flatpak/app/{adapt.NEW}/', patched)
            self.assertEqual(patched.replace(adapt.NEW, adapt.OLD),original)
            self.assertEqual(adapt.adapt(root), [])

    def test_icon_derivative_dimensions_and_original_preserved(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('ffmpeg unavailable')
        spec = importlib.util.spec_from_file_location('build_icon', ROOT/'packaging/flatpak/build_icon.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = ROOT/'assets/brand/icon.png'
        before = hashlib.sha256(source.read_bytes()).digest()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)/'icons/trama.png'
            module.install_icon(source, destination)
            self.assertEqual(struct.unpack('>II', destination.read_bytes()[16:24]), (512,512))
            self.assertEqual(destination.stat().st_mode & 0o777, 0o644)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def run_launcher(self, arguments):
        # Replace the fixed pkexec executable ONLY in a temporary test copy.
        # Neither Polkit nor a privileged helper is ever executed by this test.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stub = root/'pkexec-stub'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TRAMA_ARGS"\nexit 23\n')
            stub.chmod(0o755)
            launcher = root/'launcher'
            launcher.write_text((ROOT/'packaging/flatpak/launch-kms.sh').read_text().replace(
                '/usr/bin/pkexec', str(stub)))
            output = root/'arguments'
            env = dict(os.environ, TRAMA_ARGS=str(output))
            result = subprocess.run(['/bin/sh',str(launcher),*arguments],env=env,
                                    capture_output=True,text=True)
            return result, output.read_text().splitlines() if output.exists() else []

    def test_launcher_fixed_target_and_literal_arguments(self):
        socket = '/tmp/socket ; $HOME with spaces'
        result, arguments = self.run_launcher([socket, '/dev/dri/card12', '/unused/home'])
        self.assertEqual(result.returncode,23)
        self.assertEqual(arguments, [
            '/var/lib/flatpak/app/io.github.xoloitzcuintle95.Trama/current/active/files/bin/gsr-kms-server',
            socket, '/dev/dri/card12'])
        text = (ROOT/'packaging/flatpak/launch-kms.sh').read_text()
        self.assertNotIn('setcap', text)
        self.assertNotIn('setup-gsr-ui', text)
        self.assertNotIn('eval ', text)

    def test_launcher_rejects_invalid_inputs_before_authorization(self):
        cases = [[], ['/tmp/socket','/dev/dri/card0'],
                 ['relative','/dev/dri/card0','home'],
                 ['/'+'a'*107,'/dev/dri/card0','home'],
                 ['/tmp/socket','/etc/shadow','home'],
                 ['/tmp/socket','/dev/dri/card','home'],
                 ['/tmp/socket','/dev/dri/card0/../../etc/shadow','home'],
                 ['/tmp/socket','/dev/dri/card0;echo','home']]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result, called = self.run_launcher(arguments)
                self.assertEqual(result.returncode,2)
                self.assertEqual(called,[])

    def test_unknown_upstream_layout_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(['python3', str(ROOT/'packaging/flatpak/adapt-app-id.py'),
                                     '--require-match'], cwd=temporary,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('review', result.stderr)

if __name__ == '__main__':
    unittest.main()
