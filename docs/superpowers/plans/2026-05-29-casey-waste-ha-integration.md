# City of Casey Waste Collection — HA Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-ready Home Assistant custom integration that exposes a single configured Casey address's next bin-collection date, which bins to put out, and a "bin night" binary sensor, for display in built-in HA cards.

**Architecture:** Standard HA pattern — a `config_flow` setup wizard geocodes an address once and stores coordinates + the matched collection record; a daily `DataUpdateCoordinator` re-queries the council dataset and computes the schedule via a pure, unit-tested `calc` module; entities read from the coordinator.

**Tech Stack:** Python 3.11+, Home Assistant, async `aiohttp` (HA-bundled, no runtime deps), pytest + aioresponses for tests.

**Verified domain facts (City of Casey):** Rubbish (red lid) is collected **weekly**; Recycling (yellow) and Food & Garden/FOGO (green) are **fortnightly and alternate**. The dataset value is `Day_Week_N` (e.g. `Thursday_Week_2`); records also carry a `postcode` field. Anchor: Mon 2025-10-20 falls in a "Week 2" week (validated: Thu 23 Oct 2025, Week-2 areas received recycling).

---

## File structure

```
city-of-casey-waste-collection/
├── custom_components/casey_waste/
│   ├── __init__.py          # setup/unload entry, runtime_data = coordinator
│   ├── manifest.json        # domain metadata, requirements:[]
│   ├── const.py             # constants, URLs, bin labels, FORTNIGHT_ANCHOR
│   ├── calc.py              # PURE: parse/next-date/bins/night-before
│   ├── client.py            # async aiohttp client + typed exceptions
│   ├── coordinator.py       # DataUpdateCoordinator
│   ├── entity.py            # shared CoordinatorEntity base (DeviceInfo)
│   ├── sensor.py            # next_collection + bins_out sensors
│   ├── binary_sensor.py     # bin_night
│   ├── config_flow.py       # address setup wizard
│   └── translations/en.json # UI strings + entity names
├── legacy/                  # main.py, api.py, API_README.md, requirements.txt (archived)
├── tests/
│   ├── test_calc.py         # pure-logic unit tests
│   └── test_client.py       # mocked-HTTP client tests
├── hacs.json
├── pytest.ini
├── requirements-dev.txt
└── README.md
```

---

### Task 0: Scaffolding, legacy archive, constants, metadata

**Files:**
- Move: `main.py`, `api.py`, `API_README.md`, `requirements.txt` → `legacy/`
- Create: `custom_components/casey_waste/const.py`
- Create: `custom_components/casey_waste/manifest.json`
- Create: `hacs.json`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Create directories and archive legacy files**

```bash
mkdir -p custom_components/casey_waste/translations tests legacy
git mv main.py api.py API_README.md requirements.txt legacy/
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
homeassistant
pytest
pytest-homeassistant-custom-component
aioresponses
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4: Create `custom_components/casey_waste/const.py`**

```python
"""Constants for the City of Casey Waste Collection integration."""
from __future__ import annotations

from datetime import date, timedelta

DOMAIN = "casey_waste"

# External endpoints
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "HomeAssistantCaseyWaste/1.0"
CASEY_WASTE_API = (
    "https://data.casey.vic.gov.au/api/explore/v2.1/catalog/"
    "datasets/waste-collection-area/records"
)

# City of Casey collection model (verified against the council schedule):
#   - Rubbish (red lid): WEEKLY, every collection day.
#   - Recycling (yellow) and Food & Garden / FOGO (green): FORTNIGHTLY, alternating.
# The dataset's Week_1/Week_2 tag is the area's fortnight phase for recycling.
# FORTNIGHT_ANCHOR is a Monday in a "Week 2" collection week
# (validated: Thu 23 Oct 2025, Week-2 areas received recycling).
FORTNIGHT_ANCHOR = date(2025, 10, 20)

