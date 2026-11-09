"""Independent pixels/time/loop oracle via Pillow; optional C reference parity."""
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageSequence, GifImagePlugin

DUMP = "build/rust-target/release/media-dump"


def check(path, compare_c=False):
    with Image.open(path) as image:
        size = image.size
        frames = []
        durations = []
        for frame in ImageSequence.Iterator(image):
            frames.append(frame.convert("RGBA").convert("RGBa").tobytes())
            durations.append(frame.info.get("duration", 0) or 100)
        loop = image.info.get("loop")
        plays = 1 if loop is None else None if loop == 0 else loop + 1
    info = json.loads(subprocess.check_output([DUMP, str(path), "--info"]))
    cycle = sum(durations)
    assert info["cycle_ms"] == cycle and info["frames"] == len(frames), info
    assert info["plays"] == plays and (info["width"], info["height"]) == size, info
    assert info["cache_bytes"] == size[0] * size[1] * 4 * len(frames)
    assert info["cache_bytes"] <= 16 * 2**20 and info["temporary_bytes"] <= 8 * 2**20
    starts = [0] + info["ends_ms"][:-1]
    times = {0, cycle * 1000 + 1}
    for iteration in range(3):
        for start in starts + [cycle]:
            times.update(iteration * cycle + start + delta for delta in (-1, 0, 1)
                         if iteration * cycle + start + delta >= 0)
    for ms in sorted(times):
        if plays is not None and ms >= cycle * plays:
            index = len(frames) - 1
        else:
            phase = ms % cycle
            index = max(i for i, start in enumerate(starts) if start <= phase)
        actual = subprocess.check_output([DUMP, str(path), str(ms)])
        assert actual == frames[index], (path, ms, index)
    if compare_c:
        assert Path("build/media-dump").is_file(), "Falta el oráculo C previamente compilado"
        # Compare inside intervals to avoid the C prototype's floating boundary rounding.
        for ms in [start + 1 for start in starts] + [cycle + 1, cycle * 2 + 1]:
            c_raw = subprocess.check_output(["build/media-dump", str(path), str(ms / 1000)], stderr=subprocess.DEVNULL)
            c_premultiplied = Image.frombytes("RGBA", size, c_raw).convert("RGBa").tobytes()
            rust_raw = subprocess.check_output([DUMP, str(path), str(ms)])
            assert rust_raw == c_premultiplied, ("C/Rust", path, ms)
    print(f"OK {path.name}: {len(frames)} frames, tiempos/disposal/alfa/loop, {info['cache_bytes']} bytes de caché")


def partial_gif(path, loop=None, opaque=False, local=False, zero_delay=False):
    palette = [0, 30, 90, 255, 30, 20, 20, 220, 50, 40, 80, 250] + [0] * (768 - 12)
    canvas = Image.new("P", (20, 18), 0)
    canvas.putpalette(palette)
    header, _ = GifImagePlugin.getheader(canvas, info={"background": 0})
    data = bytearray(b"".join(header))
    if loop is not None:
        data.extend(b"\x21\xff\x0bNETSCAPE2.0\x03\x01" + loop.to_bytes(2, "little") + b"\x00")
    for i, (x, y, w, h, disposal) in enumerate([(0,0,20,18,1),(2,3,7,6,2),(8,5,5,8,3),(1,9,9,3,1)]):
        frame = Image.new("P", (w, h), 0)
        colors = palette.copy()
        if local and i:
            colors[3:6] = [240, 170, 20]
        frame.putpalette(colors)
        for row in range(h):
            for col in range(w):
                if (row + col) % 3:
                    frame.putpixel((col, row), 1 + i % 3)
        options = {"duration": 0 if zero_delay and i == 0 else [10,70,130,40][i],
                   "disposal": disposal, "include_color_table": local}
        if not opaque:
            options["transparency"] = 0
        data.extend(b"".join(GifImagePlugin.getdata(frame, offset=(x, y), **options)))
    data.append(0x3B)
    path.write_bytes(data)


for asset in sorted(Path("examples/assets").glob("*.gif")):
    check(asset, compare_c=True)

with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    for name, options in [("once", {}), ("finite", {"loop": 1}), ("infinite", {"loop": 0}),
                          ("opaque", {"opaque": True}), ("local", {"local": True}),
                          ("zero-delay", {"zero_delay": True})]:
        path = folder / (name + ".gif")
        partial_gif(path, **options)
        check(path)
    # PIL emits interlaced image data for this larger canvas.
    image = Image.new("P", (32, 24))
    image.putpalette([v for i in range(256) for v in (i, 255-i, (i*3)%256)])
    image.putdata([(x * 7 + y * 13) % 256 for y in range(24) for x in range(32)])
    path = folder / "interlaced.gif"
    image.save(path, interlace=True, duration=50)
    check(path)
    good = path.read_bytes()
    for name, data in [("no-trailer", good[:-1]), ("truncated", good[:50]),
                       ("bad-header", b"GIF89a"), ("bad-block", good[:13] + b"\xff")]:
        path = folder / (name + ".gif")
        path.write_bytes(data)
        result = subprocess.run([DUMP, str(path), "--info"], capture_output=True)
        assert result.returncode == 1, (name, result)
    print("OK rechazo de GIFs truncados/malformados")
    # A GIF87a image with no graphics-control delay uses the explicit 100 ms policy.
    still = Image.new("P", (8, 8), 1)
    still.putpalette([0, 0, 0, 120, 50, 200] + [0] * 762)
    header, _ = GifImagePlugin.getheader(still)
    path = folder / "no-gce.gif"
    path.write_bytes(b"".join(header) + b"".join(GifImagePlugin.getdata(still)) + b"\x3b")
    check(path)
