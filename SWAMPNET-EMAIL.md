# SwampNet Outreach Email (draft)

**To:** SwampNet (swampnet.info)
**From:** Michael Pyle — michael.b.pyle@gmail.com
**Subject:** Meshtastic help for the Hollygrove Community Fridge — short LoRa link + sensor node

---

Hi SwampNet,

I'm working on a sensor project for the **Hollygrove Community Fridge** and your New Orleans
Meshtastic work looks like exactly the right fit — I'd love your help, and ideally to tie into the
mesh you've already built rather than reinvent it.

**The short version:** we want a small solar/battery-friendly node at the fridge that reports a few
things over LoRa — door-open counts, weather, and the health of the fridge's off-grid power system —
with no WiFi, SIM, or recurring cost. The backend (MQTT + Node-RED) is self-hosted on our own server.

**The link:** the hop is **8430 Apple St ↔ 9000 Oleander**, about **694 m (0.43 mi)**. We can mount
antennas up to ~3 stories at Apple St and ~2 stories at the fridge. By our math it should close
comfortably, but we'd rather trust your field experience than a Fresnel-zone calculation — could we
do a quick RSSI/SNR walk-test before committing to permanent mounts?

**A few things we're hoping you can weigh in on:**
1. Does your existing mesh already reach Hollygrove / the Oleander site? If so, we may not need to
   stand up our own internet gateway at all.
2. Does that ~694 m link look reliable at those mount heights?
3. For the custom sensor data (we want to read the fridge's **Growatt** inverter and **EG4** LiFePO4
   battery over Modbus/RS485, plus some load-cell shelf weights) — in your experience, is it cleaner
   to feed a stock Meshtastic node from a companion ESP32 over its serial API, or to run custom
   firmware? Any experience bridging Growatt/EG4 telemetry onto a mesh would be hugely helpful.
4. Any node hardware / antenna / mounting you'd want us to standardize on to fit your network.

I've put together a one-page technical brief with the full sensor list, the link geometry, and the
power-system details — happy to send it over or walk through it whenever's good for you.

Is there a good way to connect — a meeting, your Signal/Discord, or just email? Thanks so much for
the work you all do; it's a big part of why this felt possible.

Best,
Michael Pyle
michael.b.pyle@gmail.com

---

*Attach or paste `SWAMPNET-BRIEF.md` when sending. Fill in the actual SwampNet contact address /
channel before hitting send.*
