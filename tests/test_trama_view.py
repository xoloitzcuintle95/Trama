"""Layout/navigation and repaint policy: no graphics or capture devices."""
import curses
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compositor_profile import load_profile,save_profile
from trama_model import Model
from trama_tui import App
from trama_view import clipped


class Screen:
    def __init__(self,width=110,height=30):
        self.width,self.height=width,height
        self.refreshes=0
        self.waits=[]
        self.rows=[]
        self.erase()
        self.input=lambda:None
    def getmaxyx(self): return self.height,self.width
    def erase(self): self.rows=[[' ']*self.width for _ in range(self.height)]
    def addstr(self,y,x,text,attr=0):
        if not 0<=y<self.height or x+len(text)>=self.width:
            raise AssertionError((y,x,text))
        self.rows[y][x:x+len(text)]=list(text)
    def refresh(self): self.refreshes+=1
    def text(self): return '\n'.join(''.join(row) for row in self.rows)
    def keypad(self,enabled): pass
    def timeout(self,milliseconds): self.waits.append(milliseconds)
    def get_wch(self): return self.input()


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.base=Path(self.tmp.name)
        profile=load_profile(ROOT/'examples/perfil.toml')
        profile['recording']['screen']='TEST-DISPLAY'
        self.path=self.base/'profile.toml';save_profile(profile,self.path)
        self.model=Model(self.path,self.base/'session.json')
        self.model.screens={'TEST-DISPLAY':(1920,1080)}
        self.screen=Screen()
        self.app=App(self.screen,self.model,None)
    def tearDown(self): self.tmp.cleanup()

    def test_sections_and_contextual_footer_at_all_sizes(self):
        for width,height in ((110,30),(80,24),(72,20),(160,40)):
            screen=Screen(width,height);app=App(screen,self.model,None)
            for focus in ('overview','layers','capture','audio','output'):
                app.focus=focus;app.home();text=screen.text()
                for label in ('TRAMA','Overview','Layers','Capture','Audio','Output'):
                    self.assertIn(label,text)
                self.assertIn('Tab Sección',text)
                self.assertIn('Ayuda',text)
                self.assertEqual('PROPIEDADES' in text,focus=='layers')
                if focus=='overview': self.assertIn('GRABAR',text)
            app.focus='overview';app.dispatch('\t')
            self.assertEqual(app.focus,'layers')

    def test_enter_routes_each_section_to_existing_actions(self):
        for focus,row,key in (('overview',0,'r'),('overview',1,'t'),('overview',2,'s'),
                              ('capture',0,'p'),('capture',1,'f'),
                              ('audio',0,'m'),('audio',1,'g'),
                              ('output',0,'d'),('output',1,'n')):
            self.app.focus,self.app.row=focus,row
            with patch.object(self.app,'dispatch') as dispatch:
                self.app.activate()
            dispatch.assert_called_once_with(key)
        self.app.focus='layers'
        with patch.object(self.app,'edit_layer') as edit:
            self.app.activate()
        edit.assert_called_once()

    def test_status_badges_do_not_claim_validation(self):
        self.app.home();self.assertIn('CONFIGURACIÓN INCOMPLETA',self.screen.text())
        self.app.discovered=True;self.app.home();self.assertIn('LISTO',self.screen.text())
        self.model.errors['screen']='Monitor ausente'
        self.app.focus='capture';self.app.home()
        self.assertIn('ERROR',self.screen.text());self.assertIn('Monitor ausente',self.screen.text())

    def test_focus_enter_and_more_actions_keep_existing_routes(self):
        self.app.focus='output';self.app.row=1
        with patch.object(self.app,'text',return_value='daily-{timestamp}.mkv'):
            self.app.dispatch('\n')
        self.assertEqual(self.model.output_name,'daily-{timestamp}.mkv')
        with patch.object(self.app,'menu',return_value='h'):
            self.app.focus='layers';self.app.dispatch(' ')
        self.assertFalse(self.model.profile['layers'][0]['visible'])
        self.app.dispatch(curses.KEY_BTAB)
        self.assertEqual(self.app.focus,'overview')

    def test_static_recording_view_does_not_render_edit_panels(self):
        self.app.active=True;self.app.started=1
        self.app.pending_output=self.base/'recording.mkv';self.app.seconds=30
        self.app.home();text=self.screen.text()
        self.assertIn('GRABANDO',text)
        self.assertIn('Parada automática: 30 s',text)
        self.assertIn('recording.mkv',text)
        self.assertNotIn('PROPIEDADES',text)
        self.assertNotIn('CAPAS',text)
        self.app.dispatch('x');self.app.home()
        self.assertIn('CERRANDO',self.screen.text())
        self.assertTrue(self.app.stop_event.is_set())

    def test_idle_event_loop_only_paints_on_change(self):
        count=0
        def input_key():
            nonlocal count
            count+=1
            return 'q' if count==60 else None
        self.screen.input=input_key
        with patch.object(self.app,'discover'),patch.object(self.app,'remember_profile'), \
             patch.object(self.app.view,'setup'),patch('curses.curs_set'):
            self.app.run()
        self.assertEqual(self.screen.refreshes,1)
        self.assertEqual(count,60)

    def test_recording_loop_waits_and_repaints_only_state_transitions(self):
        self.app.active=True;self.app.started=1;self.app.pending_output=self.base/'test.mkv'
        count=0
        def input_key():
            nonlocal count
            count+=1
            if count==20: return 'x'
            if count==40: self.app.events.put(('done',{'output':str(self.base/'test.mkv')}))
            if count==60: return 'q'
            return None
        self.screen.input=input_key
        with patch.object(self.app,'discover'),patch.object(self.app,'remember_profile'), \
             patch.object(self.app.view,'setup'),patch('curses.curs_set'):
            self.app.run()
        self.assertEqual(self.screen.refreshes,3)  # recording, closing, dashboard
        self.assertIn(1000,self.screen.waits)
        self.assertFalse(self.app.active)
        self.assertTrue(self.model.last_success)

    def test_unicode_clip_and_small_terminal(self):
        self.assertEqual(clipped('AB界C',4),'AB界')
        self.assertEqual(clipped('A\nB',3),'A B')
        screen=Screen(60,15);app=App(screen,self.model,None);app.home()
        self.assertIn('amplía',screen.text())


if __name__=='__main__': unittest.main()
