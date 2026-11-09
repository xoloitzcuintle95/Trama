"""Acceptance through a real pseudo-terminal. Capture/device adapter is simulated."""
import copy
import codecs
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from compositor_profile import load_profile, save_profile

ENGINE='''#!/usr/bin/env python3
import signal,subprocess,sys,time
running=True
def stop(*args):
 global running
 running=False
signal.signal(signal.SIGINT,stop)
started=time.monotonic()
output=sys.argv[sys.argv.index('-o')+1]
print('loaded plugin: test, name: rust-media-overlay, version: 4',flush=True)
while running: time.sleep(0.03)
duration=max(0.2,time.monotonic()-started)
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=64x48:r=30','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',str(duration),'-c:v','libx264','-c:a','aac',output],check=True)
print('unloaded plugin: rust-media-overlay',flush=True)
'''


class Screen:
    """Small VT screen reader for curses' differential output, not raw substrings."""
    def __init__(self):
        self.rows=[[' ']*110 for _ in range(30)]
        self.row=self.col=0
        self.pending=''
        self.decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
    def feed(self,data):
        self.pending+=self.decoder.decode(data)
        i=0
        while i<len(self.pending):
            c=self.pending[i]
            if c=='\x1b':
                rest=self.pending[i:]
                if len(rest)<2: break
                if rest[1]=='[':
                    match=re.match(r'\x1b\[([0-?]*)([ -/]*)([@-~])',rest)
                    if not match: break
                    params=match[1]
                    cmd=match[3]
                    values=[int(x or 0) for x in params.split(';')] if not params.startswith('?') else [0]
                    n=values[0] or 1
                    if cmd in ('H','f'):
                        self.row=max(0,min(29,n-1)); self.col=max(0,min(109,(values[1] if len(values)>1 else 1)-1))
                    elif cmd=='d': self.row=max(0,min(29,n-1))
                    elif cmd=='G': self.col=max(0,min(109,n-1))
                    elif cmd=='A': self.row=max(0,self.row-n)
                    elif cmd=='B': self.row=min(29,self.row+n)
                    elif cmd=='C': self.col=min(109,self.col+n)
                    elif cmd=='D': self.col=max(0,self.col-n)
                    elif cmd=='K':
                        start=0 if values[0] in (1,2) else self.col
                        end=self.col+1 if values[0]==1 else 110
                        self.rows[self.row][start:end]=[' ']*(end-start)
                    elif cmd=='J':
                        if values[0]==2: self.rows=[[' ']*110 for _ in range(30)]
                        else:
                            self.rows[self.row][self.col:]=[' ']*(110-self.col)
                            for row in range(self.row+1,30): self.rows[row]=[' ']*110
                    elif cmd=='X': self.rows[self.row][self.col:min(110,self.col+n)]=[' ']*min(n,110-self.col)
                    i+=len(match[0]); continue
                if rest[1] in ('(',')'):
                    if len(rest)<3: break
                    i+=3; continue
                i+=2; continue
            if c=='\r': self.col=0
            elif c=='\n': self.row=min(29,self.row+1)
            elif c=='\b': self.col=max(0,self.col-1)
            elif c.isprintable():
                self.rows[self.row][self.col]=c; self.col=min(109,self.col+1)
            i+=1
        self.pending=self.pending[i:]
    def text(self): return '\n'.join(''.join(row) for row in self.rows)


