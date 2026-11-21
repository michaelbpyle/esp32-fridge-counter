"""Builds the artifact page: replaces {{IMG:name}} in the template with JPEG data URIs."""
import base64, io, re
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
P = Path(r"I:\Projects\Microcontrollers\esp32-fridge-counter")
IMAGES = {
    "wiring": (HERE / "wiring.png", 1100, (0, 0, 1050, 820)),
    "dash_live": (HERE / "live-fridge.png", 800, (0, 0, 1100, 2300)),
    "door_plate": (P / "cad/demo-door/pictures/print-plate-angle-rev2.png", 600, None),
    "door_foot": (P / "cad/demo-door/pictures/base-plate-rev1-with-door-rev2.png", 560, None),
    "door_switch": (P / "cad/demo-door/pictures/switch-and-magnet-closeup-rev2.png", 520, None),
    "case_closed": (P / "cad/enclosure/pictures/bench-case-devkitc/preview-case-closed-fnk0101-rev1.png", 640, None),
    "walter": (P / "cad/enclosure/pictures/weatherproof-box-sled/preview-sled-in-box-walter-rev1.png", 640, None),
}

def data_uri(path, width, crop):
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop((0, 0, min(crop[2], im.width), min(crop[3], im.height)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

html = (HERE / "template.html").read_text(encoding="utf-8")
def sub(m):
    path, width, crop = IMAGES[m.group(1)]
    if not path.exists():
        print("MISSING", path); return ""
    return data_uri(path, width, crop)
html = re.sub(r"\{\{IMG:(\w+)\}\}", sub, html)
out = HERE / "fridge-counter-build.html"
out.write_text(html, encoding="utf-8")
print(out, round(len(html) / 1024), "KB")
