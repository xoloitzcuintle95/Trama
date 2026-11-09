#!/usr/bin/env python3
"""Generate neutral geometric examples; no personal artwork or app mascot."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def write_animation(path, size=128, active=False):
    palette=[0,0,0, 72,145,210, 85,190,135, 235,240,245]+[0]*(768-12)
    frames=[]
    for offset in (0,2,0,-2):
        frame=Image.new('P',(size,size),0)
        frame.putpalette(palette)
        draw=ImageDraw.Draw(frame)
        inset=size//5
        draw.rounded_rectangle((inset,inset+offset,size-inset-1,size-inset-1+offset),
                               radius=max(1,size//10),fill=2 if active else 1)
        draw.ellipse((size//2-3,inset+offset+5,size//2+3,inset+offset+11),fill=3)
        frames.append(frame)
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=[150,2000,150,3000],
                   loop=0,transparency=0,disposal=2,optimize=False)


def main():
    folder=ROOT/'examples/assets'
    folder.mkdir(parents=True,exist_ok=True)
    write_animation(folder/'idle.gif')
    write_animation(folder/'talking.gif',active=True)
    image=Image.new('RGBA',(240,80),(0,0,0,0))
    ImageDraw.Draw(image).rounded_rectangle((2,2,237,77),radius=12,fill=(72,145,210,160))
    image.save(folder/'overlay.png')
    print('Ejemplos geométricos generados en examples/assets')


if __name__=='__main__': main()