DEFAULT_SCAN_INTERVAL = timedelta(days=1)

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# Bin labels
BIN_RUBBISH = "Rubbish (red lid)"
BIN_RECYCLING = "Recycling (yellow lid)"
BIN_GREEN = "Food & Garden (green lid)"

# Config entry data keys
CONF_ADDRESS = "address"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_COLLECTION_DAY = "collection_day"
CONF_WEEK = "week"
CONF_POSTCODE = "postcode"
```

- [ ] **Step 5: Create `custom_components/casey_waste/manifest.json`**

(Replace `github-username` with the real GitHub account before publishing to HACS.)

```json
{
  "domain": "casey_waste",
  "name": "City of Casey Waste Collection",
  "codeowners": ["@github-username"],
  "config_flow": true,
  "documentation": "https://github.com/github-username/city-of-casey-waste-collection",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/github-username/city-of-casey-waste-collection/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Step 6: Create `hacs.json`**

```json
{
  "name": "City of Casey Waste Collection",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

- [ ] **Step 7: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: completes successfully (installs Home Assistant + test tooling; may take a few minutes).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: scaffold casey_waste integration, archive legacy scripts"
```

---

### Task 1: Pure logic (`calc.py`) — TDD

**Files:**
- Test: `tests/test_calc.py`
- Create: `custom_components/casey_waste/calc.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_calc.py`:

```python
"""Unit tests for the pure calc logic."""
from datetime import date

from custom_components.casey_waste import calc
from custom_components.casey_waste.const import (
    BIN_GREEN,
    BIN_RECYCLING,
    BIN_RUBBISH,
    FORTNIGHT_ANCHOR,
)

ANCHOR = FORTNIGHT_ANCHOR  # Monday 2025-10-20, a "Week 2" week


def test_parse_collection_valid():
    assert calc.parse_collection("Thursday_Week_2") == ("Thursday", "2")
    assert calc.parse_collection("Monday_Week_1") == ("Monday", "1")


def test_parse_collection_invalid():
    assert calc.parse_collection("Unknown") == (None, None)
    assert calc.parse_collection("") == (None, None)
    assert calc.parse_collection("Saturday_Week_3") == (None, None)
    assert calc.parse_collection("Funday_Week_1") == (None, None)


def test_current_week_anchor_is_week_2():
    assert calc.current_week(ANCHOR, ANCHOR) == 2
    assert calc.current_week(date(2025, 10, 23), ANCHOR) == 2  # Thu same week
    assert calc.current_week(date(2025, 10, 27), ANCHOR) == 1  # next Monday


def test_next_collection_date_includes_today():
    # Thu 2025-10-23 is a Thursday -> today
    assert calc.next_collection_date(date(2025, 10, 23), "Thursday") == date(2025, 10, 23)


def test_next_collection_date_future():
    # Mon 2025-10-20 -> next Thursday is 2025-10-23
    assert calc.next_collection_date(date(2025, 10, 20), "Thursday") == date(2025, 10, 23)
    # Fri 2025-10-24 -> next Thursday wraps to 2025-10-30
    assert calc.next_collection_date(date(2025, 10, 24), "Thursday") == date(2025, 10, 30)


def test_next_collection_date_unknown_day():
    assert calc.next_collection_date(date(2025, 10, 20), "Notaday") is None


def test_bins_for_date_week2_matching_gets_recycling():
    # current_week == 2, area pattern "2" -> recycling
    assert calc.bins_for_date(date(2025, 10, 23), "2", ANCHOR) == [BIN_RUBBISH, BIN_RECYCLING]


def test_bins_for_date_week1_nonmatching_gets_green():
    # current_week == 2, area pattern "1" -> green
    assert calc.bins_for_date(date(2025, 10, 23), "1", ANCHOR) == [BIN_RUBBISH, BIN_GREEN]


def test_bins_for_date_alternates_next_week():
    # Following week current_week == 1
    assert calc.bins_for_date(date(2025, 10, 30), "2", ANCHOR) == [BIN_RUBBISH, BIN_GREEN]
    assert calc.bins_for_date(date(2025, 10, 30), "1", ANCHOR) == [BIN_RUBBISH, BIN_RECYCLING]


def test_night_before():
    assert calc.night_before("Thursday") == "Wednesday"
    assert calc.night_before("Monday") == "Sunday"  # wraps
    assert calc.night_before("Notaday") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_calc.py -v`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError` (calc functions not defined).

- [ ] **Step 3: Write `custom_components/casey_waste/calc.py`**

```python
"""Pure date and bin computations for Casey waste collection. No I/O."""
from __future__ import annotations

from datetime import date, timedelta

from .const import BIN_GREEN, BIN_RECYCLING, BIN_RUBBISH, DAYS_OF_WEEK


def parse_collection(collection: str) -> tuple[str | None, str | None]:
    """Parse a dataset 'collection' value like 'Monday_Week_2'.

    Returns (day, week) e.g. ('Monday', '2'); (None, None) if unparseable.
    """
    if not collection or "_" not in collection:
        return (None, None)
    parts = collection.split("_")
    if len(parts) != 3 or parts[1] != "Week":
        return (None, None)
    day, week = parts[0], parts[2]
    if day not in DAYS_OF_WEEK or week not in ("1", "2"):
        return (None, None)
    return (day, week)


def current_week(day: date, anchor: date) -> int:
    """Fortnight phase (1 or 2) for the week containing `day`.

    `anchor` must be a Monday that falls in a Week-2 collection week.
    """
    week_index = (day - anchor).days // 7
    return 2 if week_index % 2 == 0 else 1


def next_collection_date(today: date, collection_day: str) -> date | None:
    """Next date on/after `today` matching `collection_day`.

    Rubbish is weekly, so the next collection is the next occurrence of the
    area's weekday (today included when it matches).
    """
    if collection_day not in DAYS_OF_WEEK:
        return None
    target = DAYS_OF_WEEK.index(collection_day)
    offset = (target - today.weekday()) % 7
    return today + timedelta(days=offset)


def bins_for_date(day: date, week_pattern: str, anchor: date) -> list[str]:
    """Bins collected on `day` for an area on `week_pattern` ('1' or '2').

    Rubbish (red) every week; recycling (yellow) when the week's fortnight
    phase matches the area's pattern, otherwise food & garden (green).
    """
    bins = [BIN_RUBBISH]
    if week_pattern in ("1", "2"):
        if current_week(day, anchor) == int(week_pattern):
            bins.append(BIN_RECYCLING)
        else:
            bins.append(BIN_GREEN)
    return bins


def night_before(collection_day: str) -> str | None:
    """The day name before `collection_day` (when to put bins out)."""
    if collection_day not in DAYS_OF_WEEK:
        return None
    idx = DAYS_OF_WEEK.index(collection_day)
    return DAYS_OF_WEEK[(idx - 1) % 7]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_calc.py -v`
Expected: PASS (all 10 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/casey_waste/calc.py tests/test_calc.py
git commit -m "feat: pure calc logic for collection dates and bins"
```

---

### Task 2: Async client (`client.py`) — TDD

**Files:**
- Test: `tests/test_client.py`
- Create: `custom_components/casey_waste/client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_client.py`:

```python
"""Tests for the async Casey client using mocked HTTP."""
import re

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from custom_components.casey_waste import client

NOM = re.compile(r"^https://nominatim\.openstreetmap\.org/search.*$")
CAS = re.compile(r"^https://data\.casey\.vic\.gov\.au/.*$")


async def test_geocode_success():
    with aioresponses() as m:
        m.get(NOM, payload=[{"lat": "-38.1", "lon": "145.3"}])
        async with ClientSession() as session:
            result = await client.geocode(session, "2 Patrick Northeast Drive, Narre Warren")
    assert result.lat == -38.1
    assert result.lon == 145.3


async def test_geocode_falls_back_to_suburb():
    with aioresponses() as m:
        m.get(NOM, payload=[])  # full address: no result
        m.get(NOM, payload=[{"lat": "-38.0", "lon": "145.2"}])  # suburb: hit
        async with ClientSession() as session:
            result = await client.geocode(session, "999 Nowhere St, Narre Warren")
    assert result.lat == -38.0


async def test_geocode_not_found_raises():
    with aioresponses() as m:
        m.get(NOM, payload=[])
        m.get(NOM, payload=[])
        async with ClientSession() as session:
            with pytest.raises(client.AddressNotFound):
                await client.geocode(session, "999 Nowhere St, Narre Warren")


async def test_geocode_connection_error_raises():
    with aioresponses() as m:
        m.get(NOM, exception=ConnectionError("boom"))
        async with ClientSession() as session:
            with pytest.raises(client.CannotConnect):
                await client.geocode(session, "2 Patrick Northeast Drive")


async def test_find_area_within_distance():
    with aioresponses() as m:
        m.get(CAS, payload={"results": [{"collection": "Thursday_Week_2", "postcode": 3980}]})
        async with ClientSession() as session:
            area = await client.find_collection_area(session, -38.1, 145.3)
    assert area.collection == "Thursday_Week_2"
    assert area.postcode == "3980"


async def test_find_area_falls_back_to_distance():
    with aioresponses() as m:
        m.get(CAS, payload={"results": []})  # within_distance: empty
        m.get(CAS, payload={"results": [{"collection": "Monday_Week_1", "postcode": 3805}]})
        async with ClientSession() as session:
            area = await client.find_collection_area(session, -38.1, 145.3)
    assert area.collection == "Monday_Week_1"


async def test_find_area_none_raises():
    with aioresponses() as m:
        m.get(CAS, payload={"results": []})
        m.get(CAS, payload={"results": []})
        async with ClientSession() as session:
            with pytest.raises(client.AreaNotFound):
                await client.find_collection_area(session, -38.1, 145.3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_client.py -v`
Expected: FAIL — `client.geocode` / exceptions not defined.

- [ ] **Step 3: Write `custom_components/casey_waste/client.py`**

```python
"""Async API client for geocoding and the City of Casey waste dataset."""
from __future__ import annotations

from dataclasses import dataclass

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import CASEY_WASTE_API, NOMINATIM_URL, NOMINATIM_USER_AGENT

_TIMEOUT = ClientTimeout(total=15)


class CaseyClientError(Exception):
    """Base error for the Casey client."""


class CannotConnect(CaseyClientError):
    """An upstream request failed or timed out."""


class AddressNotFound(CaseyClientError):
    """Geocoding produced no usable result."""


class AreaNotFound(CaseyClientError):
    """No Casey collection area contains the point."""


@dataclass
class GeoResult:
    lat: float
    lon: float


@dataclass
class AreaResult:
    collection: str
    postcode: str | None


async def geocode(session: ClientSession, address: str) -> GeoResult:
    """Geocode `address` via Nominatim, retrying with the suburb on failure."""
    result = await _geocode_query(session, address)
    if result is None and "," in address:
        suburb = address.split(",")[1].strip() + ", Victoria, Australia"
        result = await _geocode_query(session, suburb)
    if result is None:
        raise AddressNotFound(address)
    return result


async def _geocode_query(session: ClientSession, query: str) -> GeoResult | None:
    params = {"format": "json", "q": query, "limit": 1}
    headers = {"User-Agent": NOMINATIM_USER_AGENT}
    try:
        async with session.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (ClientError, ConnectionError, TimeoutError) as err:
        raise CannotConnect(str(err)) from err
    if not data:
        return None
    return GeoResult(lat=float(data[0]["lat"]), lon=float(data[0]["lon"]))


async def find_collection_area(
    session: ClientSession, lat: float, lon: float
) -> AreaResult:
    """Find the Casey collection area containing (lat, lon)."""
    record = await _area_query(
        session,
        {
            "where": f"within_distance(geo_shape, geom'POINT({lon} {lat})', 1m)",
            "limit": 1,
        },
    )
    if record is None:
        record = await _area_query(
            session, {"geofilter.distance": f"{lat},{lon},1000", "limit": 1}
        )
    if record is None:
        raise AreaNotFound(f"{lat},{lon}")
    postcode = record.get("postcode")
    return AreaResult(
        collection=record.get("collection", ""),
        postcode=str(postcode) if postcode is not None else None,
    )


async def _area_query(session: ClientSession, params: dict) -> dict | None:
    try:
        async with session.get(
            CASEY_WASTE_API, params=params, timeout=_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (ClientError, ConnectionError, TimeoutError) as err:
        raise CannotConnect(str(err)) from err
    results = data.get("results") or []
    return results[0] if results else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_client.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/casey_waste/client.py tests/test_client.py
git commit -m "feat: async aiohttp client for geocoding and Casey dataset"
```

---

### Task 3: Coordinator (`coordinator.py`)

**Files:**
- Create: `custom_components/casey_waste/coordinator.py`

No unit test — this is HA glue, verified by import smoke test now and by manual HA load in Task 8.

- [ ] **Step 1: Write `custom_components/casey_waste/coordinator.py`**

```python
"""DataUpdateCoordinator for Casey waste collection."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .calc import bins_for_date, next_collection_date, night_before, parse_collection
from .client import CaseyClientError, find_collection_area
from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FORTNIGHT_ANCHOR,
)

LOGGER = logging.getLogger(__package__)


@dataclass
class CaseyWasteData:
    collection_day: str
    week: str
    next_date: date
    bins: list[str]
    night_before: str
    days_until: int


class CaseyWasteCoordinator(DataUpdateCoordinator[CaseyWasteData]):
    """Coordinator that refreshes the collection schedule daily."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._entry = entry
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> CaseyWasteData:
        lat = self._entry.data[CONF_LATITUDE]
        lon = self._entry.data[CONF_LONGITUDE]
        try:
            area = await find_collection_area(self._session, lat, lon)
        except CaseyClientError as err:
            raise UpdateFailed(str(err)) from err

        day, week = parse_collection(area.collection)
        if day is None or week is None:
            raise UpdateFailed(f"Unparseable collection value: {area.collection!r}")

        today = dt_util.now().date()
        next_date = next_collection_date(today, day)
        if next_date is None:
            raise UpdateFailed(f"Unknown collection day: {day!r}")

        return CaseyWasteData(
            collection_day=day,
            week=week,
            next_date=next_date,
            bins=bins_for_date(next_date, week, FORTNIGHT_ANCHOR),
            night_before=night_before(day),
            days_until=(next_date - today).days,
        )
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `python -c "from custom_components.casey_waste import coordinator; print('ok')"`
Expected: prints `ok` (no import errors).

- [ ] **Step 3: Commit**

```bash
git add custom_components/casey_waste/coordinator.py
git commit -m "feat: data update coordinator computing daily schedule"
```

---

### Task 4: Entity base + sensors + binary sensor

**Files:**
- Create: `custom_components/casey_waste/entity.py`
- Create: `custom_components/casey_waste/sensor.py`
- Create: `custom_components/casey_waste/binary_sensor.py`

- [ ] **Step 1: Write `custom_components/casey_waste/entity.py`**

```python
"""Shared entity base for Casey waste collection."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CaseyWasteCoordinator


class CaseyWasteEntity(CoordinatorEntity[CaseyWasteCoordinator]):
    """Base entity wiring DeviceInfo and entity naming."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CaseyWasteCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Casey Waste",
            manufacturer="City of Casey",
            entry_type=DeviceEntryType.SERVICE,
        )
