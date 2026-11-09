"""Independent GIF reference via Pillow (test-only dependency, not runtime)."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageSequence


def visible_rgba(data):
    # RGB beneath fully transparent pixels is unspecified by GIF decoders.
    data = bytearray(data)
    for i in range(0, len(data), 4):
        if data[i + 3] == 0:
            data[i:i + 3] = b"\0\0\0"
    return data


def check(path, repeats):
    with Image.open(path) as image:
        frames = [(f.convert("RGBA").tobytes(), f.info.get("duration", 10) / 1000)
                  for f in ImageSequence.Iterator(image)]
    cycle = sum(duration for _, duration in frames)
    starts = []
    start = 0
    for _, duration in frames:
        starts.append(start)
        start += duration
    # Check immediately before/after every boundary, including repetition/EOF.
    for t in [0] + [cycle * loop + start + delta
                    for loop in range(3) for start in starts for delta in (-0.001, 0.001)
                    if cycle * loop + start + delta >= 0]:
        if repeats is not None and t >= cycle * repeats:
            index = len(frames) - 1
        else:
            phase = t % cycle
            index = max(i for i, start in enumerate(starts) if start <= phase)
        result = subprocess.run(["build/media-dump", str(path), str(t)],
                                capture_output=True, check=True)
        assert visible_rgba(result.stdout) == visible_rgba(frames[index][0]), (path, t, index, result.stderr)
    print(f"OK {path}: pixels RGBA, tiempos, disposal y repetición ({repeats})")


for original in sorted(Path("examples/assets").glob("*.gif")):
    check(original, None)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "still.png"
    image = Image.new("RGBA", (9, 7), (30, 60, 90, 128))
    image.save(path)
    for t in (0, 0.5, 60):
        result = subprocess.run(["build/media-dump", str(path), str(t)],
                                capture_output=True, check=True)
        assert result.stdout == image.tobytes()
    print("OK PNG: imagen fija, alfa parcial y persistencia")
    # Partial transparent frames exercise restore-background/restore-previous.
    frames = []
    for x in (0, 3, 6):
        frame = Image.new("RGBA", (12, 12))
        for y in range(3, 6):
            for col in range(x, x + 3):
                frame.putpixel((col, y), (255, 40, 20, 255))
        frames.append(frame)
    for name, loop, repeats in [("once", None, 1), ("finite", 1, 2), ("forever", 0, None)]:
        path = Path(directory) / f"{name}.gif"
        options = {} if loop is None else {"loop": loop}
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=[10, 70, 130], disposal=[1, 2, 3], **options)
        check(path, repeats)