class Terminal:
    def __init__(self,profile,base,explicit=True,cwd=None):
        self.master,self.slave=pty.openpty()
        fcntl.ioctl(self.slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,110,0,0))
        self.before=termios.tcgetattr(self.slave)
        env=os.environ.copy()
        engine=base/'fake-gsr'; engine.write_text(ENGINE); engine.chmod(0o700)
        env.update(TERM='xterm-256color',LANG='C.UTF-8',XDG_STATE_HOME=str(base/'state'),XDG_CONFIG_HOME=str(base/'config'),TRAMA_TEST_ENGINE=str(engine),TRAMA_TEST_PROFILE=str(profile))
        command=[sys.executable,str(ROOT/'tests/trama_pty_driver.py')]+([str(profile)] if explicit else [])+['--lang','es']
        self.process=subprocess.Popen(command,
            stdin=self.slave,stdout=self.slave,stderr=self.slave,env=env,start_new_session=True,cwd=cwd or ROOT)
        self.data=b''
        self.screen=Screen()
    def read(self,timeout=0.1):
        if select.select([self.master],[],[],timeout)[0]:
            try:
                data=os.read(self.master,65536)
                self.data+=data; self.screen.feed(data)
            except OSError: pass
    def wait_for(self,text,timeout=8,after=0):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if len(self.data)>after and text in self.screen.text(): return
            self.read()
            if self.process.poll() is not None: break
        raise AssertionError(f'No aparece {text!r}; exit={self.process.poll()}\n'+self.screen.text())
    def send(self,keys):
        mark=len(self.data)
        os.write(self.master,keys.encode())
        return mark
    def close(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try: self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait()
        self.read(0)
        after=termios.tcgetattr(self.slave)
        restored=(after[3] & (termios.ECHO|termios.ICANON))==(self.before[3] & (termios.ECHO|termios.ICANON))
        os.close(self.master); os.close(self.slave)
        return restored


class PtyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
        self.path=self.base/'perfil.toml'
        source=ROOT/'examples/perfil.toml'
        profile=load_profile(source)
        profile['recording']['screen']=profile['recording']['screen'] or 'TEST-DISPLAY'
        profile['recording']['output']=str(self.base/'videos'/'test-{timestamp}.mkv')
        save_profile(profile,self.path)
        self.terminal=Terminal(self.path,self.base)
        self.terminal.wait_for('Dispositivos actualizados.')
    def tearDown(self):
        restored=self.terminal.close()
        self.tmp.cleanup()
        self.assertTrue(restored,'La terminal no restauró ECHO/ICANON')

    def test_corner_save_record_30_and_find_mkv(self):
        # Start from a copy of the user's existing TOML, not a new scene schema.
        mark=self.terminal.send('c')
        self.terminal.wait_for('Colocar',after=mark)
        # Lower-right is selected initially. k k k -> upper-left, no coordinates.
        self.terminal.send('kkk\n')
        self.terminal.wait_for('Superior izquierda, caja')
        self.terminal.send('s')
        self.terminal.wait_for('Perfil guardado:')
        avatar=next(l for l in load_profile(self.path)['layers'] if l['kind']=='avatar')
        self.assertEqual((avatar['x'],avatar['y']),(20,20))
        mark=self.terminal.send('t')
        self.terminal.wait_for('GRABANDO',after=mark)
        self.terminal.wait_for('Grabación guardada.',timeout=40,after=mark)
        mark=self.terminal.send('o')
        self.terminal.wait_for('Último MKV',after=mark)
        self.terminal.wait_for('.mkv',after=mark)
        videos=list((self.base/'videos').glob('*.mkv'))
        self.assertEqual(len(videos),1)
        report=json.loads(Path(str(videos[0])+'.report.json').read_text())
        self.assertTrue(report['completed'])
        self.assertGreaterEqual(float(report['video']['format']['duration']),29)
        self.terminal.send('\x1b')
        time.sleep(0.1)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_stop_by_key_and_ctrl_c_returns_to_ui(self):
        for use_signal in (False,True):
            mark=self.terminal.send('r')
            self.terminal.wait_for('GRABANDO',after=mark)
            time.sleep(0.15)
            if use_signal: self.terminal.process.send_signal(signal.SIGINT)
            else: self.terminal.send('x')
            self.terminal.wait_for('Grabación guardada.',timeout=12,after=mark)
            self.assertIsNone(self.terminal.process.poll())
        self.assertEqual(len(list((self.base/'videos').glob('*.mkv'))),2)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_recording_screen_is_static_until_input_or_state_change(self):
        mark=self.terminal.send('r')
        self.terminal.wait_for('GRABANDO',after=mark)
        self.terminal.wait_for('Interfaz en reposo',after=mark)
        time.sleep(0.15)
        self.terminal.read(0)
        before=len(self.terminal.data)
        end=time.monotonic()+1.3
        while time.monotonic()<end: self.terminal.read(0.1)
        self.assertEqual(len(self.terminal.data),before,'La captura repinta la terminal sin eventos')
        self.assertNotIn('CAPAS',self.terminal.screen.text())
        self.terminal.send('x')
        self.terminal.wait_for('Grabación guardada.',timeout=12,after=mark)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_switch_to_english_help_record_stop_and_preserve_profile(self):
        original=self.path.read_bytes()
        mark=self.terminal.send('L')
        self.terminal.wait_for('Idioma / Language',after=mark)
        self.terminal.send('jj\n')
        self.terminal.wait_for('Language saved.',after=mark)
        mark=self.terminal.send('?')
        self.terminal.wait_for('NAVIGATION',after=mark)
        self.terminal.wait_for('Next section',after=mark)
        self.terminal.send('\x1b')
        mark=self.terminal.send('r')
        self.terminal.wait_for('Minimal view. Panels are not redrawn.',after=mark)
        self.terminal.send('x')
        self.terminal.wait_for('Recording saved.',timeout=12,after=mark)
        self.assertEqual(self.path.read_bytes(),original)
        self.assertIn('language = "en"',(self.base/'config/trama/ui.toml').read_text())
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_compact_resize_and_focus_navigation(self):
        fcntl.ioctl(self.terminal.slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0))
        self.terminal.process.send_signal(signal.SIGWINCH)
        end=time.monotonic()+1
        while time.monotonic()<end: self.terminal.read(0.1)
        self.assertNotIn('PROPIEDADES',self.terminal.screen.text())
        self.assertIn('GRABAR',self.terminal.screen.text())
        self.terminal.send('\t\t\t')
        self.terminal.wait_for('La misma entrada')
        self.terminal.send('\n')
        self.terminal.wait_for('TRAMA / Micrófono')
        self.terminal.send('\x1b')
        time.sleep(0.1)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_single_field_name_folder_and_unsaved_exit(self):
        new_folder=self.base/'new recordings'
        mark=self.terminal.send('d')
        self.terminal.wait_for('Carpeta de grabaciones',after=mark)
        mark=self.terminal.send('p')
        self.terminal.wait_for('Ruta (relativa',after=mark)
        self.terminal.send('\x15'+str(new_folder)+'\n')
        self.terminal.wait_for('Carpeta:')
        mark=self.terminal.send('n')
        self.terminal.wait_for('Nombre del video',after=mark)
        self.terminal.send('\x15invalid.mp4\n')
        self.terminal.wait_for('elige un archivo .mkv')
        self.terminal.send('\x15daily-{timestamp}.mkv\n')
        self.terminal.send('q')
        self.terminal.wait_for('Cambios sin guardar')
        # Default is "Seguir editando"; Escape preserves the dirty session.
        self.terminal.send('\x1b')
        self.terminal.send('s')
        self.terminal.wait_for('Perfil guardado:')
        self.assertEqual(Path(load_profile(self.path)['recording']['output']).name,'daily-{timestamp}.mkv')
        self.assertEqual(Path(load_profile(self.path)['recording']['output']).parent,new_folder)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_edit_only_one_field(self):
        before=load_profile(self.path)
        mark=self.terminal.send('e')
        self.terminal.wait_for('Editar un campo',after=mark)
        mark=self.terminal.send('\n')
        self.terminal.wait_for('TRAMA / Nombre',after=mark)
        self.terminal.send('\x15Edited name\n')
        self.terminal.wait_for('Nombre: Edited name')
        self.terminal.send('\x1bs')
        self.terminal.wait_for('Perfil guardado:')
        expected=copy.deepcopy(before); expected['layers'][0]['name']='Edited name'
        self.assertEqual(load_profile(self.path),expected)
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_sigterm_unwinds_recording_and_restores_terminal(self):
        mark=self.terminal.send('r')
        self.terminal.wait_for('GRABANDO',after=mark)
        time.sleep(0.15)
        self.terminal.process.send_signal(signal.SIGTERM)
        self.assertEqual(self.terminal.process.wait(timeout=20),143)
        reports=list((self.base/'videos').glob('*.report.json'))
        self.assertEqual(len(reports),1)
        self.assertTrue(json.loads(reports[0].read_text())['completed'])

    def test_first_run_browser_corner_save_and_test(self):
        self.assertTrue(self.terminal.close())
        new_path=self.base/'first-run.toml'
        self.terminal=Terminal(new_path,self.base)
        self.terminal.wait_for('TRAMA / Pantalla')
        self.terminal.send('\n')
        self.terminal.wait_for('TRAMA / Micrófono')
        self.terminal.send('\n')
        self.terminal.wait_for('GIF de reposo')
        self.terminal.send('p')
        self.terminal.wait_for('Ruta (relativa')
        self.terminal.send('\x15'+str(ROOT/'examples/assets/idle.gif')+'\n')
        self.terminal.wait_for('GIF de habla')
        self.terminal.send('p')
        self.terminal.wait_for('Ruta (relativa')
        self.terminal.send('\x15'+str(ROOT/'examples/assets/talking.gif')+'\n')
        self.terminal.wait_for('Colocar Avatar')
        self.terminal.send('\n')
        self.terminal.wait_for('Primera prueba')
        self.terminal.send('\n')
        self.terminal.wait_for('GRABANDO')
        self.terminal.send('x')
        self.terminal.wait_for('Grabación guardada.',timeout=12)
        loaded=load_profile(new_path)
        self.assertEqual(loaded['recording']['screen'],'TEST-DISPLAY')
        self.assertEqual(loaded['recording']['microphone'],'default_input')
        self.assertEqual(len(loaded['layers']),1)
        self.assertEqual((loaded['layers'][0]['x'],loaded['layers'][0]['y']),(1600,760))
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_first_run_without_argument_uses_only_clean_temporary_state(self):
        self.assertTrue(self.terminal.close())
        clean=self.base/'new-user';clean.mkdir()
        new_path=clean/'perfil.toml'
        self.terminal=Terminal(new_path,clean,explicit=False,cwd=clean)
        self.terminal.wait_for('TRAMA / Pantalla')
        self.assertFalse((clean/'state/xolo/session.json').exists())
        self.terminal.send('\n')
        self.terminal.wait_for('TRAMA / Micrófono')
        self.terminal.send('\n')
        self.terminal.wait_for('GIF de reposo')
        self.terminal.send('p')
        self.terminal.wait_for('Ruta (relativa')
        self.terminal.send('\x15'+str(ROOT/'examples/assets/idle.gif')+'\n')
        self.terminal.wait_for('GIF de habla')
        self.terminal.send('p')
        self.terminal.wait_for('Ruta (relativa')
        self.terminal.send('\x15'+str(ROOT/'examples/assets/talking.gif')+'\n')
        self.terminal.wait_for('Colocar Avatar')
        self.terminal.send('\n')
        self.terminal.wait_for('Primera prueba')
        # Save, then return to the editor without needing a real recording.
        self.terminal.send('j\n')
        self.terminal.wait_for('Perfil guardado:')
        self.assertTrue(new_path.is_file())
        pointer=json.loads((clean/'state/xolo/session.json').read_text())
        self.assertEqual(pointer['last_profile'],str(new_path))
        loaded=load_profile(new_path)
        self.assertEqual(len(loaded['layers']),1)
        self.assertEqual(loaded['recording']['output'],str(clean/'recordings/{timestamp}.mkv'))
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)

    def test_daily_start_recovers_last_profile_instead_of_cwd_profile(self):
        self.assertTrue(self.terminal.close())
        profile=load_profile(self.path)
        profile['layers'][0]['name']='Recovered by XDG'
        save_profile(profile,self.path)
        self.terminal=Terminal(self.path,self.base,explicit=False)
        self.terminal.wait_for('Dispositivos actualizados.')
        self.terminal.send('\t')  # Layers shows names; Overview shows a compact count.
        self.terminal.wait_for('Recovered by XDG')
        self.terminal.send('q')
        self.assertEqual(self.terminal.process.wait(timeout=5),0)


if __name__=='__main__': unittest.main()