```

Note: device name `"Casey Waste"` + entity translation keys yield entity IDs
`sensor.casey_waste_next_collection`, `sensor.casey_waste_bins_out`,
`binary_sensor.casey_waste_bin_night`.

- [ ] **Step 2: Write `custom_components/casey_waste/sensor.py`**

```python
"""Sensors for Casey waste collection."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import CaseyWasteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [NextCollectionSensor(coordinator, entry), BinsOutSensor(coordinator, entry)]
    )


class NextCollectionSensor(CaseyWasteEntity, SensorEntity):
    _attr_translation_key = "next_collection"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_collection"

    @property
    def native_value(self):
        return self.coordinator.data.next_date

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "collection_day": data.collection_day,
            "week": data.week,
            "days_until": data.days_until,
            "night_before": data.night_before,
            "bins": data.bins,
        }


class BinsOutSensor(CaseyWasteEntity, SensorEntity):
    _attr_translation_key = "bins_out"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bins_out"

    @property
    def native_value(self):
        return ", ".join(self.coordinator.data.bins)

    @property
    def extra_state_attributes(self):
        return {"bins": self.coordinator.data.bins}
```

- [ ] **Step 3: Write `custom_components/casey_waste/binary_sensor.py`**

```python
"""Binary sensor: put bins out tonight."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import CaseyWasteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BinNightSensor(entry.runtime_data, entry)])


