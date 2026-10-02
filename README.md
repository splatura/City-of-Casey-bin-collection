# City of Casey Waste Collection (Home Assistant)

A Home Assistant custom integration that shows your next bin collection day,
which bins to put out, and a "bin night" reminder sensor for any address in the
City of Casey (Victoria, Australia).

## Collection model

- **Rubbish (red lid):** collected weekly.
- **Recycling (yellow lid)** and **Food & Garden / FOGO (green lid):**
  collected fortnightly, alternating.
- **Glass (purple lid):** collected every four weeks, on every second FOGO day,
  starting November 2026 (no glass collections are shown before then).

## Installation

### HACS (recommended)

1. In HACS → Integrations → ⋮ → **Custom repositories**, add this repository
   with category **Integration**.
2. Install **City of Casey Waste Collection**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/casey_waste/` into your Home Assistant
`config/custom_components/` directory and restart.

## Setup

Settings → Devices & Services → **Add Integration** → search
**City of Casey Waste Collection**. Enter an address within the City of Casey
(e.g. `2 Patrick Northeast Drive, Narre Warren, VIC`). The integration geocodes it,
finds your collection area, and creates these entities:

- `sensor.casey_waste_next_collection` — next collection date, with attributes
  `collection_day`, `week`, `glass_week`, `next_glass_date`, `days_until`,
  `night_before`, `bins`.
- `sensor.casey_waste_bins_out` — e.g. `Rubbish (red lid), Recycling (yellow lid)`
  or `Rubbish (red lid), Food & Garden (green lid), Glass (purple lid)`.
- `binary_sensor.casey_waste_bin_night` — `on` when tonight is the night before
  collection.

> If your entity IDs differ, check **Developer Tools → States**.

## Cards

Markdown card:

```yaml
type: markdown
content: >
  ## 🗑️ Bin Collection

  **Next pickup:** {{ states('sensor.casey_waste_next_collection') }}
  ({{ state_attr('sensor.casey_waste_next_collection','collection_day') }})

  **Put bins out:** {{ state_attr('sensor.casey_waste_next_collection','night_before') }} night

  **Bins:** {{ states('sensor.casey_waste_bins_out') }}

  **Next glass:** {{ state_attr('sensor.casey_waste_next_collection','next_glass_date') }}
```

Entities card:

```yaml
type: entities
title: Bin Collection
entities:
  - entity: sensor.casey_waste_next_collection
  - entity: sensor.casey_waste_bins_out
  - entity: binary_sensor.casey_waste_bin_night
```

## Notes & limitations

- **Public-holiday shifts are not modelled.** Councils delay collections after
  public holidays; this integration does not account for that.
- **Fortnight anchor:** the Week 1 / Week 2 phase is derived from a reference
  date (`FORTNIGHT_ANCHOR` in `const.py`, `2025-10-20`). If the council ever
  shifts its cycle and dates look off by a week, adjust that constant.
- **Glass anchor:** the 4-week glass phase is derived from `GLASS_ANCHOR`
  (`2026-11-23`, a Glass Week 1 Monday) and `GLASS_START` (`2026-11-02`, the
  first week of the glass service), both in `const.py`.

## Development

```bash
pip install -r requirements-dev.txt
pytest -v
```
