# City of Casey Waste Collection — Home Assistant Integration

**Date:** 2026-05-29
**Status:** Approved design, pending implementation plan

## Goal

Turn the existing standalone Casey waste-lookup script into a Home Assistant
custom integration. After setup, the user gets sensor entities they can drop
into Home Assistant's built-in cards to see, for a single configured location:

- the next bin collection date,
- which bins to put out, and
- when to put them out (the night before).

## Decisions (locked)

| Decision | Choice |
|---|---|
| Card style | Built-in HA cards (Markdown / Entities). No custom frontend. |
| Location input | Typed street address, geocoded via OpenStreetMap Nominatim. |
| Number of locations | One. (Multiple entries are not a goal but the design won't preclude them.) |
| Distribution | HACS-ready (public repo, installable via HACS). |
| Old files | `main.py`, `api.py`, `API_README.md` archived under `legacy/`. |
| HTTP | Async `aiohttp` (HA-bundled). No external runtime dependencies. |
| Public-holiday collection shifts | Out of scope for v1. |

## Approach

Native `custom_components/casey_waste/` integration following the standard HA
pattern: a `config_flow` setup wizard, a shared `DataUpdateCoordinator`, and
entity classes that read from the coordinator. The user's card is just built-in
cards pointed at those entities.

Rejected alternatives:
- **One rich sensor with everything in attributes** — worse for automations and
  the card template gets fiddly.
- **Keep the Flask API + HA RESTful sensor** — requires a separate always-on
  server, adds a failure point, and gives no config UI or HACS install.

## Architecture

### Repo structure

```
city-of-casey-waste-collection/
├── custom_components/casey_waste/
│   ├── __init__.py          # async_setup_entry / async_unload_entry, build coordinator
│   ├── manifest.json        # domain, version, config_flow:true, iot_class, requirements:[]
│   ├── config_flow.py       # setup wizard: address → geocode → validate → confirm
│   ├── coordinator.py       # CaseyWasteCoordinator(DataUpdateCoordinator), daily refresh
│   ├── client.py            # async aiohttp: geocode() + find_collection_area()
│   ├── calc.py              # PURE logic: parse, next date, bins, night-before
│   ├── const.py             # DOMAIN, URLs, bin mappings, FORTNIGHT_ANCHOR
│   ├── sensor.py            # next-collection + bins sensors
│   ├── binary_sensor.py     # "put bins out tonight"
│   └── translations/en.json # config-flow UI text
├── legacy/                  # main.py, api.py, API_README.md (archived, unchanged)
├── tests/test_calc.py       # unit tests for the pure logic
├── hacs.json
├── README.md                # install + ready-to-paste card YAML
└── requirements-dev.txt     # pytest (calc.py is pure → light test deps)
```

### Components and responsibilities

**`client.py`** — async network layer, depends only on an aiohttp session:
- `async geocode(session, address) -> GeoResult(lat, lon)`
  - Tries the full address first; if empty, retries with the suburb portion
    (text after the first comma) + `", Victoria, Australia"`.
  - Sends a `User-Agent` header (Nominatim requires it).
- `async find_collection_area(session, lat, lon) -> AreaResult(collection, postcode)`
  - `within_distance(geo_shape, geom'POINT(lon lat)', 1m)` first, then falls
    back to a 1000 m `geofilter.distance` search.
  - The postcode comes from the dataset record's own `postcode` field (verified
    present), not scraped from the geocoder.
- Raises typed exceptions — `AddressNotFound`, `AreaNotFound`, `CaseyApiError`,
  `CannotConnect` — instead of returning `{"error": ...}` dicts.

**`calc.py`** — pure, no I/O, fully unit-testable:
- `parse_collection("Monday_Week_2") -> ("Monday", "2")`
- `next_collection_date(today, collection_day, week_pattern, anchor) -> date`
- `bins_for(week_pattern, target_week) -> list[str]`
- `night_before(collection_day) -> str`

**`coordinator.py`** — `CaseyWasteCoordinator(DataUpdateCoordinator)`:
- `update_interval = timedelta(days=1)`.
- `_async_update_data()` re-queries the Casey area (cheap; keeps day/week
  current in case the council updates its dataset), then computes the next
  collection date, bins, and night-before via `calc.py`. Returns a small
  dataclass/dict consumed by all entities.
- Network failure → raise `UpdateFailed`; entities keep their last value and
  recover automatically on the next successful refresh.

**`config_flow.py`** — UI-driven setup:
- Single step: a form with an `address` text field.
- On submit: `geocode` + `find_collection_area`. On success, show a confirmation
  (e.g. "Found: Thursday, Week 2, 3805") and create the entry.
- Stores **address, lat, lon, collection_day, week** in the config entry, so
  geocoding runs **once at setup**, never on refresh.
- Maps client exceptions to user-facing form errors: `address_not_found`,
  `area_not_found`, `cannot_connect`.
- Sets a `unique_id` from the coordinates to prevent duplicate entries.

