# Power, weatherproofing and mounting plan — fridge door-counter node

Written 2026-11-14 for the Hollygrove Community Fridge door counter (9000 Oleander St).
Audience: a volunteer who is not an electrical engineer. Nothing here has been built or
measured yet. Every choice made without the owner is logged in
`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\enclosure.md`.

Related files:

- Printable case and junction-box sled:
  `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\README.md`
- Pin map and signal wiring (owned by the firmware work, not repeated here):
  `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\wiring\`

## 1. The short version

1. **Power, first field install:** a listed 5 V USB wall adapter plugged into the inverter's
   120 VAC output, kept indoors in the dry-goods room, with a low-voltage 5 V cable run out to
   the node. Nobody touches the battery.
2. **Power, long term:** an **isolated** 48 V-to-5 V converter rated for 75 V input
   (Mean Well DDR-15L-5), fused at the battery bus, installed by whoever maintains the solar
   system. It keeps the node alive when the inverter is off.
3. **The LM2596 modules on hand must never be connected to the 48 V battery.** They are 40 V
   parts and the battery bus reaches 56 to 61 V.
4. **Weather barrier:** a bought, gasketed polycarbonate junction box (Hammond 1554H2GY) with
   cable glands on the bottom face. The 3D-printed part goes *inside* it as a carrier ("sled")
   for the electronics. A printed shell on its own is for the bench, demos and sheltered spots.
5. **Never drill the refrigerator.** Mount the box on the shelter structure. Bring the door
   sensor wire and any temperature probe in over the door gasket with flat cable.

## 2. What the node draws

| Configuration | Typical | Peak | Size the supply for |
|---|---|---|---|
| ESP32-S3 dev board, WiFi always on (today's firmware) | 80 to 120 mA at 5 V (0.4 to 0.6 W) | about 350 mA for milliseconds during transmit | 1 A |
| Same, plus breakout-board LEDs, BMP280, DS18B20, 4 x HX711, MAX485 | add roughly 30 to 60 mA | same | 1 A |
| Walter LTE-M board (later) | 10 to 60 mA | about 450 mA LTE transmit bursts | 1 A at 5 V (datasheet figure) |

At 0.6 W continuous the node uses about 14 Wh per day, about 0.3 percent of the EG4
battery's 5.12 kWh. Power budget is not a constraint; safety and reliability are.

Sources: project log (80 to 120 mA measured class figure for the WiFi firmware), Walter
datasheet rev 1.2 as summarised in `docs\archive\build-out-tutorial.md` Option 9.

## 3. Power options compared

The site's power system, from the two manuals in the `research` folder and EG4's spec sheet:

- Growatt SPF 3000TL LVM-48P inverter/charger: no-load consumption **under 50 W**, power
  saving mode **disabled by default**, constant-voltage charge 56.4 V, high DC cut-off
  **60.8 V**, operating range 0 to 55 C.
- EG4 LifePower4 48 V 100 Ah: charge 56.2 V (56.8 V on newer versions), BMS over-voltage
  protection 58.4 V (60.0 V on newer versions), built-in breaker.

So the "48 V" bus normally sits between 48 and 57 V and can legitimately reach about 61 V.
Anything connected to it must be rated well above 61 V.

| | (a) USB wall adapter on the inverter's AC output | (b) Isolated 48 V to 5 V DC-DC on the battery bus | (c) Own small solar panel and battery |
|---|---|---|---|
| Parts | UL-listed 5 V 2 A or larger USB adapter, cable | Mean Well DDR-15L-5, fuse holder and fuse, DIN rail, wire | 10 W panel, charge controller, small LiFePO4 pack, enclosure |
| Approx. cost | $10 to $15 | $40 to $55 | $70 to $120 |
| Who can install it | Anyone | A person qualified to work on the 48 V battery system | Anyone, but it is a second power system to look after |
| Works when the inverter is off, tripped or in low-battery shutdown | No | Yes, until the battery itself shuts down | Yes |
| Electrical isolation from the battery | Yes (the adapter is isolated) | Yes (4000 VDC, per datasheet) | Yes (separate system) |
| Losses | Adapter about 75 to 80 percent, inverter about 90 percent: 0.6 W at the node costs about 0.85 W. The inverter's own 50 W idle draw is spent anyway because the fridge needs AC all day | Converter about 80 to 85 percent: 0.6 W costs about 0.75 W | Not relevant |
| Main risk | Node goes dark exactly when the power system has a problem. Also stops if someone enables the inverter's power saving mode | A wiring mistake on a 48 V lithium bank is dangerous (see section 5) | Shaded or dirty panel, a second battery to replace, more to steal |
| Verdict | **Use for the first field install** | **Long-term answer** | Not warranted while a 5 kWh battery sits 10 m away |

Why not (c): the only thing a separate solar supply buys is independence from the fridge's
power system, and the long-term plan is to *report on* that power system, so the node needs to
be near it anyway.

### 3.1 The LM2596 modules: stated plainly

The 5-pack on hand is listed as "3.0-40 V to 1.5-35 V". The Texas Instruments LM2596
datasheet gives a maximum operating supply of **40 V** and an absolute maximum of **45 V**.
The battery bus runs 48 to 57 V and can reach 61 V. Connected to that bus an LM2596 module
will fail, and a failed buck converter of this type commonly fails *shorted*, which puts the
full battery voltage on the 5 V wire, the ESP32, and every sensor lead a member of the public
can touch.

The "HV" version (LM2596HV, 60 V) is not acceptable either: 60 V is below the inverter's
60.8 V cut-off, and it is not isolated.

What the LM2596 modules are good for:

- Bench work from a 9 to 24 V supply.
- A second stage after an isolated converter, for example 12 V in, 5 V out.
- Any input of 35 V or less. Set the output to 5.0 to 5.1 V with a multimeter *before*
  connecting the board; they ship set to an arbitrary voltage.

### 3.2 The breakout boards' barrel jacks are also low voltage

The Freenove FNK0091 breakout's jack is marked "Input: 7-12V" (its regulator capacitors are
16 V parts per the schematic). The FNK0101 universal breakout accepts 5 to 12 V. Neither may
see 48 V. In this plan the node is fed regulated 5 V at the screw terminals marked 5V and GND.

## 4. Recommended power wiring

### 4.1 First field install: option (a)

```text
 DRY-GOODS ROOM (indoors, dry)                      FRIDGE SHELTER (outdoors)

 Growatt inverter                                    Hammond 1554H box, glands down
 120 VAC outlet                                     +---------------------------+
      |                                             |  Wago 221 lever splices   |
 [ UL-listed USB adapter, 5 V 2 A ]                 |    +5V ---> "5V" terminal |
      |  USB-A to bare-wire lead                    |    GND ---> "GND" terminal|
      |  (or cut a USB cable: red = +5, black = GND)|  breakout board + ESP32   |
      +--- 18 AWG 2-conductor cable, up to 10 m ----+--> PG9 gland, drip loop   |
           (through the wall, in conduit or loom)   +---------------------------+
