# Decisions made without owner input: server, database and dashboard

Date: 2026-11-14. The owner was asleep and could not be asked. Each item says what was chosen,
why, what the alternative was, and what to confirm. Nothing was deployed. Work was confined to:

- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\server\`
- `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\docs\decisions\server.md`

## 1. Python with FastAPI, SQLite in WAL mode

- **Chose:** FastAPI and uvicorn (one worker), SQLite file on a bind mount.
- **Why:** tiny data volume (tens of events a day), one writer, trivial backup, no extra container
  on a 4 GB VM that already runs six.
- **Alternative:** Postgres (the VM already has one for NextCloud, but sharing it couples the
  fridge to NextCloud's upgrades) or Flask.
- **Confirm:** nothing needed unless a second writer or high volume is expected.

## 2. Time stored in UTC; local date and hour precomputed at ingest

- **Chose:** `zoneinfo` America/Chicago computes `local_date` and `local_hour`; hours are
  zero-filled by stepping UTC hours, so 23 and 25 hour days are right.
- **Why:** SQLite has no real time-zone support; a test covers a DST boundary.
- **Alternative:** convert in SQL, or store only local time.
- **Confirm:** the time zone is correct for the fridge (New Orleans is Central).

## 3. Privacy: counts publish only after the hour ends

- **Chose:** public numbers include only rows whose event time and receive time are before the
  last top of the hour, and last-heard is floored to the hour. No endpoint returns an event
  timestamp, signal strength or memory figure.
- **Why:** a live counter could reveal when a particular neighbor opened the door; the brief
  requires hourly or coarser aggregates.
- **Alternative:** live numbers with only the hourly buckets visible.
- **Confirm:** the owner is happy that "today" lags by up to an hour. Set
  `FRIDGE_PUBLISH_GRANULARITY_S=0` for live counts.

## 4. Data-quality rules

- **Chose:** an opening under 1 second is not counted (bounce); a door held open counts once and is
  excluded from duration statistics; ranges start at the first day with data; the 7-day average
  appears only for complete days. Raw rows are always stored.
- **Why:** reed-switch bounce would inflate counts; a held-open door would distort averages.
- **Alternative:** count everything, or discard on ingest.
- **Confirm:** the 1 second threshold after real data arrives (`FRIDGE_MIN_OPEN_MS`). The README
  documents each constant.

## 5. A device key only works for its own device id

- **Chose:** the key is matched in constant time, then the body `device_id` must equal the key's
  device, otherwise 401.
- **Why:** one leaked bench key cannot write as the fridge.
- **Alternative:** any valid key may post for any id.
- **Confirm:** nothing, but firmware must send the matching `device_id`.

## 6. Bad items are skipped, not fatal

- **Chose:** an unusable event or reading is skipped and counted as `rejected` in the response; 400 is
  for an unparseable or structurally wrong body. The response has two extra fields
  (`rejected`, `readings_accepted`) beyond the fixed contract.
- **Why:** one bad item must not make the sensor re-send the same batch forever.
- **Alternative:** reject the whole POST.
- **Confirm:** the firmware treats any 200 as "delete these from the queue" and ignores unknown fields.

## 7. Limits

- **Chose:** 64 KB body, 200 events and 500 readings per POST, 120 posts a minute per device, 20
  bad keys a minute per address (address from `CF-Connecting-IP`, kept only in memory).
- **Why:** generous for a sensor that posts every few minutes with at most 20 events.
- **Alternative:** stricter limits, or rate limiting in Caddy (needs a plugin).
- **Confirm:** on the VM, that the address header really arrives (see README, Verify).

## 8. No chart library; hand-written inline SVG

- **Chose:** all charts are SVG drawn by about 600 lines of dependency-free JavaScript, with a table
  view under every chart, keyboard navigation and tooltips.
- **Why:** nothing to pin, no CDN outage, no layout shift, small page; the chart types needed (bars
  with a line, two heatmaps, a calendar) are simple.
- **Alternative:** Chart.js or Observable Plot from cdn.jsdelivr.net at a pinned version.
- **Confirm:** nothing. If the site later wants a library for consistency, only the chart functions change.

## 9. Colours and chart design

- **Chose:** bars `#4A9160`, the 7-day line `#6250D6` (the pair was checked with the dataviz
  validator on white), a one-hue green ramp for heatmaps with a separate gray for zero, text in
  ink colours, Sunday-first weeks, temperatures in Fahrenheit and pressure in inHg for US readers.
- **Why:** matches the HNA sage palette while keeping contrast and colour-blind safety.
- **Alternative:** the site's sage `#8FB596` directly (too light for bars on white).
- **Confirm:** the look on the real site theme.

## 10. Page structure follows the meetings page

- **Chose:** CSS in `include-in-header`, script in `include-after-body`, raw HTML un-indented in a
  `{=html}` block, every class prefixed `fridge-`, no external libraries.
- **Why:** Quarto turns indented raw HTML into code blocks; names like `.card` are taken.
- **Alternative:** a separate `.js` and `.css` served from the site.
- **Confirm:** that Quarto 1.7.29 on the VM renders it the same as 1.8.26 did locally.

## 11. Empty state and sample data

- **Chose:** with no data the page says the counter was just installed and offers `?demo=1`, which
  uses numbers generated in the browser, every card marked SAMPLE DATA, and a banner. Weather,
  pressure, fridge-temperature and shelf-weight sections stay hidden until the API reports data.
- **Why:** production starts empty and fake numbers must never look real.
- **Alternative:** hide the page until data exists.
- **Confirm:** that the demo link may be public.

## 12. Deployment shape

- **Chose:** one container, no published ports, Caddy route `handle /fridge/api/*` placed before the
  catch-all `handle`, path passed through unstripped, secrets in `fridge.env` (mode 600), data in
  `/opt/hollygrove/fridge/data` owned by uid 1000, image built on the VM from `/opt/hollygrove/fridge/app`.
- **Why:** smallest change to a live production stack; only the new service is started.
- **Alternative:** a registry image, or a second Caddy site name.
- **Confirm:** the Dockerfile builds (Docker was not available on the dev PC, so it is untested),
  and the Caddy edit is reloaded with `caddy validate` first.

## 13. Backups

- **Chose:** `app.cli backup` (SQLite online backup with an integrity check) to
  `/opt/hollygrove/fridge/data/backup/`, with a cron suggestion but no cron installed.
- **Why:** a plain file copy of a WAL database can be inconsistent; a cron entry is a persistent
  change to the VM, which needs the owner's approval.
- **Alternative:** copying the file with the service stopped.
- **Confirm:** who wants the nightly job and where copies should go.

## 14. Rate limiter and cache are in memory, one worker

- **Chose:** one uvicorn worker; a 20 second query cache and a one-minute rate window in process memory.
- **Why:** simple and sufficient; they reset on restart, which is harmless.
- **Alternative:** Redis (already on the VM, but another dependency).
- **Confirm:** nothing.
