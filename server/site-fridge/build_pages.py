"""Builds the three pages published under hollygrovenola.org/fridge/ from two sources.

  hub.qmd        -> out/fridge/index.qmd          the hub with two cards
  dashboard.qmd  -> out/fridge/sample/index.qmd   the dashboard, always sample data
                 -> out/fridge/live/index.qmd     the dashboard, real data from LIVE_DEVICE

Edit hub.qmd or dashboard.qmd, run `python build_pages.py`, then copy out/fridge/ to
/opt/hollygrove/site/fridge/ on the VM. LIVE_DEVICE is the WiFi test unit for now; set it
to None once the fridge unit reports, and the live page will show the public numbers.
"""
from pathlib import Path

HERE = Path(__file__).parent
LIVE_DEVICE = "bench-01"
src = (HERE / "dashboard.qmd").read_text(encoding="utf-8")

def swap(text, old, new):
    assert text.count(old) == 1, f"expected exactly one: {old[:60]!r} ({text.count(old)} found)"
    return text.replace(old, new)

def page(mode):
    t = src
    if mode == "sample":
        t = swap(t, 'title: "Community Fridge Door Counter"', 'title: "Fridge Door Counter: Sample Data"')
        t = swap(t, "var DEMO = qs.get('demo') === '1';", "var DEMO = true;")
        t = swap(t, "var DEVICE = /^[A-Za-z0-9_-]{1,32}$/.test(qs.get('device') || '') ? qs.get('device') : null;", "var DEVICE = null;")
    else:
        dev = "null" if LIVE_DEVICE is None else "'" + LIVE_DEVICE + "'"
        t = swap(t, 'title: "Community Fridge Door Counter"', 'title: "Fridge Door Counter: Live WiFi Test"')
        t = swap(t, "var DEMO = qs.get('demo') === '1';", "var DEMO = false;")
        t = swap(t, "var DEVICE = /^[A-Za-z0-9_-]{1,32}$/.test(qs.get('device') || '') ? qs.get('device') : null;", "var DEVICE = " + dev + ";")
    t = swap(t, 'They are not real counts. <a href="./">See the real numbers</a>.</div>',
             'They are not real counts. <a href="../live/">See the live WiFi test</a> or go <a href="../">back to the counter page</a>.</div>')
    t = swap(t, '<strong>TEST VIEW.</strong> Showing one device only: <span id="fridge-device-name"></span>. <a href="./">Back to the public numbers</a>.</div>',
             '<strong>WIFI TEST.</strong> These are real counts from the test unit on the workbench, not from the fridge.<span id="fridge-device-name" hidden></span> <a href="../sample/">See the sample data</a> or go <a href="../">back to the counter page</a>.</div>')
    t = swap(t, '<a href="?demo=1">See a preview with sample data</a>', '<a href="../sample/">See a preview with sample data</a>')
    t = swap(t, '[Get in touch](../contact/)', '[Get in touch](../../contact/)')
    return t

out = HERE / "out" / "fridge"
(out / "sample").mkdir(parents=True, exist_ok=True)
(out / "live").mkdir(parents=True, exist_ok=True)
(out / "index.qmd").write_text((HERE / "hub.qmd").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
(out / "sample" / "index.qmd").write_text(page("sample"), encoding="utf-8", newline="\n")
(out / "live" / "index.qmd").write_text(page("live"), encoding="utf-8", newline="\n")
print("built", out)