```

Notes:

- Keep the adapter indoors. A wall adapter is not rated for a damp location.
- Check on the inverter's display that **power saving mode is disabled** (setting 04; the
  manual says disabled is the default). With it enabled the inverter switches its output off
  at light load and the node would lose power whenever the fridge compressor rests.
- Voltage drop: 18 AWG copper is about 0.021 ohm per metre, so a 10 m run (20 m of conductor)
  is 0.42 ohm. At 0.2 A that is 0.08 V; at a 1 A Walter transmit peak it is 0.42 V, which
  still leaves 4.6 V. For runs over about 10 m, send 12 V instead (see 4.3).
- Add a 1 A fast fuse or a 1.1 A resettable polyfuse in the +5 V wire at the adapter end if the
  cable passes anywhere it can be crushed. A 2 A adapter cannot overheat 18 AWG wire, so this
  is protection for the electronics, not the cable.
- **Do not plug a laptop into the board's USB port while field 5 V is connected** until the
  board's back-feed protection has been checked. Open one lever splice first.

### 4.2 Long term: option (b)

```text
 BATTERY ROOM (behind the wall)                         FRIDGE SHELTER

 48 V positive busbar                                   Hammond 1554H box
   |                                                   +----------------------+
 [ FUSE 2 A, DC rated 80 V or more,  ] <-- within      |                      |
 [ touch-safe holder                 ]     18 cm of    |  +5V --> 5V terminal |
   |  18 AWG red                           the busbar  |  GND --> GND terminal|
   |                                                   |                      |
 +-------------------------------+                     +----------+-----------+
 | Mean Well DDR-15L-5           |                                |
 | IN  18-75 VDC   OUT 5 V 3 A   |---- 18 AWG 2-conductor --------+
 | isolated 4000 VDC, DIN rail   |     (5 V only leaves the room)
 +-------------------------------+
   |  18 AWG black
 48 V negative busbar
