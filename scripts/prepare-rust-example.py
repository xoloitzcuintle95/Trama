"""Creates a STATIC PNG example from frame 0; never modifies the supplied GIF."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent.parent
output = root / "build/rust-fixtures/idle-static.png"
output.parent.mkdir(parents=True, exist_ok=True)
with Image.open(root / "examples/assets/idle.gif") as source:
    source.seek(0)
    source.convert("RGBA").save(output)
print(output)
