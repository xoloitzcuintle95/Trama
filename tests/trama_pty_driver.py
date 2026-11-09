"""Test-only adapter: real TUI/loader/recorder, simulated devices and capture.
There is no equivalent bypass flag or engine override in the production launcher.
"""
from pathlib import Path
import os
import sys
runtime=os.environ.get("TRAMA_TEST_RUNTIME")
scripts=Path(runtime)/"scripts" if runtime else Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(scripts))
import compositor as backend
from compositor_profile import load_profile, new_profile
import trama_tui

fixture=Path(os.environ.get("TRAMA_TEST_PROFILE",sys.argv[1] if len(sys.argv)>1 else "perfil.toml"))
profile=load_profile(fixture) if fixture.exists() else new_profile(fixture.parent)
screen=profile["recording"]["screen"] or "TEST-DISPLAY"
source=profile["recording"]["microphone"] or "test.mic"
if source=="default_input": source="test.mic"

# The selected production runtime supplies its own engine and manifest checks.
gsr=backend.Devices().gsr
if runtime:
    assert Path(trama_tui.__file__).parent==scripts
    assert Path(backend.__file__).parent==scripts

class Devices:
    gsr=gsr
    def screens(self): return {screen:(1920,1080)}
    def audio(self): return {"default_output":"Game",source:"Test microphone"},{source:"Test microphone"}
    def capabilities(self): pass
    def resolve_mic(self,selected,audio=None):
        if not selected: return None
        if selected=="default_input": return source
        if selected!=source: raise ValueError("recording.microphone: missing")
        return source

trama_tui.Devices=Devices
backend.probe_microphone=lambda selected:None
original=backend.recording_command
def command(prepared):
    args=original(prepared)
    args[0]=os.environ["TRAMA_TEST_ENGINE"]
    return args
backend.recording_command=command
sys.exit(trama_tui.main(sys.argv[1:]))
