# Shopping list - Hollygrove Community Fridge door counter

Prices checked: 2026-11-14 (US dollars, buyer in New Orleans, Louisiana). Shipping and Louisiana sales tax are not included unless stated.

How to read this file:

- "Price each" is a price seen on the store page or in a current search result on 2026-11-14. Where I could not see a price, the cell says "not confirmed" and the estimated range is beside it. An estimate is a range for planning, not a quote.
- Totals are split into "confirmed" (prices seen) and "unconfirmed" (estimates), so no guess is hidden inside a total.
- "Already owned?" marks what the owner has, so he can skip it. Owned items are still priced.
- Where the link says "search link", it goes to a search for that item, not to one product page.
- Quantities cover one bench unit plus one field unit where a part is needed in both, and the table says so.
- Euro prices are converted at roughly 1 euro = 1.16 dollars and marked "approximate".

## What to buy first

Three totals, each shown two ways: if you own nothing, and given what you already own (owned lines removed).

| Total | If you own nothing | Given what you already own |
| --- | --- | --- |
| (A) Finish the bench demo now (incl. soldering kit, tools, case and demo-door hardware) | $504.05 confirmed + 0 unconfirmed lines (est. $0 to $0) = $504.05 | $417.74 confirmed + 0 unconfirmed lines (est. $0 to $0) = $417.74 |
| (B) Deploy at the fridge with the Walter (first install, USB adapter power; includes the Walter carrier board, headers and terminal blocks) | $431.90 confirmed + 2 unconfirmed lines (est. $1.50 to $4.50) = about $433.40 to $436.40 | $431.90 confirmed + 2 unconfirmed lines (est. $1.50 to $4.50) = about $433.40 to $436.40 |
| (C) Optional sensors for later | $101.53 confirmed + 0 unconfirmed lines (est. $0 to $0) = $101.53 | $91.58 confirmed + 0 unconfirmed lines (est. $0 to $0) = $91.58 |
| (D) Extra, long-term 48 V power (installed by the solar maintainer) | $75.89 confirmed + 1 unconfirmed lines (est. $4 to $10) = about $80 to $86 | $75.89 confirmed + 1 unconfirmed lines (est. $4 to $10) = about $80 to $86 |

Suggested order of buying:

1. Bench demo (A): the soldering kit, M3 inserts and screws, rubber feet, zip ties, a USB adapter, and the resistor kit. The board, reed switch, breakouts and cables are already owned.
2. Field install (B): Walter, antenna, SIM, the Walter carrier board with its headers, terminal blocks, diode and capacitors, the Hammond box, glands, vent plug, cable and splices. Do the "what to measure" items in the notes first.
3. Sensors (C) and long-term 48 V power (D) only when you get to them. Group D parts are fitted by whoever maintains the solar system, not by a volunteer.

Soldering kit choice: **Hakko FX-888DX** ($129.95 at SparkFun). It is a real temperature-controlled station with cheap, widely sold tips and a long record, well above a $20 kit, and far below professional gear. The two runners-up:

| Option | Price seen | Why not first |
| --- | --- | --- |
| Pinecil V2 (pine64.com, community price) | $25.99 iron, plus a 65 W USB-C PD supply (about $30-40, not confirmed) and its M3 insert tip set at $14.99 | Cheapest and good, and its official insert tips are the easiest fit; pick this if budget matters most. Not chosen because the Hakko is a more forgiving bench station for a beginner |
| Weller WE1010NA | $197.50 list at Weller, $158.00 at gotopac.com | Good, but costs $30 to $70 more than the Hakko for the same use |

If you buy the Pinecil instead, delete the Hakko and its insert-tip line and add the three Pinecil items above (about $71 to $81 together, with the PD supply unconfirmed).

Things to avoid in the tools group:

- Cheap all-in-one kits with a fixed-temperature iron and no temperature control.
- Plumbing solder or acid-core flux (it eats electronics). Use rosin-core electronics solder only.
- Heat-set tip kits sold "for any iron": the FX-888DX takes Hakko T18 tips, not the older 900M tips, so check the kit says T18 or FX-888D before ordering.
- Leaded solder is fine for this work, but wash your hands afterwards and keep it away from the food-prep area; the fume fan is not optional.
- Wiping a hot tip on a wet sponge alone; use the brass cleaner.
- Do not put the LM2596 buck modules (already owned) on the 48 V battery. They are 40 V parts. They are not listed in the field lists.
- Do not use an ordinary car blade fuse on the 48 V bus (32 V rated). Use the 80 V rated parts listed.

## Parts tables

