# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small Python tool that tells residents of the City of Casey (Victoria, Australia) which bins to put out and when. It takes a street address, geocodes it, finds the matching council waste-collection area, and returns the collection day, fortnightly week pattern, and which bins go out.

Two entry points wrap the same core logic:
- `main.py` — interactive CLI (`input()` prompt, prints a formatted report).
- `api.py` — Flask REST API exposing the same logic over HTTP.

## Commands

```bash
# Setup (venv already exists at .venv/)
source .venv/bin/activate
pip3 install -r requirements.txt

# Run the CLI
python3 main.py

# Run the API (binds to 0.0.0.0:5001, debug mode on)
python3 api.py

# Smoke-test the API
curl -X POST http://localhost:5001/api/waste-collection \
  -H "Content-Type: application/json" \
  -d '{"address": "2 Patrick Northeast Drive, Narre Warren, VIC"}'
curl http://localhost:5001/api/health
```

There is no test suite, linter, or build step.

## Architecture

The whole program is one function, `get_casey_waste_services(address)`, which runs a 3-step pipeline:

1. **Geocode** — POST the address to OpenStreetMap Nominatim (`nominatim.openstreetmap.org/search`) to get lat/lon. If the full address returns nothing, it retries with just the suburb part (text after the first comma) + ", Victoria, Australia". Postcode is scraped out of the Nominatim `display_name` string (first 4-digit token).
2. **Find collection area** — query the City of Casey OpenDataSoft API (`data.casey.vic.gov.au/api/explore/v2.1/.../waste-collection-area/records`) with a `within_distance` geo-filter on the point. Falls back to a 1000m `geofilter.distance` search if the point isn't inside any polygon. The matched record's `collection` field looks like `"Monday_Week_2"` and is split on `_` into day and week pattern.
3. **Compute schedule** — derive the night-before day, the current fortnightly week, and which bins go out this/next week.

Both external APIs are public and require no auth key. Nominatim requires a `User-Agent` header (set to `CaseyBinLookup/1.0`).

## Things to know before editing

- **The core function is duplicated, not shared.** `get_casey_waste_services` is copy-pasted identically into both `main.py` and `api.py`. Any change to the lookup logic must be applied to BOTH files, or they will diverge. (If asked to refactor, extracting it into a shared module is the obvious improvement — confirm with the user first per surgical-change guidance.)

- **The fortnightly "current week" is hardcoded against a reference date.** In step 3, `ref_date = datetime.date(2025, 10, 20)` anchors the Week 1 / Week 2 alternation. This is an assumption, not data from the council API — if the council's cycle shifts or the reference proves wrong, this is the line to fix. `current_week = 2 if weeks_since_ref % 2 == 0 else 1`.

- **Bin mapping is a fixed convention**, also in step 3: Week 1 areas get Rubbish + Food & Garden (green lid); Week 2 areas get Rubbish + Recycling (yellow lid); Rubbish (red lid) goes out every week.

- **Port drift:** `api.py` runs on port **5001**, but `API_README.md` documents port 5000. Trust the code.

- **Error handling convention:** the core function never raises to callers — it returns a dict with an `"error"` key on any failure. The API layer checks for that key and maps it to HTTP 400; the CLI checks for it and prints the message.
