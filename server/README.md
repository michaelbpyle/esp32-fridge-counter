# Hollygrove Community Fridge door counter: server

Receives door-opening reports from the fridge sensor, stores them in SQLite, and serves
public, privacy-safe aggregates to the dashboard page at `https://hollygrovenola.org/fridge/`.

Location of this folder: `\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\server\`

Status: built and tested on the dev PC only (47 automated tests, a local run with 7 weeks of
synthetic data, and the dashboard checked in headless Chrome). The `Dockerfile` has NOT been
built, because Docker is not installed on the dev PC. Nothing has been deployed.

## Architecture

```text
 ESP32 door sensor                                   visitors (phones, laptops)
        |  POST /fridge/api/v1/ingest                         |  GET /fridge/ , GET /fridge/api/v1/*
        |  (X-Device-Key)                                     |
        v                                                     v
   Cloudflare (TLS ends here) --> cloudflared --> hollygrove-caddy  (caddy:2-alpine, port 80, no host ports)
                                                      |
                     /fridge/api/*  -----------------+-----------------  everything else
                           |                                                  |
                           v                                                  v
                hollygrove-fridge (this app)                    /srv/site  = site/_site (Quarto output)
                FastAPI + uvicorn, 1 worker                     /fridge/index.html is rendered from
                           |                                    site/fridge/ (hub, sample/ and live/ pages)
                           v
            /data/fridge.db  (SQLite, WAL)  <- bind mount /opt/hollygrove/fridge/data
```

The dashboard is a static page. Its JavaScript calls the public GET endpoints once a minute.
The only component that writes data is the ingest endpoint.

## Files

| Path (relative to this folder) | What it is |
|---|---|
| `app\` | The service: `config.py` (all settings), `db.py` (schema), `timeutil.py`, `ingest.py`, `queries.py`, `main.py` (HTTP), `cli.py` (operator commands) |
| `Dockerfile`, `.dockerignore`, `requirements.txt` | Image build (python:3.12-slim, non-root uid 1000, healthcheck) |
| `fridge.env.example` | Template for the secrets file |
| `deploy\docker-compose.fridge.yml` | Compose service snippet |
| `deploy\Caddyfile.fridge-block.txt` | Caddy block |
| `site-fridge\hub.qmd` | The page at `/fridge/`: two cards linking to the sample and live pages |
| `site-fridge\dashboard.qmd` | The dashboard (Quarto). Source for both `/fridge/sample/` and `/fridge/live/` |
| `site-fridge\build_pages.py` | Generates the three published pages into `site-fridge\out\fridge\` (not committed). `LIVE_DEVICE` there is `bench-01`, the WiFi test unit; set it to `None` when the fridge unit reports |
| `tests\`, `requirements-dev.txt` | pytest suite |
| `tools\load_synthetic.py` | Posts weeks of fake history through the real ingest path (local use only) |
| `screenshots\` | Dashboard in populated, empty, demo (sample data) and API-down states, at 1280 and 390 px |

## Schema

SQLite, WAL mode, one connection per request. Times are stored in UTC; the local date and hour
(America/Chicago) are computed once at ingest with Python `zoneinfo` and stored beside them.
Queries never use SQLite date functions.

- `devices`: one row per device, latest status (`last_seen`, `fw`, `uplink`, `rssi`, `heap`, `door_open`, `queue`, `dropped`, `reset_reason`, `door_total`, `post_count`).
- `events`: one row per opening. `UNIQUE (device_id, boot, n)`. Columns `ts` (UTC epoch), `time_quality` (`device`, `approx`, `received`, `clamped`), `dur_ms` (-1 means held open, NULL means not reported), `local_date`, `local_hour`, `received_at`.
- `readings`: generic sensor data: `device_id`, `sensor`, `metric`, `value`, `ts`, `local_date`. `UNIQUE (device_id, sensor, metric, ts)`. A new sensor or metric needs no schema change.
- `meta`: schema version and time zone.

Raw data is never altered or filtered on the way in; all data-quality rules are applied when
reading.

## API

Base path: `/fridge/api/v1/`.

### POST ingest

Headers: `Content-Type: application/json`, `X-Device-Key: <key>`. Body as in the project contract
(`device_id`, `fw`, `boot_id`, `uplink`, `sent_at`, `uptime_s`, `door_total`, `events[]`,
`readings[]`, `status{}`).

| Result | Meaning |
|---|---|
| 200 `{"ok":true,"accepted":N,"duplicates":M,"rejected":R,"readings_accepted":K,"server_time":epoch}` | Stored. `rejected` counts individual bad items that were skipped. |
| 400 `{"ok":false,"error":"..."}` | Body is not JSON or the top level is malformed (short reason given) |
| 401 | Missing or wrong key, or the key does not belong to the `device_id` in the body |
| 413 | Body over 64 KB |
| 429 | Over 120 posts a minute for a device, or 20 bad keys a minute from one address (`Retry-After` header) |

Rules: duplicates on `(device_id, boot, n)` are ignored and counted. `t` is the UTC epoch of the
opening; `t` of 0 or an implausible value uses receive time minus `age_s` (`approx`); with neither,
receive time (`received`). A time more than 5 minutes in the future is replaced by receive time
(`clamped`). `dur_ms` -1 means held open. Empty `events` and `readings` is a heartbeat; every
accepted POST updates the device row. Up to 200 events and 500 readings per POST (the firmware
sends at most 20 events).

### Public GET endpoints

No authentication. All accept `?device=<id>` (a test device is included only when asked for by
name). Dates are `YYYY-MM-DD` in America/Chicago. Responses carry `Cache-Control: public, max-age=60`.

| Endpoint | Returns |
|---|---|
| `summary` | Today, yesterday, last 7 and 30 days with the previous period, all time, average per day, busiest hour and weekday, first data date, sensor online and last heard, data-through time, which metrics exist, the active rules |
| `hourly?start&end` | Count per local hour, zero-filled (23 and 25 hour days come out right). At most 366 days |
| `daily?start&end` | Count, 7-day average, average open seconds, held-open count, `complete` flag per day, zero-filled |
| `heatmap?start&end` | Weekday by hour averages, plus by-hour and by-weekday averages |
| `durations?start&end` | Open-time histogram, median, mean, 90th percentile, held-open and too-short counts |
| `readings?metric=&sensor=&start&end&bucket=hour\|day` | Min, average and max per bucket for `temp_c`, `pressure_hpa`, `humidity_pct`, `fridge_temp_c`, `weight_g` (or any stored metric) |
| `export.csv?grain=hour\|day&start&end` | The same counts as a download |
| `health` | `{"ok":true,...}`, used by the container healthcheck |

Without `start` and `end`, `hourly` defaults to the last 7 days and the other range endpoints
to the last 30 days. Ranges start no earlier than the first day with data.

Errors: 400 for a bad parameter (short reason), 404 for an unknown device.

## Privacy and data-quality rules

All are constants in `app\config.py`, overridable by environment variable.

- Privacy: the public API returns only counts by the hour or coarser. Individual event timestamps are never returned. In addition, rows only become public after a delay set by `FRIDGE_PUBLISH_GRANULARITY_S`. The code default is 3600 (the top of the next hour). The owner set production to 60 on 2026-11-15, so counts appear about a minute behind; someone watching the page can therefore see a count change within a minute of a door opening, although the charts still show hourly totals only. Device last-heard is floored to the hour. Signal strength, memory and similar device details are not public. Set the value to 0 to publish live. Client addresses are used only in memory for rate limiting and are never stored or logged.
- An opening shorter than 1 second (`FRIDGE_MIN_OPEN_MS=1000`) is treated as a bounce and left out of public counts.
- A door held open (`dur_ms` -1) counts once and is left out of duration statistics.
- Test devices (`FRIDGE_TEST_DEVICES`) are stored but excluded from every public aggregate.
- Ranges start at the first day with data, so there are no fake zeros before installation.
- The 7-day average is shown only for complete days.
- Online means heard from within 40 minutes.

## Run it locally (Windows, Python 3.13)

Two commands from this folder (`I:\Projects\Microcontrollers\esp32-fridge-counter\server`), in
Git Bash. The first creates a virtual environment and runs the tests; the second starts the
service on `http://127.0.0.1:8765` with local keys and the API only:

```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements-dev.txt && .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
FRIDGE_DB_PATH=./data/fridge.db FRIDGE_DEVICE_KEYS=fridge-01:local-dev-key-fridge-01,bench-01:local-dev-key-bench-01 FRIDGE_TEST_DEVICES=bench-01 .venv/Scripts/python.exe -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8765
```

Fake history (7 weeks) through the real ingest path; add `--backdate-db <C:/path/to/fridge.db>`
to make it visible immediately (otherwise it appears at the next hour):

```bash
.venv/Scripts/python.exe tools/load_synthetic.py --url http://127.0.0.1:8765 --device fridge-01 --key local-dev-key-fridge-01 --weeks 7 --readings --backdate-db C:/path/to/data/fridge.db
```

To see the dashboard locally, run `python build_pages.py` in `site-fridge\`, copy `out\fridge\` into a copy of the site
and render it (`quarto render fridge/live/index.qmd`) and start the service with
`FRIDGE_DEV_STATIC_DIR=<copy>/_site` (dev only; never set in production). Then open
`http://127.0.0.1:8765/fridge/`, or `/fridge/?demo=1` for sample data.

## DEPLOY runbook (the `hollygrove` VM)

Run by the lead on the VM. Nothing here has been run. Paths are on the VM.

Existing: `/opt/hollygrove/docker-compose.yml` (project `hollygrove`, network key `hollygrove`),
`/opt/hollygrove/Caddyfile`, `/opt/hollygrove/site/` (Quarto source, rendered to `site/_site`).
Six containers are running and must not be disturbed.

### 1. Back up what will be edited

```bash
cd /opt/hollygrove
cp docker-compose.yml /opt/hollygrove-backups/docker-compose.yml.$(date +%F)   # or wherever backups live
cp Caddyfile /opt/hollygrove-backups/Caddyfile.$(date +%F)
```

### 2. Copy files

| From (`\\TRUENAS\Pyle-TNAS_Individual\Projects\Microcontrollers\esp32-fridge-counter\server\`) | To (VM) |
|---|---|
| `Dockerfile`, `.dockerignore`, `requirements.txt`, `app\` (whole folder) | `/opt/hollygrove/fridge/app/` |
| `fridge.env.example` | `/opt/hollygrove/fridge/fridge.env` (edited, see step 3) |
| `site-fridge\out\fridge\` (after `python build_pages.py`): `index.qmd`, `sample\index.qmd`, `live\index.qmd` | `/opt/hollygrove/site/fridge/` (same three paths) |

```bash
sudo mkdir -p /opt/hollygrove/fridge/app /opt/hollygrove/fridge/data /opt/hollygrove/site/fridge
sudo chown -R 1000:1000 /opt/hollygrove/fridge/data
```

Do not copy `.venv`, `data`, `tests` or `__pycache__`.

### 3. Create the secrets file

```bash
cd /opt/hollygrove/fridge
sudo cp fridge.env.example fridge.env     # if you copied the example here
sudo chmod 600 fridge.env
# generate one key per device (needs the image from step 5 first, or any 40-character random string):
openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
sudoedit fridge.env                        # set FRIDGE_DEVICE_KEYS=fridge-01:<key>,bench-01:<key>
```

Record the `fridge-01` key for the firmware (`include\secrets.h`). Do not paste it in logs or chat.

### 4. Add the compose service

Paste the contents of `deploy\docker-compose.fridge.yml` under `services:` in
`/opt/hollygrove/docker-compose.yml` (same indent as `caddy:`):

```yaml
  fridge:
    build: ./fridge/app
    image: hollygrove-fridge:1
    container_name: hollygrove-fridge
    restart: unless-stopped
    env_file: ./fridge/fridge.env
    volumes:
      - ./fridge/data:/data
    networks:
      - hollygrove
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/fridge/api/v1/health', timeout=4).status == 200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

### 5. Build and start only the new service

```bash
cd /opt/hollygrove
docker compose config -q && echo compose-ok
docker compose up -d --build --no-deps fridge
docker compose ps           # the other six must be unchanged (same "Up" times)
docker logs --tail 20 hollygrove-fridge
docker exec hollygrove-fridge python -m app.cli devices   # "no device has reported yet"
```

`--no-deps` and naming the service keep the other containers untouched.

### 6. Add the Caddy block and reload safely

Edit `/opt/hollygrove/Caddyfile`. Inside the `hollygrovenola.org:80 { ... }` block, add this
ABOVE the final catch-all `handle { root * /srv/site ... }` (order matters; handle blocks are
tried top to bottom, and the catch-all matches everything):

```caddyfile
    handle /fridge/api/* {
        reverse_proxy fridge:8000
    }
```

`/fridge` and `/fridge/` keep falling through to the static catch-all and reach
`_site/fridge/index.html`. Then validate before reloading; a reload with a bad file is refused and
leaves the running config in place:

```bash
docker exec hollygrove-caddy caddy validate --config /etc/caddy/Caddyfile
docker exec hollygrove-caddy caddy reload --config /etc/caddy/Caddyfile
```

No container restart is needed. Because `./Caddyfile` is a single-file bind mount, if an editor
replaced the file (new inode) and Caddy still sees the old text, run
`docker compose restart caddy` instead (about two seconds of downtime for the whole site).

### 7. Render the page

The watcher re-renders a page when its `.qmd` changes. It has twice missed one of these pages (a new
folder is not watched until `hollygrove-render` is restarted, and one of two files copied together
was skipped), so check each page and render any that is stale by hand, for example
`quarto render fridge/live/index.qmd` in `/opt/hollygrove/site`. Check that
`site/_site/fridge/index.html` exists. If `_quarto.yml` lists pages explicitly, no change should
be needed, but confirm the page is built (Quarto 1.7.29 on the VM; the page was rendered with
1.8.26 locally).

### 8. Verify

```bash
docker exec hollygrove-caddy wget -qO- http://fridge:8000/fridge/api/v1/health      # inside the network
curl -s https://hollygrovenola.org/fridge/api/v1/health                            # public path
curl -sI https://hollygrovenola.org/fridge | head -3                               # page, 200 or redirect to /fridge/
curl -s https://hollygrovenola.org/fridge/api/v1/summary | head -c 300             # has_data:false at first
# test ingest with the bench device (stored but never public):
curl -s -X POST https://hollygrovenola.org/fridge/api/v1/ingest \
  -H 'Content-Type: application/json' -H "X-Device-Key: $BENCH_KEY" \
  -d '{"device_id":"bench-01","fw":"test","boot_id":1,"uplink":"wifi","sent_at":'$(date +%s)',"uptime_s":1,"door_total":0,"events":[],"readings":[],"status":{}}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://hollygrovenola.org/fridge/api/v1/ingest -d '{}'   # expect 401
docker exec hollygrove-fridge python -m app.cli devices
```

Then open `https://hollygrovenola.org/fridge/` (empty state, "The counter was just installed") and
`https://hollygrovenola.org/fridge/?demo=1` (sample data with a SAMPLE DATA banner).

One thing only the VM can confirm: the app reads the visitor address from `CF-Connecting-IP`
(set by Cloudflare) for rate limiting. Check in `docker logs` that requests arrive and that bad-key
attempts from one address are limited rather than all sharing one address.

### 9. Roll back

```bash
cd /opt/hollygrove
# remove the handle /fridge/api/* block from Caddyfile (or restore the backup), then:
docker exec hollygrove-caddy caddy validate --config /etc/caddy/Caddyfile && docker exec hollygrove-caddy caddy reload --config /etc/caddy/Caddyfile
docker compose stop fridge && docker compose rm -f fridge
# restore docker-compose.yml from backup; remove site/fridge/ to unpublish the page
```

`/opt/hollygrove/fridge/data/` (the database) is left in place; delete it only on purpose.

### Operating

```bash
docker exec hollygrove-fridge python -m app.cli devices        # last heard, firmware, signal, queue
docker exec hollygrove-fridge python -m app.cli counts         # raw row counts, rule effects
docker exec hollygrove-fridge python -m app.cli genkey         # new random device key
docker logs -f hollygrove-fridge                               # JSON lines
```

Updating the code: copy the new `app\` over `/opt/hollygrove/fridge/app/`, then
`docker compose up -d --build --no-deps fridge`.

## Backups

The database is one file plus its WAL. Do not copy the file while running with plain `cp`.
Use the built-in consistent copy:

```bash
mkdir -p /opt/hollygrove/fridge/data/backup
docker exec hollygrove-fridge python -m app.cli backup /data/backup/fridge-$(date +%F).db
```

Run it nightly from the VM's cron and let the existing backup of `/opt/hollygrove` (or a copy to
`\\TRUENAS\Pyle-TNAS_Backups`) pick the file up. Keep about 14 days. The cron entry is a
persistent change to the VM: agree it with the owner first. Restore: stop the service, replace
`fridge.db` (delete any `fridge.db-wal` and `fridge.db-shm`), start the service.

## Adding a device or sensor

- New device: `docker exec hollygrove-fridge python -m app.cli genkey`, add `id:key` to
  `FRIDGE_DEVICE_KEYS` in `fridge.env` (add the id to `FRIDGE_TEST_DEVICES` if it is a bench
  unit), then `docker compose up -d --no-deps fridge`. The device sends its own `device_id`; a key
  only works for its own id. Public numbers combine all non-test devices.
- New sensor or metric: nothing to change in the service. The device sends `readings` with any
  `sensor` and `metric` name (lowercase letters, digits, underscore, up to 32 characters). It is
  stored immediately and available at `readings?metric=<name>`. To show it on the page, add an
  entry to the `ENV` list and a hidden card in `site-fridge\dashboard.qmd`; the existing five
  metrics (temperature, humidity, pressure, fridge temperature, shelf weight) already have cards that
  appear by themselves once data arrives.
- Changing the time zone: set `FRIDGE_TZ`, then run `python -m app.cli relocalize` in the container.

## State of the deployment (2026-11-21)

- Deployed on the hollygrove VM on 2026-11-14 as container `hollygrove-fridge`. The runbook above was followed, with one change: the pages are now the hub plus `sample/` and `live/`.
- Production settings in `/opt/hollygrove/fridge/fridge.env`: two device keys (`fridge-01`, `bench-01`), `FRIDGE_TEST_DEVICES=bench-01`, `FRIDGE_PUBLISH_GRANULARITY_S=60`.
- Backups: `hollygrove-fridge-backup.timer` copies the database nightly at 01:45 into `fridge/data/backups/fridge-slot-00.db` to `fridge-slot-13.db`; TrueNAS snapshots the VM disk daily at 02:30 and keeps 14 days. Both are on the same storage pool as the VM.
- The live page shows the test unit `bench-01` to the public on purpose during the WiFi test.
- The VM's own record is Session 17 of `\\10.0.10.13\hollygrove\project-log.md`.