## Core electronics (bench)

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ESP32-S3 dev board, 3-pack | the bench computer | 1 | AYWHP 3 PCS ESP-32-S3 Development Board ESP-1-N16R8 (Type-C), 3-pack; in stock (a same-titled listing, B0DG8L5NG5, is $32.99) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0DG8L7MQ9) | $19.99 | $19.99 | Yes (3 boards) |
| Breakout board, ESP32/ESP32-S3 (FNK0091) | screw terminals for the Freenove boards (bench + spare) | 2 | Freenove Breakout Board for ESP32 ESP32-S3, Terminal Block Shield HAT (FNK0091) | [Freenove store (shows out of stock on 2026-11-14; try Amazon)](https://store.freenove.com/products/fnk0091) | $12.99 | $25.98 | Yes (2) |
| Universal breakout board (FNK0101) | screw terminals for the DevKitC-style board | 1 | Freenove Universal Breakout Board for Arduino Nano Raspberry Pi Pico ESP32 Shield HAT (FNK0101); in stock | [Freenove store (seen in browser 2026-11-14)](https://store.freenove.com/products/fnk0101) | $14.99 | $14.99 | Yes (1) |
| USB data cable, USB-A to USB-C, 1 m | program and power the board | 2 | Adafruit USB Type A to Type C Cable - approx 1 meter / 3 ft long | [Adafruit (price from an Adafruit page that lists it)](https://www.adafruit.com/category/33) | $4.95 | $9.90 | Yes |
| Jumper wires | plug-in wiring on the bench (docs call for Dupont-style jumpers; no JST needed) | 1 | Adafruit breadboard jumper wire bundle, 75 flexible stranded wires with stiff ends (product 153) | [Adafruit](https://www.adafruit.com/product/153) | $4.95 | $4.95 | Yes (jumpers; breadboard not repriced) |
| Resistors, 4.7 k, pack of 25 | DS18B20 and door-switch pull-up | 1 | Adafruit Through-Hole Resistors - 4.7K ohm 5% 1/4W - Pack of 25 (2783) | [Adafruit](https://www.adafruit.com/product/2783) | $0.75 | $0.75 | No |
| Resistors, 10 k, pack of 25 | DHT and I2C pull-ups | 1 | Adafruit Through-Hole Resistors - 10K ohm 5% 1/4W - Pack of 25 (2784) | [Adafruit](https://www.adafruit.com/product/2784) | $0.75 | $0.75 | No |
| Resistors, 1 k, pack of 25 | series resistor on the door-switch pin | 1 | Adafruit Through-Hole Resistors - 1.0K ohm 5% 1/4W - Pack of 25 (4294); out of stock at Adafruit on 2026-11-14, any 1 k 1/4 W resistor works | [Adafruit (out of stock) (seen in browser 2026-11-14)](https://www.adafruit.com/product/4294) | $0.75 | $0.75 | No |
| Capacitor kit (includes 100 nF) | 100 nF cap from the door pin to ground | 1 | SparkFun Capacitor Kit (KIT-13698), 115+ capacitors, 10 values | [SparkFun](https://www.sparkfun.com/sparkfun-capacitor-kit.html) | $11.50 | $11.50 | No |
| TVS diodes, 5 V bidirectional | surge protection on the door-switch wire (power doc section 7.5) | 4 | Bourns SMBJ5.0CA, 5 V bidirectional TVS diode, SMB (DO-214AA); price from the DigiKey results list, product page not readable (bot check), stock not seen; buy 4 (bench, field, spares) | [DigiKey (seen in browser 2026-11-14)](https://www.digikey.com/en/products/detail/bourns-inc/SMBJ5-0CA/2254207) | $0.60 | $2.40 | No |

Group subtotal, everything counted: confirmed prices $91.96, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $16.15, plus 0 unconfirmed lines estimated at $0 to $0.

## Deployment board and cellular (Walter, antenna, SIM, carrier board)

The owner chose the bare Walter module with a separate LTE antenna and an IoT SIM. The Walter has no screw terminals, so it plugs into header strips on a prototyping board that carries the field terminals (design: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\cad\enclosure\README.md`).

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Walter module (SoM) | the field board with built-in LTE-M; it has its own USB-C port for flashing | 1 | DPTechnics WALTER SOM, part P000000100 | [DigiKey (price from a search snippet; Mouser cached $77.00); Mouser page linked](https://www.mouser.com/ProductDetail/DPTechnics/P000000100?qs=HFfMDpzxxd0uK7GROMK76w%3D%3D) | $70.73 | $70.73 | No |
| LTE antenna, flexible adhesive | cellular antenna, 96 x 21 x 0.2 mm, stuck on the printed sled's antenna pad (the one the datasheet names) | 1 | Taoglas FXUB63.07.0150C, 150 mm, U.FL | [DigiKey (search link)](https://www.digikey.com/en/search?keywords=FXUB63.07.0150C) | $7.67 | $7.67 | No |
| IoT SIM, 1NCE (10 years, 500 MB) | cellular data for the Walter | 1 | 1NCE IoT Lifetime Flat, 500 MB, 250 SMS, 10 years | [1NCE US](https://www.1nce.com/en-us/1nce-connect/pricing) | $14.00 | $14.00 | No |
| Walter carrier board | proto board the Walter plugs into and the field wires land on (the sled holds it; half-sized board 1609 was out of stock) | 1 | Adafruit Perma-Proto Full-sized Breadboard PCB - Single (1606), 157 x 51 mm, 1.6 mm; 35 in stock | [Adafruit (seen in browser 2026-11-14)](https://www.adafruit.com/product/1606) | $10.95 | $10.95 | No |
| Female header strips | two 14-pin sockets for the Walter (cut from one 36-pin strip, 22 pins left over) | 1 | Adafruit 36-pin 0.1" female header, pack of 5 (598); in stock | [Adafruit (seen in browser 2026-11-14)](https://www.adafruit.com/product/598) | $2.95 | $2.95 | No |
| Terminal blocks, 2-pin | PWR, DOOR, I2C, RS485 and HX711 wiring (7 needed) | 2 | Adafruit Terminal Block - 2-pin 3.5mm - pack of 5 (724); in stock | [Adafruit (seen in browser 2026-11-14)](https://www.adafruit.com/product/724) | $2.95 | $5.90 | No |
| Terminal blocks, 3-pin | 1W, DHT, RS485 and HX711 wiring (4 needed) | 1 | Adafruit Terminal Block - 3-pin 3.5mm - pack of 5 (725); in stock | [Adafruit (seen in browser 2026-11-14)](https://www.adafruit.com/product/725) | $3.95 | $3.95 | No |
| Schottky diode, 3 A | in series with the 5 V so a USB cable in the Walter's USB-C port cannot back-feed the box supply (Walter datasheet 5.1.1; VIN and USB VBUS are tied together) | 1 | 3 A 40 V through-hole Schottky, for example 1N5822 or SB340; no store page could be read (DigiKey showed a bot check) | [DigiKey (search link)](https://www.digikey.com/en/search?keywords=1N5822) | not confirmed (est. $0.50-$1.50) | not confirmed (est. $0.50-$1.50) | No |
| Ceramic capacitors, 10 uF | two at the Walter's VIN pin (datasheet 5.1.1: 2 x 10 uF X5R or X7R) | 2 | 10 uF, 10 V or higher, X5R or X7R ceramic, radial leaded; not priced (the SparkFun capacitor kit above may include 10 uF, not checked) | [DigiKey (search link)](https://www.digikey.com/en/search?keywords=10uF+ceramic+capacitor+radial) | not confirmed (est. $0.50-$1.50) | not confirmed (est. $1-$3) | No |
| OPTION: Soracom SIM from DPTechnics | alternative SIM | option | 250Mb worldwide M2M SIM, EUR 9.95 is about $11.50 (converted, approximate); US shipping not confirmed | [DPTechnics shop (Belgium)](https://shop.dptechnics.com/) | not confirmed (est. $11-12) | not counted | No |
| OPTION: Hologram Hyper SIM | alternative SIM, pay per MB | option | Hologram Hyper eUICC IoT SIM, $3.00 plus data about $0.03 per MB (page said sold out) | [Hologram](https://store.hologram.io/products/hyper-euicc-iot-sim-card-1) | $3.00 | not counted | No |
| OPTION: u.FL to SMA adapter cable | only if you want an outside antenna through the box wall | option | Adafruit SMA to uFL/u.FL/IPX/IPEX RF Adapter Cable (product 851) | [Adafruit](https://www.adafruit.com/product/851) | $3.95 | not counted | No |

Group subtotal, everything counted: confirmed prices $116.15, plus 2 unconfirmed lines estimated at $1.50 to $4.50.  
Group subtotal, only what you do not own: confirmed prices $116.15, plus 2 unconfirmed lines estimated at $1.50 to $4.50.

Alternative, not chosen: the Walter DevKit (part P000000101, module plus antennas, cables and a SIM in one box, about $250 to $290, not confirmed; [Mouser](https://www.mouser.com/new/dptechnics/dptechnics-walter-devkit)).

## Door sensor

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Reed switch, recessed, wired, 5-pack | senses door open or closed (bench demo and field) | 1 | Gebildet 5pcs Recessed Wired Security Window Gate Contact Sensor Alarm Magnetic Reed Switch (B07YFBG27Y); EUR 9.05 seen, about $10.50 converted, approximate | [Amazon (price from search result, shown in euros)](https://www.amazon.com/dp/B07YFBG27Y) | $10.50 | $10.50 | Yes |
| Reed switch cable | run from switch to box (see Wire and connectors) | option | see 22 AWG 2-conductor alarm cable below | - | - | not counted | No |

Group subtotal, everything counted: confirmed prices $10.50, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $0.00, plus 0 unconfirmed lines estimated at $0 to $0.

## Sensors (optional, later)

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BMP280 module, 3.3 V, 5-pack | outside pressure and temperature | 1 | Adafruit BMP280 I2C or SPI Barometric Pressure & Altitude Sensor - STEMMA QT (2651), one module; the owner's generic 5-pack is equivalent | [Adafruit](https://www.adafruit.com/product/2651) | $9.95 | $9.95 | Yes |
| BME280 module | adds humidity to pressure and temperature | 1 | Adafruit BME280 I2C or SPI Temperature Humidity Pressure Sensor - STEMMA QT (2652) | [Adafruit](https://www.adafruit.com/product/2652) | $14.95 | $14.95 | No |
| DS18B20 waterproof probe | fridge temperature (4.7 k resistor included) | 1 | Adafruit Waterproof 1-Wire DS18B20 Digital Temperature Sensor (381); out of stock at Adafruit on 2026-11-14, DigiKey lists it, or Amazon 3-pack with resistors (est. $10-15) | [Adafruit (out of stock)](https://www.adafruit.com/product/381) | $9.95 | $9.95 | No |
| DHT22 / AM2302 module | humidity (optional; BME280 does this better) | 1 | DHT22 / AM2302 temperature-humidity sensor module, 3-pack (pull-up resistor on the board not verified in the listing); shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0D9W5CMHS) | $7.99 | $7.99 | No |
| HX711 amplifier board | reads one shelf scale (up to four) | 4 | SparkFun Load Cell Amplifier - HX711 (SEN-13879) | [SparkFun](https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html) | $4.95 | $19.80 | No |
| Load cell, 50 kg | one per shelf scale (experimental); see notes about 4 cells per platform | 4 | SparkFun Load Sensor - 50kg (Generic); page says Backorder | [SparkFun](https://www.sparkfun.com/load-sensor-50kg-generic.html) | $6.25 | $25.00 | No |
| Isolated RS485 module, 3.3 V logic | talk to the solar inverter (the power doc says use an isolated one) | 1 | Waveshare TTL To RS485 (C) Galvanic isolated Converter, lightning/anti-surge (SKU 27479) | [Waveshare](https://www.waveshare.com/ttl-to-rs485-c.htm) | $6.99 | $6.99 | No |
| OPTION: plain 3.3 V RS485 breakout | bench-only RS485 test | option | SparkFun Transceiver Breakout - RS-485 (BOB-10124, SP3485) | [SparkFun](https://www.sparkfun.com/products/10124) | $12.50 | not counted | No |
| OPTION: radiation shield | buy instead of printing one in white ASA | option | Ambient Weather SRS100LX (the power doc guessed $20; current price is higher) | [Ambient Weather](https://www.ambientweather.com/amwesrpatean.html) | $54.99 | not counted | No |
| 28 AWG ribbon, 4 wire, per metre | flat lead across the fridge door gasket for the probe | 1 | Adafruit silicone-cover stranded-core ribbon, 4 wires 28 AWG, 1 m (product 3890, 4-wire variant) | [Adafruit](https://www.adafruit.com/product/3890) | $1.95 | $1.95 | No |
| Polyimide (Kapton) tape | tape the flat lead flat | 1 | Adafruit High Temperature Polyimide Tape - 1cm wide x 33 meter roll (3057); out of stock on 2026-11-14 | [Adafruit (out of stock)](https://www.adafruit.com/product/3057) | $4.95 | $4.95 | No |

Group subtotal, everything counted: confirmed prices $101.53, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $91.58, plus 0 unconfirmed lines estimated at $0 to $0.

## Power

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| USB wall adapter, bench | power the bench board when not on a laptop | 1 | SparkFun USB Wall Charger - 5V, 2A (TOL-16893); the page does not say UL-listed, so look for a UL mark on the label before using it in the field | [SparkFun](https://www.sparkfun.com/usb-wall-charger-5v-2a.html) | $9.50 | $9.50 | No (check drawer) |
| USB wall adapter, field, UL-listed | first field install, kept indoors on the inverter AC outlet | 1 | SparkFun USB Wall Charger - 5V, 2A (TOL-16893); the page does not say UL-listed, so look for a UL mark on the label before using it in the field | [SparkFun](https://www.sparkfun.com/usb-wall-charger-5v-2a.html) | $9.50 | $9.50 | No |
| USB-A to bare-wire lead | carry 5 V to the node (or cut a USB cable) | 1 | 1 ft 20 AWG USB-A male to pre-tinned red/black pigtail cable, 5-pack; shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0H2S7NWYG) | $8.99 | $8.99 | No |
| Fuse, 1 A fast or 1.1 A resettable | protect the electronics at the adapter end (power doc 4.1) | 1 | 5x20 mm screw-type inline fuse holder with wire plus 150 fast-blow 5x20 glass fuses (15 values; check 1 A is in the kit; rated 250 V AC, fine for 5 V DC); shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B08KZPFRXF) | $9.99 | $9.99 | No |
| Isolated DC-DC converter 48 V to 5 V | long-term power from the battery bus, fitted by whoever maintains the solar system | 1 | Mean Well DDR-15L-5, 18-75 V in, 5 V 3 A out, DIN rail | [Amazon (price from search result; not found on DigiKey)](https://www.amazon.com/Mean-Well-DDR-15L-5-Industrial-Converter/dp/B07H8QFKQ5) | $26.60 | $26.60 | No |
| Fuse holder, 80 V (FKH) | fuse at the battery bus, within 18 cm of the busbar | 1 | Littelfuse / Wickmann FKH holder 178.6152.0002, 80 V, 1-circuit blade, chassis mount; 853 in stock | [DigiKey (page that lists it)](https://www.digikey.com/en/products/detail/littelfuse-inc/0287010-PXCN/2519807) | $4.25 | $4.25 | No |
| Fuse, 80 V DC rated, 3 A | goes in that holder (never an ordinary 32 V car fuse) | 2 | Littelfuse FKS 80 V blade fuse, 3 A | [DigiKey (search link)](https://www.digikey.com/en/search?keywords=FKS+80V+3A) | not confirmed (est. $2-5) | not confirmed (est. $4-10) | No |
| DIN rail, 35 mm, 150-200 mm | holds the converter in the battery room | 1 | IDEC BNDN1000 DIN rail 35 x 10 mm slotted aluminium, 1 m long ($11.58, seen on the Omron PFP-100N2 page); cut to 150 mm with a hacksaw | [DigiKey (price from search result)](https://www.digikey.com/en/products/detail/omron-automation-and-safety/PFP-100N2/369799) | $11.58 | $11.58 | No |
| Ring terminals | land the wires on the busbar studs | 1 | 200 pcs insulated ring terminals, M3/M4/M5/M6/M8/M10, 22-16 / 16-14 / 12-11 AWG; shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0DZ6CMG94) | $8.99 | $8.99 | No |
| Ferrule crimp kit | ferrules for the converter's screw terminals | 1 | Ferrule crimping tool kit, AWG 23-7, 1800-piece class ferrule assortment with square crimper; shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0DRJ9CDNG) | $14.99 | $14.99 | No |
| 18 AWG stranded wire, red and black | short battery-side leads, 300 V insulation or better | 1 | BNTECHGO 18 AWG silicone wire, red and black, 10 ft (assumed 10 ft of each colour), stranded tinned copper | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B01AQOI36M) | $9.48 | $9.48 | No |

Group subtotal, everything counted: confirmed prices $113.87, plus 1 unconfirmed lines estimated at $4 to $10.  
Group subtotal, only what you do not own: confirmed prices $113.87, plus 1 unconfirmed lines estimated at $4 to $10.

## Enclosure and weatherproofing

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Junction box | the weatherproof box for the field node | 1 | Hammond 1554H2GY, 180 x 120 x 60 mm, polycarbonate, grey solid lid | [DigiKey (44 in stock)](https://www.digikey.com/en/products/detail/hammond-manufacturing/1554H2GY/634342) | $33.09 | $33.09 | No |
| Cable gland PG7 | door, probe, weather and I2C cables (3 to 6.5 mm) | 4 | Adafruit Cable Gland PG-7 size (762) | [Adafruit](https://www.adafruit.com/product/762) | $1.95 | $7.80 | No |
| Cable gland PG9 | power cable (4 to 8 mm) | 2 | Adafruit Cable Gland PG-9 size (761) | [Adafruit](https://www.adafruit.com/product/761) | $1.95 | $3.90 | No |
| Blanking plugs | fill unused gland holes | 1 | uxcell 10 pcs PG9 black nylon blanking cap, threaded (PG7 plugs: the one pack seen had no clear price, so only PG9 is priced) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B018HML33U) | $7.99 | $7.99 | No |
| Vent plug, M12 x 1.5 | lets the box breathe without letting liquid in | 1 | Amphenol LTW VENT-PS1NBK-O8001 | [DigiKey](https://www.digikey.com/en/products/detail/amphenol-ltw/VENT-PS1NBK-O8001/7898275) | $3.22 | $3.22 | No |
| Silica gel desiccant, indicating, 5-10 g | soak up moisture inside the box | 1 | wisedry 10 Gram [30 Packs] color-indicating silica gel packets; in stock | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B01MPYB16J) | $13.99 | $13.99 | No |
| Conformal coating | two thin coats on the boards against humidity (the power doc recommends it; it cost more than the doc's $15-18 guess) | 1 | MG Chemicals 422B-55ML silicone conformal coating, 55 mL; 321 in stock | [DigiKey](https://www.digikey.com/en/products/detail/mg-chemicals/422B-55ML/5230613) | $31.02 | $31.02 | No |
| VHB tape | stick the reed-switch saddle and mount points | 1 | 3M VHB Tape 5952, 2 in x 5 yd (narrower rolls exist but were not priced) | [Amazon](https://www.amazon.com/3M-2-5-5952-Permanent-Bonding-Adhesive/dp/B007Y7H63Q) | $26.99 | $26.99 | No |
| Step drill bit, 4-32 mm | drill the 12.5 mm and 15.2 mm gland holes | 1 | 4-32 mm metric 5% cobalt step drill bit, 15 steps (cheaper 3-piece titanium sets exist but do not state 4-32 mm) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0886JKJMD) | $28.49 | $28.49 | No |
| Stainless mounting screws | screw the box to the shelter structure | 1 | Dianrui 280 pcs 304 stainless #6/#8 pan-head screw assortment (no anchors; buy anchors once the wall type is known) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0H2YRBYGL) | $9.99 | $9.99 | No |
| Security lid screws | swap the 4 lid screws for pin-Torx (power doc section 9) | 1 | M4 Torx security screws with bit, M4x8/10/12/16/20, 100 pieces (stainless not stated in the title) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0GLNS7Y3Q) | $9.49 | $9.49 | No |
| Split loom, 10 mm, UV rated | cover cables on the way in | 1 | Electriduct 3/8 in (about 9.5 mm) UV-rated flame-retardant split wire loom, 25 ft | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B07N487Z2R) | $17.05 | $17.05 | No |

Group subtotal, everything counted: confirmed prices $193.02, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $193.02, plus 0 unconfirmed lines estimated at $0 to $0.

## Wire and connectors

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hookup wire, 22 AWG stranded, 6 colours | wire between breakout terminals and sensors (the wiring doc's colour code) | 1 | Adafruit Hook-up Wire Spool Set - 22AWG Stranded-Core - 6 x 25ft (3111) | [Adafruit](https://www.adafruit.com/product/3111) | $19.95 | $19.95 | No |
| 2-conductor 22 AWG twisted alarm cable, outdoor | reed-switch run to the box (keep under 5 m); 25 ft covers it | 1 | 22 Gauge 2 conductor wire 25 ft, UL 2464, 22 AWG (jacket not stated as sunlight-resistant; run it inside the split loom) | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0CN76L8G3) | $8.99 | $8.99 | No |
| 2-conductor 18 AWG outdoor cable | 5 V power run, up to 10 m (33 ft) | 2 | Syston Cable Technology 25 ft 18/2 Black Stranded Tinned Copper low-voltage waterproof UV-resistant cable (8108-SB-BK-25), $11.63 each; 2 rolls = 50 ft | [Home Depot (price from search result)](https://www.homedepot.com/p/Syston-Cable-Technology-25ft-18-2-Black-Stranded-Tinned-Copper-Electrical-Wire-Low-Voltage-Waterproof-Control-Cable-Automotive-RV-and-DC-Marine-8108-SB-BK-25/337854317) | $11.63 | $23.26 | No |
| Lever splices, Wago 221-412 | joins in the box so no screwdriver touches the terminals | 1 | WAGO 221-412/K007-0000 Lever-Nuts splicing connector, 2-conductor, bag of 10 | [DigiKey (price from the DigiKey listing)](https://www.digikey.com/en/products/detail/wago-corporation/221-412-K007-0000/25972935) | $7.67 | $7.67 | No |
| Heat-shrink, adhesive-lined | seal the reed-switch splice | 1 | 400 pcs 3:1 adhesive-lined dual-wall heat-shrink tubing kit | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0BVVMCY86) | $13.99 | $13.99 | No |

Group subtotal, everything counted: confirmed prices $73.86, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $73.86, plus 0 unconfirmed lines estimated at $0 to $0.

## Fasteners

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M3 heat-set inserts, 5.7 mm | threads in the printed case (4 lid + 4 clamps per case, 4 clamps per sled) | 1 | iplusmile 100 pcs M3 brass heat-set inserts, 5.7 mm long x 4.6 mm OD (matches the case design); in stock | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B087NBYF65) | $9.89 | $9.89 | No |
| M3 screw assortment | M3 x 8 and x 10 for lid, clamps and sled | 1 | 720 pcs M3 hex socket screw assortment kit, M3x6/8/10/12/16/20/25/30 mm (socket cap head; material not checked); shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0FG2BRXL3) | $9.99 | $9.99 | No |
| Rubber feet, self-adhesive | stop the demo door sliding | 1 | Adafruit Little Rubber Bumper Feet - Pack of 4 (550) | [Adafruit](https://www.adafruit.com/product/550) | $0.95 | $0.95 | No |
| Zip ties, 2.5 mm x 100-150 mm | demo door foot and cable tie-down | 1 | HS 6 inch black thin nylon zip ties, 18 lb, UV resistant, 100 pack | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0DR8KSVQD) | $5.99 | $5.99 | No |
| US quarters | ballast in the demo door foot (16 x 0.25) | 16 | 16 US quarters, face value | any bank or pocket change | $0.25 | $4.00 | No |

Group subtotal, everything counted: confirmed prices $30.82, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $30.82, plus 0 unconfirmed lines estimated at $0 to $0.

## Filament

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ASA, 1 kg | outdoor printed parts (sled, switch saddle): about 95-100 C softening and good UV resistance; PETG is the minimum alternative | 1 | Bambu Lab ASA, 1.75 mm, 1 kg with spool; $17.99 shown on a sale (typical $29.99), no end date shown | [Bambu Lab US store](https://us.store.bambulab.com/products/asa-filament) | $17.99 | $17.99 | No |
| OPTION: PETG, 1 kg | cheaper sled-only choice, 75-80 C softening | option | Bambu Lab PETG Basic, MSRP $13.99 (1-roll sale price not shown) | [Bambu Lab US store](https://us.store.bambulab.com/products/petg-basic) | $13.99 | not counted | No |
| OPTION: ASA, other brand | if the Bambu sale ends | option | ELEGOO ASA Filament 1.75 mm Deep Black 1 KG (price from a September snippet, may be stale) | [Amazon](https://www.amazon.com/ELEGOO-Filament-Resistant-Functional-Engineering/dp/B0G2L64Z7H) | $19.99 | not counted | No |

Group subtotal, everything counted: confirmed prices $17.99, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $17.99, plus 0 unconfirmed lines estimated at $0 to $0.

## Tools (mid-tier soldering kit and measuring)

| Item | What it is for | Qty | Specific product | Where to buy | Price each | Line total | Already owned? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Soldering station (chosen) | temperature-controlled iron for splices and heat-set inserts | 1 | Hakko FX-888DX soldering station, 70 W, T18-D16 tip included, 120 V (TOL-25926; only 2 left on 2026-11-14) | [SparkFun](https://www.sparkfun.com/hakko-fx-888dx-soldering-station.html) | $129.95 | $129.95 | No |
| Heat-set insert tip set | press M3 inserts into the printed case | 1 | Heat-set insert tips M2-M8 for threaded inserts, listing states Hakko FX-888D / T18 compatible (includes M3); shows as buyable | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0CS662NVK) | $12.99 | $12.99 | No |
| Solder, 63/37 leaded, rosin core, 0.031 in | the solder | 1 | Kester 44 Solder Wire, 63/37 0.031 in, RMA Rosin, 1 oz tube (B00AVLM4SO) | [Amazon](https://www.amazon.com/dp/B00AVLM4SO) | $15.93 | $15.93 | No |
| Flux pen | helps solder flow on splices | 1 | Chip Quik No-Clean Liquid Flux Pen 10 ml (TOL-14579); link is the SparkFun page that lists it | [SparkFun](https://learn.sparkfun.com/tutorials/how-to-solder-through-hole-soldering/soldering-accessories) | $8.50 | $8.50 | No |
| Brass tip cleaner | clean the tip without cooling it | 1 | Hakko Brass Sponge Solder Tip Cleaner (Adafruit 1172) | [Adafruit](https://www.adafruit.com/product/1172) | $10.95 | $10.95 | No |
| Desoldering braid | remove a mistake | 1 | Chemtronics Soder-Wick Rosin 0.06 in (1.5 mm), 25 ft (50-2-25); only 11 left | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B00FS7AQ0Y) | $21.50 | $21.50 | No |
| Solder sucker | suck up a solder blob | 1 | SparkFun Solder Vacuum (TOL-13203) | [SparkFun](https://www.sparkfun.com/products/13203) | $6.95 | $6.95 | No |
| Flush cutters | trim leads and ties | 1 | Hakko CHP-170 Micro Cutter | [DigiKey](https://www.digikey.com/en/products/detail/american-hakko-products-inc/CHP-170/6228793) | $7.30 | $7.30 | No |
| Wire strippers, 30-20 AWG | strip thin wire cleanly | 1 | Hakko CSP-30-1 Wire Stripper (30-20 AWG; check it handles your 22 AWG) | [DigiKey (search link)](https://www.digikey.com/en/search?keywords=CSP-30-1) | $16.21 | $16.21 | No |
| Helping hands / PCB holder | hold work while you solder | 1 | Helping Third Hand Magnifier w/ Magnifying Glass Tool - MZ101 (Adafruit 291) | [Adafruit](https://www.adafruit.com/product/291) | $6.95 | $6.95 | No |
| Silicone soldering mat | protect the table | 1 | SparkFun Insulated Silicone Soldering Mat (TOL-14672); link is the page that lists it | [SparkFun](https://learn.sparkfun.com/tutorials/how-to-solder-through-hole-soldering/soldering-accessories) | $15.95 | $15.95 | No |
| Safety glasses | eye protection (solder spits, wire clippings) | 1 | Clear Safety Glasses, ANSI Z87.1, anti-scratch, 3-pair pack ($16.54) | [Home Depot (price from search result; a category page)](https://www.homedepot.com/b/Safety-Equipment-Protective-Eyewear-Safety-Glasses/ANSI-Compliant/N-5yc1vZc1xtZ1z1a5ho) | $16.54 | $16.54 | No |
| Fume extractor, small fan with carbon filter | keep rosin and lead fumes out of your face | 1 | YIHUA 948DQ V soldering fume extractor with dual activated carbon filters | [Amazon (seen in browser 2026-11-14)](https://www.amazon.com/dp/B0GZYZRHPK) | $29.99 | $29.99 | No |
| Multimeter | check polarity, continuity and 5.0 V before connecting | 1 | AstroAI Digital Multimeter Tester 2000 Counts (AM33D) | [AstroAI](https://www.astroai.com/digital-multimeter-2000-counts-am33d/ap/100071) | $18.99 | $18.99 | No |
| Digital caliper, 6 in | measure boards, cable diameters and box inserts before printing | 1 | Husky 6 in. 3-Mode Digital Fractional Caliper 1467H (a cheaper Neiko 01407A was not priced) | [Home Depot (price from search result)](https://www.homedepot.com/p/Husky-6-in-3-Mode-Digital-Fractional-Caliper-1467H/206007130) | $44.97 | $44.97 | No |

Group subtotal, everything counted: confirmed prices $363.67, plus 0 unconfirmed lines estimated at $0 to $0.  
Group subtotal, only what you do not own: confirmed prices $363.67, plus 0 unconfirmed lines estimated at $0 to $0.

## Notes

### Measure before ordering

- Outside diameter of every cable that goes through a gland (door cable, probe, weather lead, power cable). PG7 seals about 3 to 6.5 mm and PG9 about 4 to 8 mm. The case drawings assume 4.0 to 5.3 mm; those are guesses until you measure the actual cable.
- Length of the power run from the inverter outlet to the box. Under about 10 m, 5 V over 18 AWG is fine; longer needs 12 V (the power doc, section 4.3), which changes the adapter and converter you buy.
- The distance from the reed switch to the box (keep it under 5 m) so 25 ft of alarm cable is enough.
- Row spacing of the DevKitC board (it must be 25.4 mm or less to fit the FNK0101), and the Gebildet switch halves and magnet with the caliper (the demo door depends on them).
- The mounting surface at the shelter, for screw length and anchors.
- Whether the site has WiFi (open question in the power doc); if it does, the Walter and SIM may not be needed yet.
- Which unit the load cells should be: a full shelf platform normally uses four bar cells plus a combiner board per shelf; the doc says "one load cell per shelf", so confirm that design before buying 4 more cells (SparkFun combinator board is $2.75).

### Cheaper substitutes that are fine

- Pinecil V2 instead of the Hakko (see above).
- A different 5 V USB adapter, any UL-listed 2 A one.
- Any 22 AWG 2-conductor cable with an outdoor jacket for the door run, and any 18 AWG 2-conductor outdoor cable for power.
- Any M3 insert and screw brand; any silicone mat, helping hands, glasses, cutters.
- PETG (Bambu PETG Basic, $13.99 list) for the sled inside the box, ASA only for parts in daylight.
- Printing the radiation shield in white ASA instead of buying the $54.99 Ambient Weather unit (the power doc guessed $20, which is out of date).
- A bare 3.3 V RS485 board (SparkFun BOB-10124, $12.50) for bench tests; use the isolated Waveshare board for the real inverter run.
- The DigiKey Hammond box is $33.09, near the top of the doc's $25-$35 range; check Mouser and Newark for a lower price. The conformal coating is $31.02, well above the doc's $15-18 guess; it is optional if the box stays dry.
- A $4.95 Adafruit 75-wire jumper bundle covers the bench wiring; the breadboard was not repriced (owned).
- The Walter DevKit (about $290) costs more than the module plus antenna plus SIM ($92.40 confirmed) and was not chosen; the carrier board, headers and terminal blocks for the bare module add $23.75 confirmed (plus about $1.50 to $4.50 for the diode and capacitors).

### Prices or availability not confirmed

- Every line was re-checked in the owner's browser on 2026-11-14. Amazon pages loaded. DigiKey showed a bot-check page partway through and Mouser returned nothing, so three lines are still unconfirmed. Re-check prices at checkout.
- The unconfirmed lines are the FKS 80 V 3 A fuses (est. $2 to $5 each; Amazon showed no 80 V DC fuse of that type, DigiKey and Mouser could not be read) and, for the Walter carrier, the 3 A Schottky diode (est. $0.50 to $1.50) and the two 10 uF ceramic capacitors (est. $1 to $3). The Adafruit lines for the Walter carrier (Perma-Proto 1606 $10.95, female header 598 $2.95, terminal blocks 724 $2.95 and 725 $3.95) were read from the Adafruit product pages on 2026-11-14 and show in stock; the half-sized Perma-Proto (1609, $4.50) and its 3-pack were out of stock.
- Prices marked "price from search result" were read from a current search snippet, not from the product page itself. The Gebildet switch was seen in euros (EUR 9.05) and converted, so treat $10.50 as approximate.
- M3 inserts: Adafruit sells 4 mm long M3 inserts (4255, $5.95 per 50) but the case design uses 5.7 mm inserts, so they are not a substitute. The pack chosen (iplusmile, 5.7 x 4.6 mm) matches. The earlier candidate B0BVMMBG2N does not state its length, so it was dropped.
- The Adafruit USB adapters were out of stock; the SparkFun 5 V 2 A charger replaces them but its page does not say UL-listed, so check the label.
- The 22 AWG alarm cable chosen is a plain UL 2464 cable, not stated as sunlight-resistant; run it inside the split loom, or choose a UV-rated cable.
- Walter module: $70.73 came from a DigiKey search snippet; a cached Mouser result showed $77.00. Stock not confirmed. The Walter DevKit price is not confirmed (about $250 to $290).
- 1NCE: $14 for the 10-year, 500 MB plan is confirmed on 1NCE's US pricing page. The one-time SIM card fee ($1 to $2 on older price lists), US shipping, and which US carriers carry LTE-M on that SIM were not confirmed. Check LTE-M coverage in New Orleans before relying on any SIM. Hologram's page said sold out; Soracom's US price is not confirmed and its store may not ship to the US.
- Freenove FNK0091 shows out of stock at Freenove (owned already). FNK0101 price did not load.
- Adafruit DS18B20 (381) is out of stock; the DHT22 (385) is discontinued at Adafruit (the AHT20 module, 5183, is $4.50 but is I2C and the firmware expects a DHT-type one-wire part). SparkFun 50 kg load cells are on backorder.
- The FKH 80 V holder used is the chassis-mount 178.6152.0002 (in stock); the inline adapters (178.6191.0001) were out of stock. The FKS 80 V 3 A fuse price was not found.
- Mean Well DDR-15L-5: $26.60 comes from an Amazon search result; DigiKey's page for it was not found. Walter module $70.73 comes from a DigiKey listing card, stock not shown.
- The DIN rail found is a 1 m length at $11.58; you only need about 150 mm.
- Hakko FX-888DX: only 2 left at SparkFun; DigiKey lists FX888DX-010BY at $133.81.
- The Hakko heat-set tip chosen (B0CS662NVK, $12.99) states Hakko FX-888D / T18 compatibility and includes M3; it has not been tested on the owner's station.
- Details the listings did not settle: the DHT22 module's on-board pull-up, a 1 A fuse inside the fuse kit, 10 ft of each colour in the 18 AWG pack, stainless material of the M3 screws and security screws, PG7 blanking plugs (not priced), and anchors for the mounting screws. The TVS price is from the DigiKey results list (product page blocked) and the 1 k resistor pack is out of stock at Adafruit.
- Bambu ASA at $17.99 is a sale price (typical $29.99, a Black Friday promotion; no end date shown). If the sale ends, the line becomes about $30 (adds about $12).
- The Hammond 1554T2GY (deeper box, needed if four HX711 boards and RS485 are added): $41.78 at DigiKey from an earlier snippet, not re-checked, and not in the totals.
- Not listed because not needed: the owned Freenove ESP32-S3 boards (the DevKitC covers the bench), Hammond screw kit 1591MM100 ($13.35 at DigiKey; the M3 assortment covers it), the BMP280 and breadboards beyond one kit each.
