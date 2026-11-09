"""Create the Flatpak icon derivative without modifying the original artwork."""
from pathlib import Path
import struct
import subprocess


def install_icon(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-y', '-i', str(source), '-vf',
                    'scale=512:512:force_original_aspect_ratio=decrease:flags=lanczos,'
                    'pad=512:512:(ow-iw)/2:(oh-ih)/2:color=black@0,format=rgba',
                    '-frames:v', '1', '-threads', '1', '-update', '1',
                    str(destination)], check=True)
    header = destination.read_bytes()[:24]
    if header[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', header[16:24]) != (512, 512):
        raise ValueError('Flatpak icon must be a 512x512 PNG')
    destination.chmod(0o644)
