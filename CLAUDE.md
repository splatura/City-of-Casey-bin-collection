# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **Home Assistant custom integration** (`casey_waste`) that tells residents of the City of Casey (Victoria, Australia) when their next bin collection is, which bins to put out, and when to put them out. The user configures one address; the integration geocodes it once, finds the council collection area, and exposes HA entities for display in built-in cards.

The standalone CLI (`main.py`) and Flask API (`api.py`) that preceded this live in `legacy/` and are **superseded** — don't develop against them. The real project is `custom_components/casey_waste/`.

## Commands

```bash
# Dev setup (venv at .venv/, Home Assistant + test tooling installed)
source .venv/bin/activate
pip install -r requirements-dev.txt

# Tests (pytest.ini sets pythonpath=. and asyncio_mode=auto)
.venv/bin/pytest -q                          # full suite
.venv/bin/pytest tests/test_calc.py -v       # one file
.venv/bin/pytest tests/test_calc.py::test_night_before -v   # one test

# Quick import sanity check for the whole integration
.venv/bin/python -c "import custom_components.casey_waste; print('ok')"
```

There is no build step. Running it for real means loading `custom_components/casey_waste/` into a Home Assistant `config/custom_components/` directory and restarting HA — there is no way to fully exercise the HA wiring from the CLI; the integration tests cover it instead.

## Architecture

Standard HA integration shape. Data flows: **config flow** (one-time geocode + area lookup) → **coordinator** (daily refresh) → **entities** (read coordinator data) → built-in HA cards.

| File (`custom_components/casey_waste/`) | Responsibility |
|---|---|
| `const.py` | Constants: domain, API URLs, bin labels, `FORTNIGHT_ANCHOR`, config-entry keys |
| `calc.py` | **Pure, I/O-free** date/bin logic — the unit-tested core |
| `client.py` | **Async** `aiohttp` calls to Nominatim (geocode) + Casey dataset; raises typed exceptions |
| `coordinator.py` | `DataUpdateCoordinator`, daily; re-queries the area and computes the schedule via `calc` |
| `config_flow.py` | Address setup wizard; geocodes once, stores coords + day/week in the entry |
| `entity.py` / `sensor.py` / `binary_sensor.py` | Entity base (DeviceInfo) + 2 sensors + "bin night" binary sensor |
| `__init__.py` | `async_setup_entry`/`async_unload_entry`; builds coordinator, sets `entry.runtime_data` |
| `translations/en.json` | Config-flow UI strings + entity names |

The `calc.py` / `client.py` split is deliberate: keeping the date math pure (no HTTP, no HA) is what makes the fragile fortnight logic testable without mocking the network. Tests mirror this — `tests/test_calc.py` (pure), `tests/test_client.py` (mocked HTTP via `aioresponses`), `tests/test_config_flow.py` + `tests/test_coordinator.py` (HA harness via `pytest-homeassistant-custom-component`).

## Things to know before editing

- **Async only.** The integration runs in HA's event loop. Never use `requests` or other blocking I/O in the integration code — use `aiohttp` via the HA-provided session (`async_get_clientsession`). This is why `manifest.json` has `"requirements": []` (aiohttp is bundled with HA).

- **The verified collection model lives in `calc.py`/`const.py`.** Confirmed against the council schedule: **Rubbish (red lid) is weekly**; **Recycling (yellow) and Food & Garden/FOGO (green) are fortnightly and alternate.** The council dataset's `collection` field is `"Day_Week_N"` (e.g. `Thursday_Week_2`); the `Week_1`/`Week_2` tag is the area's fortnight phase for recycling. `bins_for_date` ties bins to an actual date: recycling when `current_week(date) == area_pattern`, else green.

- **The fortnight anchor is the one real risk.** The council API gives the day and fortnight *phase* but not which real-world week is current. That's resolved by a single constant, `FORTNIGHT_ANCHOR = date(2025, 10, 20)` in `const.py` (a validated Week-2 Monday). If the council shifts its cycle and dates drift by a week, that constant is the place to fix. Unit tests pin its behaviour across week boundaries.

- **Geocoding happens once, at setup** (in the config flow), and the coordinates are stored in the config entry. The coordinator re-queries only the (cheap) Casey area lookup on its daily refresh; it does not re-geocode. Note: a transient Casey-API outage at refresh time currently makes entities briefly `unavailable` until the next successful refresh (a known trade-off; the entry also stores `collection_day`/`week` which could serve as a fallback if resilience is preferred over freshness).

- **Out of scope (v1):** public-holiday collection shifts. Councils delay pickups after public holidays; this is not modelled.

- **Entity IDs** are derived from `has_entity_name = True` + device name `"Casey Waste"` + translation keys, producing `sensor.casey_waste_next_collection`, `sensor.casey_waste_bins_out`, `binary_sensor.casey_waste_bin_night`. The README's card YAML references these.

- **Error handling convention:** `client.py` raises typed exceptions (`AddressNotFound`, `AreaNotFound`, `CannotConnect`, all `CaseyClientError`). The config flow maps them to user-facing form errors (keys must stay in sync with `translations/en.json`); the coordinator wraps failures in `UpdateFailed`.

- **Before publishing to HACS:** replace the `@github-username` / repo-URL placeholders in `manifest.json`.
