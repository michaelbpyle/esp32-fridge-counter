#!/usr/bin/env python3
"""Generate docs/wiring/wiring-diagram.svg (letter landscape, 11 x 8.5 in).

Run from the project folder:
    python tools/gen_wiring_svg.py

The pin map below must match include/config.h. Standard library only.
"""
import itertools
import os

W, H = 1100, 850
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "wiring", "wiring-diagram.svg")

# ---------------------------------------------------------------------------
# Board: ESP32-S3-DevKitC-1 style, 22 pins per side, USB at the bottom.
# ---------------------------------------------------------------------------
J1 = ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18", "8", "3", "46",
      "9", "10", "11", "12", "13", "14", "5V", "GND"]
J3 = ["GND", "TX", "RX", "1", "2", "42", "41", "40", "39", "38", "37", "36", "35", "0",
      "45", "48", "47", "21", "20", "19", "GND", "GND"]

BX0, BX1 = 470, 670          # board left / right edge
ROW0, PITCH = 112, 26        # first pin row centre, pin spacing
PAD = 9                      # pin pad size


def row_y(i):
    return ROW0 + PITCH * i


# Colours (wire colour suggestions are repeated in wiring.md).
C = {
    "3v3": "#d62828", "gnd": "#111111", "5v": "#e07b00",
    "reed": "#7a4a21", "ds": "#c99700", "dht": "#2a9d3a",
    "sda": "#1f6fd1", "scl": "#7b3fc4",
    "de": "#6b7280", "tx": "#0f8b8d", "rx": "#d1338a",
    "sck": "#6b7280", "d1": "#1f6fd1", "d2": "#2a9d3a", "d3": "#c99700", "d4": "#7b3fc4",
}

# Pins that must be left alone: label -> (short reason, fill colour)
AVOID = {
    "TX": "serial", "RX": "serial", "0": "boot", "3": "boot", "45": "boot", "46": "boot",
    "35": "memory", "36": "memory", "37": "memory", "19": "USB", "20": "USB", "48": "LED",
}

out = []


def add(s):
    out.append(s)


def text(x, y, s, size=12, anchor="start", weight="normal", fill="#1a1a1a", style=""):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" font-weight="%s" fill="%s"%s>%s</text>'
        % (x, y, size, anchor, weight, fill, (' font-style="%s"' % style) if style else "", s))


def rect(x, y, w, h, fill="#ffffff", stroke="#333333", sw=1.2, rx=6, extra=""):
    add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" stroke="%s" stroke-width="%g"%s/>'
        % (x, y, w, h, rx, fill, stroke, sw, (" " + extra) if extra else ""))


def wire(points, colour, width=2.6, halo=True, dash=None):
    d = "M" + " L".join("%g %g" % p for p in points)
    if halo:  # white under-stroke so a wire visibly passes OVER what it crosses
        add('<path d="%s" fill="none" stroke="#ffffff" stroke-width="%g" stroke-linejoin="round"/>' % (d, width + 3.5))
    add('<path d="%s" fill="none" stroke="%s" stroke-width="%g" stroke-linejoin="round" stroke-linecap="round"%s/>'
        % (d, colour, width, (' stroke-dasharray="%s"' % dash) if dash else ""))


def dot(x, y, colour, r=4):
    add('<circle cx="%g" cy="%g" r="%g" fill="%s"/>' % (x, y, r, colour))


def badge(x, y, label, kind):
    fill = {"have": "#1f8a3b", "buy": "#b45309", "now": "#1d4ed8"}[kind]
    w = 7.2 * len(label) + 14
    rect(x - w, y, w, 17, fill=fill, stroke=fill, rx=8.5)
    text(x - w / 2, y + 12.5, label, size=10.5, anchor="middle", weight="bold", fill="#ffffff")


