"""Language selection, explicit UI strings and on-disk preference isolation."""
import ast
import copy
import locale
import os
from pathlib import Path
import string
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import trama_i18n as i18n
from trama_model import Model
from trama_tui import App, main
from compositor_profile import load_profile, save_profile
from test_trama_view import Screen


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.base=Path(self.tmp.name)
        self.old=i18n.preference()
        self.old_language=i18n.language()
        i18n.select_language('es')
    def tearDown(self):
        i18n.select_language(self.old,{'LANG':self.old_language})
        self.tmp.cleanup()

    def app(self,width=80,height=24):
        profile=load_profile(ROOT/'examples/perfil.toml')
        profile['recording']['screen']='Monitor Español'
        profile['layers'][0]['name']='Micrófono'
        path=self.base/'profile.toml';save_profile(profile,path)
        model=Model(path,self.base/'session.json')
        model.screens={'Monitor Español':(1920,1080)}
        screen=Screen(width,height)
        return App(screen,model,None),screen

    def test_detection_precedence_and_unsupported_fallback(self):
        for env,expected in [({},'en'),({'LANG':'es_MX.UTF-8'},'es'),
                             ({'LANG':'ES-es'},'es'),({'LANG':'es@euro'},'es'),({'LANG':'en_GB.UTF-8'},'en'),
                             ({'LANG':'fr_FR.UTF-8'},'en'),({'LANG':'C'},'en'),
                             ({'LANG':'es_MX','LC_MESSAGES':'de_DE'},'en'),
                             ({'LANG':'en_US','LC_MESSAGES':'en_US','LC_ALL':'es_ES'},'es'),
                             ({'LC_ALL':'','LC_MESSAGES':'','LANG':'es'},'es')]:
            self.assertEqual(i18n.detect_language(env),expected)
        i18n.select_language('en',{'LANG':'es'})
        self.assertEqual(i18n.language(),'en')

    def test_preference_roundtrip_and_invalid_config(self):
        target=self.base/'settings/ui.toml'
        self.assertEqual(i18n.read_preference(target),'auto')
        for value in ('en','es','auto'):
            i18n.save_preference(value,target)
            self.assertEqual(i18n.read_preference(target),value)
        for contents in ('broken [', 'language = "fr"', 'language = ["en"]'):
            target.write_text(contents)
            self.assertEqual(i18n.read_preference(target),'auto')
        with self.assertRaises(ValueError): i18n.save_preference('fr',target)
        self.assertEqual(len(list(target.parent.iterdir())),1)

    def test_cli_override_does_not_write_preference_or_touch_profile(self):
        config=self.base/'config';i18n.save_preference('es',config/'trama/ui.toml')
        app,_=self.app();before=app.model.path.read_bytes()
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(config),'LANG':'fr_FR.UTF-8'},clear=True):
            with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True), \
                 patch('trama_tui.locale.setlocale',side_effect=locale.Error('not installed')),patch('trama_tui.Devices'), \
                 patch('trama_tui.curses.wrapper') as wrapper:
                self.assertEqual(main([str(app.model.path),'--lang','en']),0)
                self.assertEqual(i18n.language(),'en')
                wrapper.assert_called_once()
            self.assertEqual(i18n.read_preference(),'es')
        self.assertEqual(app.model.path.read_bytes(),before)

    def test_language_menu_persists_and_does_not_dirty_scene(self):
        app,screen=self.app();original=copy.deepcopy(app.model.profile)
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.base/'config')}), \
             patch.object(app,'menu',return_value='en'):
            app.dispatch('L')
            self.assertEqual(i18n.read_preference(),'en')
            app.home()
            self.assertIn('RECORD',screen.text())
            self.assertIn('Language saved.',screen.text())
        self.assertEqual(app.model.profile,original)
        self.assertFalse(app.model.dirty)
        with patch.object(app,'menu',return_value=None): app.choose_language()
        self.assertEqual(i18n.language(),'en')

    def test_english_layout_and_user_names_are_not_translated(self):
        i18n.select_language('en')
        for width,height in ((72,20),(80,24),(110,30)):
            app,screen=self.app(width,height)
            for section in ('overview','layers','capture','audio','output'):
                app.focus=section;app.home()
                self.assertNotIn('GRABAR',screen.text())
                self.assertIn('Help',screen.text())
            app.focus='layers';app.home()
            self.assertIn('Micrófono',screen.text())  # user layer name
            self.assertIn('PROPERTIES',screen.text())
            app.focus='capture';app.home()
            self.assertIn('Monitor Español',screen.text())  # real display name
            app.active=True;app.started=1;app.seconds=30;app.home()
            self.assertIn('RECORDING',screen.text())
            self.assertIn('Automatic stop: 30 s',screen.text())

    def test_help_is_translated_and_each_action_has_its_own_entry(self):
        app,_=self.app();i18n.select_language('en')
        with patch.object(app,'details') as details: app.help()
        title,lines=details.call_args.args
        self.assertEqual(title,'Help')
        self.assertIn('r             Record until stopped manually',lines)
        self.assertIn('L             Language / Idioma',lines)
        self.assertNotIn('NAVEGACIÓN',lines)

    def test_catalogue_coverage_and_format_placeholders(self):
        formatter=string.Formatter()
        for original,english in i18n.EN.items():
            fields=lambda s: sorted((key,spec,conversion) for _,key,spec,conversion in formatter.parse(s) if key is not None)
            self.assertEqual(fields(original),fields(english),original)
        for name in ('trama_tui.py','trama_view.py'):
            tree=ast.parse((ROOT/'scripts'/name).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tr' and node.args and isinstance(node.args[0],ast.Constant):
                    self.assertIn(node.args[0].value,i18n.EN)

    def test_help_flag_uses_requested_language_without_tty(self):
        for language,expected in [('en','Interface language'),('es','Idioma de la interfaz')]:
            result=subprocess.run([str(ROOT/'trama'),'--lang',language,'--help'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(expected,result.stdout)


if __name__=='__main__': unittest.main()