class BinNightSensor(CaseyWasteEntity, BinarySensorEntity):
    _attr_translation_key = "bin_night"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bin_night"

    @property
    def is_on(self) -> bool:
        # Tonight is the night before collection when the next pickup is tomorrow.
        return self.coordinator.data.days_until == 1
```

- [ ] **Step 4: Verify imports**

Run: `python -c "from custom_components.casey_waste import sensor, binary_sensor, entity; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/casey_waste/entity.py custom_components/casey_waste/sensor.py custom_components/casey_waste/binary_sensor.py
git commit -m "feat: device entity base, sensors, and bin-night binary sensor"
```

---

### Task 5: Config flow + translations

**Files:**
- Create: `custom_components/casey_waste/config_flow.py`
- Create: `custom_components/casey_waste/translations/en.json`

- [ ] **Step 1: Write `custom_components/casey_waste/config_flow.py`**

```python
"""Config flow for City of Casey Waste Collection."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .calc import parse_collection
from .client import (
    AddressNotFound,
    AreaNotFound,
    CannotConnect,
    find_collection_area,
    geocode,
)
from .const import (
    CONF_ADDRESS,
    CONF_COLLECTION_DAY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POSTCODE,
    CONF_WEEK,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_ADDRESS): str})


class CaseyWasteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the address setup wizard."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            session = async_get_clientsession(self.hass)
            try:
                geo = await geocode(session, address)
                area = await find_collection_area(session, geo.lat, geo.lon)
            except AddressNotFound:
                errors["base"] = "address_not_found"
            except AreaNotFound:
                errors["base"] = "area_not_found"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                day, week = parse_collection(area.collection)
                if day is None or week is None:
                    errors["base"] = "area_not_found"
                else:
                    await self.async_set_unique_id(f"{geo.lat:.5f},{geo.lon:.5f}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=address,
                        data={
                            CONF_ADDRESS: address,
                            CONF_LATITUDE: geo.lat,
                            CONF_LONGITUDE: geo.lon,
                            CONF_COLLECTION_DAY: day,
                            CONF_WEEK: week,
                            CONF_POSTCODE: area.postcode,
                        },
                    )
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
```

- [ ] **Step 2: Write `custom_components/casey_waste/translations/en.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "City of Casey Waste Collection",
        "description": "Enter an address within the City of Casey.",
        "data": {
          "address": "Address"
        }
      }
    },
    "error": {
      "address_not_found": "Address could not be found. Try including the suburb.",
      "area_not_found": "No City of Casey collection area was found for that address.",
      "cannot_connect": "Could not connect to the lookup services. Please try again."
    },
    "abort": {
      "already_configured": "This location is already configured."
    }
  },
  "entity": {
    "sensor": {
      "next_collection": { "name": "Next collection" },
      "bins_out": { "name": "Bins out" }
    },
    "binary_sensor": {
      "bin_night": { "name": "Bin night" }
    }
  }
}
```

- [ ] **Step 3: Verify config flow imports**

Run: `python -c "from custom_components.casey_waste import config_flow; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add custom_components/casey_waste/config_flow.py custom_components/casey_waste/translations/en.json
git commit -m "feat: address config flow and UI translations"
```

---

### Task 6: Integration entry points (`__init__.py`)

**Files:**
- Create: `custom_components/casey_waste/__init__.py`

- [ ] **Step 1: Write `custom_components/casey_waste/__init__.py`**

```python
"""City of Casey Waste Collection integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import CaseyWasteCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type CaseyWasteConfigEntry = ConfigEntry[CaseyWasteCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CaseyWasteConfigEntry) -> bool:
    """Set up Casey waste from a config entry."""
    coordinator = CaseyWasteCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CaseyWasteConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- [ ] **Step 2: Verify the whole package imports**