```

Parts and reasons:

- **Converter: Mean Well DDR-15L-5.** Input 18 to 75 VDC, output 5 V 3 A, 4000 VDC
  input-to-output isolation, operating range -40 to +85 C, protections for short circuit,
  overload, over-voltage, reversed input and input under-voltage, UL 62368-1, DIN-rail mount.
  About $18 to $28 (Newark listed $27.86 for one). 75 V gives 14 V of margin above the
  inverter's 60.8 V cut-off. Its sister part DDR-15L-12 gives 12 V if a long cable run needs it.
- **Why isolated.** With an isolated converter there is no electrical path from the battery to
  the 5 V side. That matters three ways. First, a non-isolated buck that fails can pass the
  whole battery voltage to the 5 V wire; an isolated one cannot. Second, the node will later be
  wired to the inverter's and battery's RS485 ports, to a metal fridge cabinet, and to a
  laptop over USB during service: with a shared negative those become unplanned current paths
  through thin signal wires. Third, a pinched sensor cable outdoors can then only ever carry
  5 V.
- **Fuse at the source.** The fuse protects the *wire*. It goes in the positive lead within
  about 18 cm (7 in) of where the wire leaves the busbar, so no unprotected wire runs around
  the room. Use a DC-rated part: either a touch-safe DIN-rail holder for 10 x 38 mm fuses with a
  2 A fuse rated 80 VDC or more, or a Littelfuse FKS 80 V blade fuse (3 A is the smallest
  common size) in a Littelfuse FKH 80 V inline holder. **An ordinary automotive blade fuse is
  rated 32 V and must not be used.** The converter draws about 0.4 A at full load on 48 V and
  1.1 A at its minimum input, so 2 to 3 A does not nuisance-blow and is far below what 18 AWG
  can carry.
- **Wire.** 18 AWG stranded copper, 300 V insulation or better, red and black, with crimped
  ring terminals sized for the busbar studs and ferrules at the converter's screw terminals.
- **Where it lives.** On a short DIN rail in the battery room, so only 5 V travels to the
  public side of the wall.

### 4.3 Runs longer than about 10 m

Send 12 V instead of 5 V (DDR-15L-12, or a 12 V wall adapter for option (a)) and plug it into
the breakout board's barrel jack, which is designed for 7 to 12 V and makes 5 V locally. This
halves the current and removes any worry about voltage drop.

## 5. Safety when working on the 48 V battery bus

Read this before option (b). It is the reason option (a) comes first.

- **Who:** the person who installed or maintains the solar system, or a licensed electrician.
  Not a first job for a volunteer. 48 to 61 V DC can deliver a shock through wet skin, and the
  real hazard is **arc and burn**: a 100 Ah lithium bank can drive hundreds of amps into a
  dropped wrench before its protection opens.
- **De-energize:** switch the inverter off, open the battery's own breaker, and confirm with a
  meter that the busbar is dead before touching it. Follow the EG4 manual's procedure for
  connecting and disconnecting DC terminals.
- **Fuse first:** fit the fuse holder to the wire, with the fuse *out*, before the wire goes
  anywhere near the busbar. Insert the fuse last.
- **Tools and jewellery:** insulated tools, no rings, watches or bracelets, one hand at a time
  where practical, eye protection.
- **Torque:** the EG4 manual specifies 60 in-lb (7 N m) for its terminal and busbar bolts. A
  loose high-current joint overheats.
- **Polarity:** check with a meter before connecting the converter, then check 5.0 V at the
  output before connecting the node.
- **Label** the fuse holder: "Door counter node, 2 A, 48 V DC".
- The EG4 manual's own warning applies: the battery's built-in breaker does not replace
  correctly sized protection on each conductor.

## 6. Weatherproofing

### 6.1 The honest state of the art for a hobby outdoor node

A printed part is made of stacked layers with tiny gaps between them. It sheds rain but it is
not sealed: water wicks in along layer lines and through seams over months, and humid air goes
straight through. New Orleans adds sun, heat and wind-driven rain. What works is the same
recipe used for commercial outdoor sensors:

1. A **moulded, gasketed box** with a published IP rating is the weather barrier.
2. **Cable glands** seal each cable. All of them go in the **bottom** face.
3. A **vent plug** with a waterproof breathable membrane lets the box breathe without letting
   liquid in, which stops it sucking moist air past the gasket every time it cools.
4. **Desiccant** and **conformal coating** deal with the humidity that gets in anyway.
5. The 3D-printed part is an **internal carrier** that holds the electronics. It needs to be
   heat-resistant, not waterproof.

### 6.2 The box

**Hammond 1554H2GY**: 180 x 120 x 60 mm, UV-stabilised polycarbonate, grey solid lid,
silicone gasket, stainless lid screws, IP66 and IP68, UL listed Type 4X. About $25 to $35.
Inside it is 172.9 x 108.9 x 54.5 mm with four M3 brass inserts on a 132 x 84 mm pattern,
which is what the printed sled bolts to. Wall-mounting holes are outside the gasket, so
mounting it does not puncture the seal. If more room is wanted, the 1554T2GY is the same
footprint and 90 mm deep and takes the same sled.

Why this one rather than the $18 generic ABS box on the original shopping list:

- It has a published drawing, so the sled can be designed to fit before the box arrives.
- Polycarbonate is UV-stabilised; plain ABS chalks and cracks in Gulf Coast sun.
- Choose the **solid grey lid**, not the clear one. A clear lid turns the box into a
  greenhouse and shows passers-by that there are electronics inside.

Do not use Hammond's steel inner panel (1554HPL). A steel sheet 15 mm behind the ESP32's
antenna hurts the radio. The printed sled replaces it.

### 6.3 Keeping water and condensation out

- **Glands on the bottom face only.** PG7 glands seal cables of about 3 to 6.5 mm (door
  sensor, temperature probe, I2C lead); PG9 seals about 4 to 8 mm (power). Drill with a step
  drill: 12.5 mm for PG7, 15.2 mm for PG9. One cable per gland; a gland cannot seal two.
- **Unused holes** get a blanking plug, never tape.
- **Drip loops:** every cable dips below its gland before rising into it, so water running
  down the cable drips off at the low point.
- **Vent plug:** one M12 x 1.5 membrane vent (for example Amphenol LTW VENT-PS1 series) in
  the bottom face or low on a side.
- **Desiccant:** a 5 to 10 g silica gel pack with a colour indicator, replaced at each
  service visit.
- **Conformal coating:** two thin coats of silicone or acrylic conformal coating (for
  example MG Chemicals 422B) on the breakout board and the dev board. Mask the sockets, pin
  headers, screw-terminal openings, USB ports and buttons first.
- **Gasket:** seat it in its groove, tighten the four lid screws evenly, do not overtighten
  (Hammond specifies 30 to 40 cN m).
- **Mount vertically** on a wall with the long side horizontal and glands down.

### 6.4 Heat

The ESP32-S3 modules with 8 MB PSRAM (both "N8R8" and "N16R8", which covers every board on
hand) are rated by Espressif for **-40 to 65 C ambient**, lower than the 85 C most people
assume. A sealed box in direct New Orleans summer sun can pass 60 C inside. So:

- Mount the box **in permanent shade**: under the shelter roof, on a north-facing surface, off
  the top of the fridge and away from the warm air the fridge blows out.
- Light grey, solid lid, as chosen.
- The firmware can enable "PSRAM ECC" to raise the limit to 85 C at the cost of 1/16 of the
  PSRAM; that is a firmware decision, noted here only so it is not forgotten. The firmware
  does not need PSRAM at all for door counting.
- Walter is rated -40 to 85 C. The Mean Well converter is rated to 85 C but stays indoors.

### 6.5 Where a printed case alone is fine

The printed case in `cad\enclosure` is for the bench, for demos, and for a spot that is
indoors or fully sheltered and shaded, such as inside the dry-goods room.

| Material | Softens at about | Outdoor UV | Use |
|---|---|---|---|
| PLA (on hand: Creality black, white, red) | 55 to 60 C | Poor | Bench and demo only. Deforms in a parked car or in sun |
| PETG (to buy, about $20/kg) | 75 to 80 C | Fair | Sled inside the box; sheltered case |
| ASA (to buy, about $25/kg; the P1S's enclosure suits it) | 95 to 100 C | Good | Anything that sees daylight: sensor shield, reed switch holder |

No PETG or ASA order was found in the owner's purchases, so one spool has to be bought before
anything printed goes to the site. **A PLA sled must not go in the outdoor box.**

## 7. Sensors and cables

### 7.1 Door switch (reed contact)

- **Which part goes where:** the **magnet on the door** (the moving part), the **switch on
  the cabinet** (the fixed part), so the wire never flexes.
- **Where on the fridge:** top edge, on the handle side (the side that swings open). The gap
  there changes the most when the door moves, and it is above spills and out of casual reach.
- **Gap:** the Gebildet contacts on hand are specified for 10 to 15 mm. Aim for 8 mm or less
  with the door closed, and test that the switch releases before the door is open 3 cm.
- **Do not drill.** These contacts are the "recessed" type meant to be pressed into a hole in
  a wooden frame. On the fridge, hold each one in a small printed saddle (print in ASA) stuck
  on with VHB tape.
- **Type:** they are sold as "normally closed", meaning magnet near gives a closed circuit.
  That matches the firmware's logic (door closed reads LOW).
- **Cable:** 22 AWG stranded 2-conductor twisted alarm cable with an outdoor (sunlight
  resistant) jacket. The contact's own lead is only 33 cm, so splice it: solder, then
  adhesive-lined heat-shrink over each wire and over the pair, or gel-filled crimp connectors.
- **Length:** a switch loop like this works over tens of metres provided the input is
  protected as in 7.5. Keep it under 5 m here.

### 7.2 Temperature probe inside the fridge (DS18B20)

- A round 4 mm probe cable pinched in the door will leak cold air and eventually be cut.
  Cross the **door gasket on the hinge side** with a short piece of **flat ribbon cable**
  (three wires of 28 AWG ribbon, under 1 mm thick), taped flat to the cabinet face with
  aluminium or polyimide tape, and spliced to round cable on each side.
- Do not use the drain hole and **do not drill the cabinet or the door**: refrigerant lines
  and wiring run inside the walls, and on many fridges the side walls are the condenser.
- Wire it three-wire (power, ground, data), not "parasite" mode, with a 4.7 k pull-up at
  the board (use 2.2 to 3.3 k if the run exceeds 3 m).
- Put the probe mid-shelf, away from the walls, ideally in a small sealed bottle of water so
  it reports food temperature rather than each puff of warm air.

### 7.3 Weather sensor (BMP280 now, BME280 later)

- The BMP280 modules on hand measure **pressure and temperature only**. Humidity needs a BME280.
- A sensor inside the sealed box reports the box, not the weather. It must sit in **outside
  air, in shade, shielded from rain**: a small louvered radiation shield (a bought one such as
  the Ambient Weather SRS100LX at about $20, or a printed stacked-plate shield in white ASA),
  under the shelter roof on the shaded side and at least a metre from the fridge's warm exhaust.
- Coat the module with conformal coating **except the sensor's metal can and its vent hole**.
- I2C is a short-distance bus. Keep the lead under 1 m, or up to about 3 m with 4-conductor
  shielded cable and the bus speed lowered to 10 to 50 kHz in firmware.
- The printed case has a small vented pocket for the BMP280. That is for demos and sheltered
  use: the reading will run a little warm because the pocket shares a wall with the electronics.

### 7.4 Load cells and RS485 (later phases)

- Each HX711 amplifier should sit close to its load cell or inside the box with the load-cell
  cable kept short and shielded; the signals are microvolts.
- The bare MAX485 modules have no surge protection and no isolation. For the run to the
  inverter or battery, which is on a different ground, use an **isolated RS485 module**
  with built-in transient protection instead.
- Four HX711 boards plus RS485 will not fit comfortably beside the breakout board in the
  1554H; plan on the deeper 1554T or a second box at that stage.

### 7.5 Lightning, surges and static on long leads

Nothing survives a direct strike. The aim is to survive nearby strikes and static, which reach
the board through the long wires acting as antennas.

- Keep sensor leads short, twisted, and away from the AC and PV wiring.
- **Door switch input:** external pull-up of 4.7 to 10 k to 3.3 V, a 1 k resistor in series
  with the GPIO pin, 100 nF from the pin to ground, and a 5 V bidirectional TVS diode from the
  incoming wire to ground at the terminal. The resistor limits surge current into the chip,
  the capacitor removes radio pickup and contact bounce, the TVS clamps spikes.
- **1-Wire and I2C lines:** 100 to 220 ohm in series, plus a low-capacitance TVS array (for
  example Littelfuse SP0503BAHTG) at the box entry.
- **Shielded cable:** connect the shield to ground at the node end only.
- **Do not bond the node's ground to the fridge cabinet.**
- The isolated power supply in either option means a surge on the power cable has no direct
  path into the 5 V rail.

The exact resistor and pin assignments belong to the wiring document; this section only says
what protection to budget for.

## 8. Mounting

In order of preference:

1. **Screw the box to the shelter structure** (wall, post or frame) through its external
   mounting holes, glands down, at about 2 m height, in shade.
2. **VHB tape on the fridge** (3M VHB 5952 or similar): clean both surfaces with isopropyl
   alcohol, apply above 15 C, press hard, allow 72 hours before loading. Use the top or a
   side that does not get warm in operation.
3. **Rubber-coated pot magnets** on the steel cabinet: quick and removable, which also means
   easy to walk off with.

**Never drill, screw or rivet into the refrigerator cabinet or door.**

Radio: do not mount the box flat against the steel cabinet with the antenna end of the board
toward the metal. Keep the board's antenna end at least 20 mm from any metal and pointing away
from the fridge.

## 9. A public, unattended site

- **Be boring:** plain grey box, solid lid, no visible lights, cables in split loom or
  conduit, mounted high.
- **Be honest:** label it. Suggested text: "Hollygrove Community Fridge door counter. Counts
  door openings only. No camera, no microphone." plus a contact. The project's stated value is
  non-surveillance; the label says so to everyone who wonders.
- **Fasteners:** swap the four M4 x 20 lid screws for pin-Torx security screws.
- **Secrets:** today's firmware stores the WiFi password in the board. If the node is stolen
  the password goes with it. Put the node on a guest or IoT-only network, or use a channel key
  that can be changed.
- **Leads:** leave no loop of cable that a hand or a bag can catch.

## 10. Serviceability: how a volunteer swaps it

The electronics live on the printed sled, held in the box by four M3 screws. Keep a **second
sled, assembled and flashed, as a spare** (two Freenove breakouts and several boards are on
hand). Field cables end in **Wago 221 lever splices** inside the box, and short labelled
pigtails run from the splices to the screw terminals, so no screwdriver touches the terminal
blocks in the field.

1. Open the four lid screws.
2. Open the lever on the +5 V splice first.
3. Open the remaining levers. Each cable is labelled DOOR, TEMP, WX or PWR.
4. Undo the four sled screws and lift the sled out.
5. Drop the spare sled in, four screws, close the levers (power last).
6. Check the status light, swap the desiccant pack, check the gasket is seated, close the lid.

A laptop can be plugged into the board's USB port with the lid open for diagnostics (see the
back-feed caution in 4.1).

## 11. Antennas

- **WiFi/Bluetooth (ESP32-S3 on-board antenna):** polycarbonate, PETG and ASA are close to
  transparent at 2.4 GHz. Metal is not: keep the steel fridge, the DIN rail and any metal
  panel out of the 20 mm around the antenna end of the board.
- **Walter LTE-M:** uses a u.FL connector. Either stick a flexible adhesive antenna (the
  datasheet lists the Taoglas FXUB63) inside the plastic lid, away from metal, or fit a
  bulkhead SMA pigtail through the bottom face with an external antenna. FCC conditions for
  the module require the antenna to be at least 20 cm from people.
- **LoRa (Heltec, Meshtastic path):** external 915 MHz antenna through a sealed bulkhead
  connector in the bottom face, with a drip loop in the coax.
- No email or note says whether **WiFi exists at the site**. That is still an open question
  for the connectivity decision and does not change this enclosure plan.

## 12. Bill of materials for the field install

Prices are approximate (November 2026) and should be checked before ordering.

| Item | Example part | Qty | Have or buy | Approx. cost |
|---|---|---|---|---|
| ESP32-S3 dev board | Freenove ESP32-S3 WROOM Lite, or AYWHP DevKitC-1 clone | 1 + 1 spare | Have | $0 |
| Screw-terminal breakout | Freenove FNK0091 (Freenove boards), FNK0101 (DevKitC clone, Walter) | 1 + 1 spare | Have (2 + 1) | $0 |
| Reed contact and magnet | Gebildet recessed, "normally closed" | 1 | Have (5) | $0 |
| BMP280 module, 3.3 V | GY-BMP280 | 1 | Have (5) | $0 |
| Junction box | Hammond 1554H2GY, polycarbonate, grey lid | 1 | Buy | $25 to $35 |
| Cable glands | PG7 x 4, PG9 x 2, plus blanking plugs | 1 set | Buy | $8 to $12 |
| Vent plug | M12 x 1.5 membrane vent, IP67 or better | 1 | Buy | $4 to $8 |
| Desiccant | Indicating silica gel, 5 to 10 g packs | 1 bag | Buy | $6 |
| Conformal coating | MG Chemicals 422B, 55 mL | 1 | Buy | $15 to $18 |
| Filament for the sled | PETG or ASA, 1 kg | 1 | Buy | $20 to $25 |
| Sled screws | M3 x 8 machine screws (Hammond 1591MM100 or any) | 4 | Buy | $5 (assortment) |
| Heat-set inserts and M3 x 8 screws for clamps | M3 x 5.7 mm brass inserts | 4 + 4 | Buy | $8 to $10 |
| USB wall adapter, option (a) | UL-listed 5 V 2 A or larger | 1 | Buy | $10 to $15 |
| USB lead with bare ends | USB-A to pigtail, or a sacrificed cable | 1 | Buy or have | $5 |
| Power cable | 18 AWG 2-conductor, outdoor jacket | 10 m | Buy | $12 to $20 |
| Sensor cable | 22 AWG 2-conductor twisted alarm cable, outdoor jacket | 10 m | Buy | $10 to $15 |
| Flat cable for the gasket crossing | 28 AWG ribbon, a few conductors | 0.3 m | Buy | $6 |
| Lever splices | Wago 221-412 or inline 221-2411 | 10 | Buy | $8 to $10 |
| Input protection parts | 1 k, 4.7 k, 100 nF, 5 V TVS diodes | few | Buy | $8 |
| Splice sealing | Adhesive-lined heat-shrink assortment | 1 | Buy | $8 |
| Mounting | Stainless screws for the shelter, or 3M VHB 5952 | 1 | Buy | $5 to $15 |
| Security lid screws | M4 x 20 pin-Torx, stainless, with bit | 4 | Buy | $8 |
| Split loom or conduit | 10 mm split loom, UV rated | 5 m | Buy | $8 |
| DS18B20 waterproof probe (later) | 1 m stainless probe | 1 | Buy | $5 to $10 |
| Radiation shield (later) | Ambient Weather SRS100LX or printed in ASA | 1 | Buy | $0 to $20 |
| **First install, option (a), subtotal** | | | | **about $175 to $240** |
| Isolated converter, option (b) | Mean Well DDR-15L-5 | 1 | Buy later | $18 to $28 |
| Fuse holder and fuses, option (b) | DIN 10 x 38 mm holder + 2 A DC fuses, or Littelfuse FKH holder + FKS 80 V 3 A | 1 | Buy later | $10 to $15 |
| DIN rail, ring terminals, ferrules, option (b) | 35 mm rail, 150 mm | 1 | Buy later | $10 to $12 |
| **Option (b) add-on subtotal** | | | | **about $40 to $55** |

No batteries, small solar panels, junction box, cable glands or hook-up wire were found in the
owner's past orders, so everything in the "Buy" rows is new. The LM2596 modules are not in
this list on purpose.

## 13. Sources

- Growatt SPF 3000TL LVM user manual (in the project's `research` folder): no-load
  consumption, power saving mode default, 56.4 V charge, 60.8 V high DC cut-off.
- EG4 LifePower4 48 V manual (same folder) and spec sheet:
  <https://eg4electronics.com/wp-content/uploads/2024/04/EG4-LifePower4-48V-Spec-Sheet.pdf>
- Texas Instruments LM2596 datasheet (40 V operating, 45 V absolute maximum):
  <https://www.ti.com/lit/ds/symlink/lm2596.pdf>
- Mean Well DDR-15L-5:
  <https://www.trcelectronics.com/products/mean-well-ddr-15l-5> and
  <https://www.newark.com/mean-well/ddr-15l-5/dc-dc-converter-5v-3a/dp/01AH7056>
- Littelfuse FKH inline holders, compatible with FKS 80 V fuses:
  <https://www.littelfuse.com/products/fuses-overcurrent-protection/fuse-holders-fuse-blocks-accessories/fuse-holders/in-line-fuse-holders/ato-fkh>
- Hammond 1554H drawing (inside dimensions, insert pattern):
  <https://www.hammfg.com/files/parts/pdf/1554H2GY.pdf> and inner panel
  <https://www.hammfg.com/files/parts/pdf/1554HPL.pdf>
- Cable gland sizes: <https://www.adafruit.com/product/762>
- Amphenol LTW M12 vents:
  <https://amphenolltw.com/product-info/Vent/Vent.M12Plastic/VENT-PS1NBK-O8001.html>
- Espressif ESP32-S3-WROOM-1 datasheet (65 C limit for R8 modules), in the vendor folder
  `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\Freenove\Freenove_ESP32_S3_WROOM_Board-main`.
- Freenove breakout boards: <https://store.freenove.com/products/fnk0091> and
  <https://store.freenove.com/products/fnk0101>
- Gebildet reed contact listing data (10 to 15 mm sensing distance, 33 cm lead, magnet near
  closes the circuit), from the retailer listing for the same product family.

Not verified by a primary source tonight, and marked as such where used: the interrupting
rating of any particular fuse, typical softening temperatures of specific filament brands, and
the price ranges.