def route(side, wires, x_from, x_to, ch_lo, ch_hi):
    """Route wires (ya, yb, colour) from x_from to x_to with one elbow each.

    Each wire runs horizontally at ya, vertically in its own channel, then
    horizontally at yb. Channel order is brute-forced for the fewest crossings.
    """
    n = len(wires)
    if n == 0:
        return
    step = (ch_hi - ch_lo) / max(1, n - 1) if n > 1 else 0
    xs = [ch_lo + step * i for i in range(n)]

    def crossings(perm):
        total = 0
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                ci, cj = xs[perm[i]], xs[perm[j]]
                ya_i, yb_i = wires[i][0], wires[i][1]
                lo, hi = min(ya_i, yb_i), max(ya_i, yb_i)
                # wire j's first horizontal (at ya_j, between x_from and cj) vs wire i's vertical
                if min(x_from, cj) < ci < max(x_from, cj) and lo <= wires[j][0] <= hi:
                    total += 1
                # wire j's second horizontal (at yb_j, between cj and x_to) vs wire i's vertical
                if min(x_to, cj) < ci < max(x_to, cj) and lo <= wires[j][1] <= hi:
                    total += 1
        return total

    best = min(itertools.permutations(range(n)), key=crossings)
    if crossings(best):
        raise SystemExit("%s side: could not route without crossings (%d)" % (side, crossings(best)))
    for i, (ya, yb, colour) in enumerate(wires):
        cx = xs[best[i]]
        if abs(ya - yb) < 0.5:
            wire([(x_from, ya), (x_to, yb)], colour)
        else:
            wire([(x_from, ya), (cx, ya), (cx, yb), (x_to, yb)], colour)


# ---------------------------------------------------------------------------
add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="11in" height="8.5in" '
    'font-family="Arial, Helvetica, sans-serif">' % (W, H))