Run: `python -c "import custom_components.casey_waste; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS (17 tests from Tasks 1 and 2).

- [ ] **Step 4: Commit**

```bash
git add custom_components/casey_waste/__init__.py
git commit -m "feat: integration setup/unload entry points"
```

---

### Task 7: README with install + card examples

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# City of Casey Waste Collection (Home Assistant)

A Home Assistant custom integration that shows your next bin collection day,
which bins to put out, and a "bin night" reminder sensor for any address in the
City of Casey (Victoria, Australia).

## Collection model

- **Rubbish (red lid):** collected weekly.
- **Recycling (yellow lid)** and **Food & Garden / FOGO (green lid):**
  collected fortnightly, alternating.

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
  `collection_day`, `week`, `days_until`, `night_before`, `bins`.
- `sensor.casey_waste_bins_out` — e.g. `Rubbish (red lid), Recycling (yellow lid)`.
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

## Development

```bash
pip install -r requirements-dev.txt
pytest -v
```
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with install, setup, and card examples"
```

---

### Task 8: Manual Home Assistant validation

No code. Validate the wiring in a real HA instance (the parts not covered by unit tests).

- [ ] **Step 1: Load the integration**

Copy `custom_components/casey_waste/` into a dev HA `config/custom_components/`
(or symlink), restart HA.
Expected: no errors in the log mentioning `casey_waste`.