**`__init__.py`** — `async_setup_entry` builds the coordinator, performs the
first refresh, and forwards setup to the `sensor` and `binary_sensor` platforms.
`async_unload_entry` tears them down.

### Entities

| Entity | State | Notes |
|---|---|---|
| `sensor.casey_waste_next_collection` | next pickup date (`device_class: date`) | Attributes: `collection_day`, `week`, `days_until`, `night_before`, `bins` |
| `sensor.casey_waste_bins_out` | `"Rubbish, Recycling"` | Attribute `bins` = list |
| `binary_sensor.casey_waste_bin_night` | `on` when tonight is the put-out night | Serves the "when to put bins out" goal; enables notification automations |

### Data flow

```
config_flow:  address → geocode (Nominatim) → find_collection_area (Casey)
              → store {address, lat, lon, day, week} in config entry
__init__:     create coordinator → first refresh
coordinator:  (daily) re-query Casey area → calc next date/bins/night
entities:     read coordinator.data
card:         built-in Markdown/Entities card → displays entities
```

## The fortnight anchor (primary risk)

The Casey API provides the collection *day* and *which fortnight pattern* an
area follows (`Week_1` / `Week_2`), but not which real-world week is current.
This is resolved with a single documented constant in `const.py`:

```python
FORTNIGHT_ANCHOR = date(2025, 10, 20)  # validated: Week 2 collection week
```

`calc.next_collection_date` uses it to determine the current fortnight. Risks
and mitigations:
- **Risk:** if the council shifts its cycle, all computed dates drift.
- **Mitigation:** the anchor is one well-named constant; unit tests pin the
  expected behaviour across week boundaries; the README documents how to verify
  and adjust it.

**Out of scope (v1):** public-holiday collection shifts. Councils delay
collections in the days after a public holiday; modelling that requires a
holiday calendar and is explicitly excluded.

## Bin mapping (verified against the City of Casey schedule)

Confirmed from the council's published schedule and the live dataset:
- **Rubbish (red lid): weekly** — out on every collection day.
- **Recycling (yellow) and Food & Garden / FOGO (green): fortnightly,
  alternating.** The dataset's `Week_1`/`Week_2` tag is the area's fortnight
  phase for recycling.

Date-tied rule (in `calc.bins_for_date`): for a collection date `d` and area
pattern `P`, the bins are `[Rubbish]` plus `Recycling` when
`current_week(d) == P`, otherwise `Food & Garden`. This matches the validation
point (Thu 23 Oct 2025, `current_week == 2` → a Week-2 area receives recycling).

This corrects the original script, whose bin lists were derived only from the
fixed `Week_N` tag and therefore never alternated week to week.

## Error handling

- `client.py` raises typed exceptions.
- `config_flow.py` maps them to user-facing form errors.
- `coordinator.py` wraps failures in `UpdateFailed`; entities go unavailable and
  recover automatically.
- Address changes are handled by reconfiguring/removing and re-adding the entry.

## Testing

- **Unit tests (`tests/test_calc.py`)** for the pure logic — the
  breakage-prone core:
  - `parse_collection` for valid/`Unknown`/malformed strings.
  - `next_collection_date` across week boundaries and both week patterns.
  - `bins_for` for Week 1, Week 2, and unknown.
  - `night_before` for each day including the Monday→Sunday wrap.
- **`client.py`** — lighter tests with mocked aiohttp responses (geocode
  fallback, area `within_distance` → distance fallback, error paths).
- **Integration wiring** (config_flow, coordinator, entities) — validated
  manually in a running HA instance; steps documented in the README. A full
  `pytest-homeassistant-custom-component` harness is optional/later.

## manifest.json (essentials)

```json
{
  "domain": "casey_waste",
  "name": "City of Casey Waste Collection",
  "version": "0.1.0",
  "config_flow": true,
  "documentation": "<repo url>",
  "issue_tracker": "<repo url>/issues",
  "codeowners": ["@<github-username>"],
  "iot_class": "cloud_polling",
  "requirements": []
}
```

## README card examples (shipped with the integration)

Markdown card (matches the approved mockup):

```yaml
type: markdown
content: |
  ## 🗑️ Bin Collection
  **Next pickup:** {{ states('sensor.casey_waste_next_collection') }}
  **Put bins out:** {{ state_attr('sensor.casey_waste_next_collection','night_before') }} night
  **Bins:** {{ states('sensor.casey_waste_bins_out') }}
```

The README will also include an Entities-card variant and manual-validation
steps.

## Success criteria

1. Integration installs into `custom_components/` and is discoverable via HACS.
2. Setup wizard accepts a Casey-area address, geocodes it, and confirms the
   detected day/week, with clear errors for bad addresses.
3. The three entities populate with correct next-collection date, bins, and
   night-before values.
4. The Markdown card from the README renders the approved layout.
5. `tests/test_calc.py` passes and covers week boundaries, bin mapping, parsing,
   and night-before wrap.
6. `legacy/` contains the original three files unchanged.
```