add('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (W, H))

text(26, 30, "Hollygrove Community Fridge door counter - wiring diagram", size=19, weight="bold")
text(26, 48, "Board shown: ESP32-S3-DevKitC-1 style N16R8 (22 pins per side). Wire to the GPIO NUMBER printed "
             "next to each pin. All sensors run on 3.3 V.", size=11.5, fill="#444444")

# ---- power rails -----------------------------------------------------------
RAIL_3V3_L, RAIL_GND_L = 30, 48
RAIL_3V3_R, RAIL_GND_R = 1070, 1052
TOP, BOT = 60, 812
wire([(RAIL_3V3_L, 640), (RAIL_3V3_L, TOP), (RAIL_3V3_R, TOP), (RAIL_3V3_R, 430)], C["3v3"], width=3.2, halo=False)
wire([(RAIL_GND_L, 100), (RAIL_GND_L, BOT), (RAIL_GND_R, BOT), (RAIL_GND_R, 230)], C["gnd"], width=3.2, halo=False)
text(120, TOP + 15, "3V3 (3.3 V) - red", size=11, fill=C["3v3"], weight="bold")
text(120, BOT + 16, "GND (ground) - black", size=11, fill=C["gnd"], weight="bold")

# ---- board -----------------------------------------------------------------
rect(BX0, 70, BX1 - BX0, 640, fill="#1f2937", stroke="#111827", sw=1.5, rx=8)
text((BX0 + BX1) / 2, 85, "ESP32-S3-WROOM-1 (N16R8)", size=11, anchor="middle", weight="bold", fill="#e5e7eb")
text((BX0 + BX1) / 2, 99, "RGB status LED on board = GPIO48", size=9.5, anchor="middle", fill="#fde68a")
for k, (lab, xo) in enumerate((("USB-C", -36), ("USB-C", 36))):
    rect((BX0 + BX1) / 2 + xo - 22, 694, 44, 26, fill="#d1d5db", stroke="#6b7280", rx=4)
    text((BX0 + BX1) / 2 + xo, 711, lab, size=9.5, anchor="middle", fill="#111827")
text((BX0 + BX1) / 2, 736, "USB-C: 5 V power + programming", size=10.5, anchor="middle", fill="#444444")
text((BX0 + BX1) / 2, 749, "(use the port marked UART / COM)", size=10.5, anchor="middle", fill="#444444")

USED = {}  # label side -> colour, filled in below


def draw_pins():
    for side, labels in (("L", J1), ("R", J3)):
        for i, lab in enumerate(labels):
            y = row_y(i)
            x = BX0 - PAD if side == "L" else BX1
            key = (side, i)
            if key in USED:
                fill = USED[key]
            elif lab in ("3V3",):
                fill = C["3v3"]
            elif lab == "GND":
                fill = "#000000"
            elif lab == "5V":
                fill = C["5v"]
            elif lab in AVOID:
                fill = "#fca5a5"
            else:
                fill = "#d1d5db"
            rect(x, y - PAD / 2, PAD, PAD, fill=fill, stroke="#111827", sw=0.8, rx=1.5)
            tx = BX0 + 7 if side == "L" else BX1 - 7
            anchor = "start" if side == "L" else "end"
            is_used = key in USED or lab in ("3V3", "GND", "5V")
            colour = "#ffffff" if is_used else ("#fca5a5" if lab in AVOID else "#9ca3af")
            shown = lab if lab in ("3V3", "GND", "5V", "RST", "TX", "RX") else "GPIO" + lab
            if lab in AVOID:
                shown += " (%s)" % AVOID[lab] if side == "L" else ""
                if side == "R":
                    shown = "(%s) %s" % (AVOID[lab], "GPIO" + lab if lab not in ("TX", "RX") else lab)
            text(tx, y + 4, shown, size=10.5, anchor=anchor, weight="bold" if is_used else "normal", fill=colour)


# ---- left-hand components --------------------------------------------------
LX0, LX1 = 82, 312   # component box left / right edge


def comp_box(y, h, title, sub, badge_label, badge_kind, dashed=False):
    rect(LX0, y, LX1 - LX0, h, fill="#f8fafc", stroke="#334155", sw=1.3,
         extra='stroke-dasharray="6 4"' if dashed else "")
    text(LX0 + 10, y + 18, title, size=13, weight="bold")
    if sub:
        text(LX0 + 10, y + 33, sub, size=10.5, fill="#475569")
    badge(LX1 - 8, y + 6, badge_label, badge_kind)


def pin_label(x, y, label, anchor="end"):
    text(x - 6 if anchor == "end" else x + 6, y + 4, label, size=11, anchor=anchor, weight="bold")


def power_stubs(box_left, y3v3, ygnd, right_side=False):
    """Short stubs from a component to the 3V3 and GND rails, with junction dots."""
    if not right_side:
        if y3v3 is not None:
            wire([(box_left, y3v3), (RAIL_3V3_L, y3v3)], C["3v3"], width=2.4)
            dot(RAIL_3V3_L, y3v3, C["3v3"])
        if ygnd is not None:
            wire([(box_left, ygnd), (RAIL_GND_L, ygnd)], C["gnd"], width=2.4)
            dot(RAIL_GND_L, ygnd, C["gnd"])
    else:
        if y3v3 is not None:
            wire([(box_left, y3v3), (RAIL_3V3_R, y3v3)], C["3v3"], width=2.4)
            dot(RAIL_3V3_R, y3v3, C["3v3"])
        if ygnd is not None:
            wire([(box_left, ygnd), (RAIL_GND_R, ygnd)], C["gnd"], width=2.4)
            dot(RAIL_GND_R, ygnd, C["gnd"])


left_wires = []


def sig(y_comp, side, row, colour):
    USED[(side, row)] = colour
    return (y_comp, row_y(row), colour)


# Reed switch
y = 92
comp_box(y, 66, "Reed switch (door)", "2 wires, either way round", "IN USE NOW", "now")
pin_label(LX1, y + 50, "to GPIO4")
left_wires.append(sig(y + 50, "L", J1.index("4"), C["reed"]))
text(LX0 + 10, y + 54, "other wire to GND", size=11, weight="bold")
power_stubs(LX0, None, y + 50)

# DS18B20
y = 170
comp_box(y, 92, "DS18B20 probe", "fridge temperature, waterproof", "TO BUY", "buy")
pin_label(LX1, y + 50, "DATA (yellow)")
left_wires.append(sig(y + 50, "L", J1.index("5"), C["ds"]))
text(LX0 + 10, y + 52, "VDD (red) to 3V3", size=11, weight="bold")
text(LX0 + 10, y + 80, "GND (black) to GND", size=11, weight="bold")
power_stubs(LX0, y + 48, y + 76)
# pull-up resistor from DATA to 3V3, drawn inside the box under the label
rx, ry = LX1 - 6, y + 62
wire([(rx, y + 50), (rx, ry)], C["ds"], width=2, halo=False)
rect(rx - 6, ry, 12, 20, fill="#fef3c7", stroke="#92400e", sw=1.2, rx=2)
text(rx - 12, ry + 9, "4.7 k pull-up", size=10.5, anchor="end", weight="bold", fill="#92400e")
text(rx - 12, ry + 21, "DATA to 3V3", size=10, anchor="end", fill="#92400e")

# DHT
y = 274
comp_box(y, 72, "DHT11 / DHT22", "air temp + humidity (DHT11 on hand)", "ON HAND", "have")
pin_label(LX1, y + 54, "DATA")
left_wires.append(sig(y + 54, "L", J1.index("6"), C["dht"]))
text(LX0 + 10, y + 50, "+ / VCC to 3V3", size=11, weight="bold")
text(LX0 + 10, y + 65, "- / GND to GND", size=11, weight="bold")
power_stubs(LX0, y + 46, y + 61)

# RS485
y = 358
comp_box(y, 116, "RS485 (reserved)", "future link to the solar inverter (Modbus)", "TO BUY", "buy", dashed=True)
for k, (lab, pin, col) in enumerate((("DE + RE", "16", "de"), ("DI", "17", "tx"), ("RO", "18", "rx"))):
    yy = y + 56 + 19 * k
    pin_label(LX1, yy, lab)
    left_wires.append(sig(yy, "L", J1.index(pin), C[col]))
text(LX0 + 10, y + 54, "VCC to 3V3", size=11, weight="bold")
text(LX0 + 10, y + 73, "GND to GND", size=11, weight="bold")
text(LX0 + 10, y + 92, "A / B to inverter", size=11, weight="bold")
text(LX0 + 10, y + 108, "Buy a 3.3 V type (MAX3485)", size=10, fill="#b45309")
power_stubs(LX0, y + 50, y + 69)

# BMP280
y = 486
comp_box(y, 92, "BMP280 (or BME280)", "air temperature + pressure, I2C", "ON HAND", "have")
pin_label(LX1, y + 54, "SDA")
pin_label(LX1, y + 76, "SCL")
left_wires.append(sig(y + 54, "L", J1.index("8"), C["sda"]))
left_wires.append(sig(y + 76, "L", J1.index("9"), C["scl"]))
text(LX0 + 10, y + 56, "VCC / VIN to 3V3", size=11, weight="bold")
text(LX0 + 10, y + 78, "GND to GND", size=11, weight="bold")
power_stubs(LX0, y + 52, y + 74)

# Left notes
y = 596
rect(LX0, y, LX1 - LX0, 150, fill="#fffbeb", stroke="#b45309", sw=1.2)
text(LX0 + 10, y + 18, "Rules that protect the board", size=12.5, weight="bold", fill="#92400e")
for k, line in enumerate((
        "3.3 V ONLY on every GPIO pin.",
        "Never connect 5 V to a GPIO pin.",
        "Power every sensor from 3V3, not 5V.",
        "Unplug USB before changing wires.",
        "Pink pins on the board: leave empty",
        "(boot, memory, USB, serial, LED).",
        "Grey pins are free for later use.")):
    text(LX0 + 10, y + 38 + 16 * k, line, size=11, fill="#451a03")

# ---- right-hand components -------------------------------------------------
RX0, RX1 = 790, 1010
right_wires = []

y = 196
rect(RX0, y, RX1 - RX0, 214, fill="#f8fafc", stroke="#334155", sw=1.3, extra='stroke-dasharray="6 4"')
text(RX0 + 62, y + 18, "HX711 amplifiers x4", size=13, weight="bold")
text(RX0 + 62, y + 33, "shelf scales - experimental", size=10.5, fill="#475569")
badge(RX1 - 8, y + 40, "TO BUY", "buy")
hx = (("SCK (all 4 joined)", "42", "sck"), ("DT of HX711 #1", "41", "d1"), ("DT of HX711 #2", "40", "d2"),
      ("DT of HX711 #3", "39", "d3"), ("DT of HX711 #4", "38", "d4"))
for lab, pin, col in hx:
    r = J3.index(pin)
    yy = row_y(r)
    text(RX0 + 8, yy + 4, lab, size=11, weight="bold")
    right_wires.append((yy, yy, C[col]))
    USED[("R", r)] = C[col]
text(RX1 - 8, y + 176, "VCC (each) to 3V3", size=11, anchor="end", weight="bold")
text(RX1 - 8, y + 200, "GND (each) to GND", size=11, anchor="end", weight="bold")
power_stubs(RX1, y + 172, y + 196, right_side=True)

# load cells
y2 = 428
for k in range(4):
    x = RX0 + 4 + 54 * k
    rect(x, y2, 48, 34, fill="#e2e8f0", stroke="#475569", rx=3)
    text(x + 24, y2 + 14, "load", size=9.5, anchor="middle")
    text(x + 24, y2 + 26, "cell %d" % (k + 1), size=9.5, anchor="middle")
    wire([(x + 24, y2), (x + 24, 410)], "#475569", width=1.6, halo=False, dash="3 2")
text(RX0, y2 + 50, "Each load cell plugs into its own HX711", size=10.5, fill="#475569")
text(RX0, y2 + 63, "(E+, E-, A+, A-: see the HX711 board labels).", size=10.5, fill="#475569")

# Right notes: status + other boards
y = 512
rect(RX0 - 28, y, RX1 - RX0 + 56, 96, fill="#f0fdf4", stroke="#166534", sw=1.2)
text(RX0 - 18, y + 18, "What works today", size=12.5, weight="bold", fill="#14532d")
for k, line in enumerate((
        "Door counting (reed switch): working.",
        "Any sensor here is found automatically",
        "at power-up. A sensor that is not",
        "plugged in is simply ignored.")):
    text(RX0 - 18, y + 37 + 15 * k, line, size=11, fill="#14532d")

y = 620
rect(RX0 - 28, y, RX1 - RX0 + 56, 124, fill="#eff6ff", stroke="#1e40af", sw=1.2)
text(RX0 - 18, y + 18, "Other boards", size=12.5, weight="bold", fill="#1e3a8a")
for k, line in enumerate((
        "Freenove ESP32-S3 WROOM (20 pins per",
        "side): same GPIO numbers, same order.",
        "Leave its microSD slot EMPTY (it uses",
        "GPIO38-40, the HX711 #2-#4 pins).",
        "Walter (LTE-M): same GPIO numbers;",
        "see the second table in wiring.md.")):
    text(RX0 - 18, y + 37 + 14.5 * k, line, size=11, fill="#1e3a8a")

# ---- board power wiring ----------------------------------------------------
# 3V3 pin (J1 row 0) up to the red rail; GND pin (J1 last row) down to the black rail.
wire([(BX0 - PAD, row_y(0)), (BX0 - 24, row_y(0)), (BX0 - 24, TOP)], C["3v3"], width=3)
dot(BX0 - 24, TOP, C["3v3"])
gy = row_y(len(J1) - 1)
wire([(BX0 - PAD, gy), (BX0 - 24, gy), (BX0 - 24, BOT)], C["gnd"], width=3)
dot(BX0 - 24, BOT, C["gnd"])
# 5 V input block
py = 738
rect(318, py, 112, 66, fill="#fff7ed", stroke="#c2410c", sw=1.3)
text(374, py + 16, "5 V power in", size=12, anchor="middle", weight="bold", fill="#7c2d12")
text(374, py + 30, "(field: 5 V buck)", size=10.5, anchor="middle", fill="#7c2d12")
text(374, py + 45, "Bench: USB-C only.", size=10, anchor="middle", fill="#7c2d12")
text(374, py + 58, "Never both at once.", size=10, anchor="middle", weight="bold", fill="#7c2d12")
vy = row_y(J1.index("5V"))
wire([(BX0 - PAD, vy), (BX0 - 40, vy), (BX0 - 40, py + 10), (430, py + 10)], C["5v"], width=3)
text(BX0 - 46, vy - 6, "5V", size=10.5, anchor="end", weight="bold", fill=C["5v"])
wire([(374, py + 66), (374, BOT)], C["gnd"], width=2.4)
dot(374, BOT, C["gnd"])

# ---- signal wires ----------------------------------------------------------
route("left", left_wires, LX1, BX0 - PAD, 336, 420)
route("right", right_wires, BX1 + PAD, RX0, 700, 770)
for (ya, yb, colour) in left_wires:
    dot(LX1, ya, colour, r=3.5)
for (ya, yb, colour) in right_wires:
    dot(RX0, ya, colour, r=3.5)

draw_pins()

text(W - 26, H - 10, "Generated by tools/gen_wiring_svg.py - pin map from include/config.h (firmware 1.0.0)", size=9.5,
     anchor="end", fill="#6b7280")
add("</svg>")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("wrote", os.path.normpath(OUT))