- [ ] **Step 2: Run the config flow**

Settings → Devices & Services → Add Integration → **City of Casey Waste
Collection** → enter a known Casey address (e.g. `2 Patrick Northeast Drive,
Narre Warren, VIC`).
Expected: entry is created; a **Casey Waste** device appears with three entities.

- [ ] **Step 3: Verify entity values**

Developer Tools → States.
Expected:
- `sensor.casey_waste_next_collection` = a future/today date; attributes include
  `collection_day`, `bins`, `night_before`, `days_until`.
- `sensor.casey_waste_bins_out` contains `Rubbish (red lid)` plus exactly one of
  recycling/green.
- `binary_sensor.casey_waste_bin_night` is `on` only when `days_until == 1`.

- [ ] **Step 4: Verify error handling**

Add another entry with a nonsense address (e.g. `zzzzz`).
Expected: the form shows the `address_not_found` error rather than crashing.

- [ ] **Step 5: Verify the card**

Add the Markdown card from the README to a dashboard.
Expected: renders next pickup, put-out night, and bins.

- [ ] **Step 6: Final commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: adjustments from manual HA validation"
```

---

## Self-review notes

- **Spec coverage:** config flow (Task 5), coordinator/daily refresh (Task 3),
  three entities (Task 4), pure calc + tests (Task 1), client + tests (Task 2),
  manifest/hacs/HACS-ready (Task 0), README cards (Task 7), legacy archive
  (Task 0), manual validation (Task 8). Public-holiday shifts explicitly
  excluded and documented in README.
- **Anchor risk** isolated to one constant (`const.py`) and documented in README.
- **Entity IDs** in the README match the `has_entity_name` + device-name
  (`Casey Waste`) + translation-key derivation.
- **Bin model** corrected to verified weekly-rubbish / fortnightly-alternating
  behaviour, tied to the collection date in `calc.bins_for_date`.
