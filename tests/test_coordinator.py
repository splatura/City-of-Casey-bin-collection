"""Integration tests for the Casey waste coordinator."""
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.casey_waste.client import AreaResult, CannotConnect
from custom_components.casey_waste.coordinator import CaseyWasteCoordinator
from custom_components.casey_waste.const import (
    BIN_GLASS,
    BIN_GREEN,
    BIN_RECYCLING,
    BIN_RUBBISH,
    DOMAIN,
)

AREA_2A = AreaResult(
    zonename="Thursday_2A",
    zonedesc="Thursday: Recycling Week 2; Garden(FOGO) Week 1; Glass Week 1",
    postcode="3980",
)


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "address": "2 Patrick Northeast Drive, Narre Warren",
            "latitude": -38.1,
            "longitude": 145.3,
            "collection_day": "Thursday",
            "week": "2",
            "postcode": "3980",
        },
        unique_id="-38.10000,145.30000",
    )
    entry.add_to_hass(hass)
    return entry


def _patch_area(ret=None, exc=None):
    return patch(
        "custom_components.casey_waste.coordinator.find_collection_area",
        AsyncMock(return_value=ret, side_effect=exc),
    )


@freeze_time("2025-10-20")
async def test_happy_path(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("UTC")
    entry = _entry(hass)
    coordinator = CaseyWasteCoordinator(hass, entry)
    with _patch_area(ret=AREA_2A):
        data = await coordinator._async_update_data()

    assert data.collection_day == "Thursday"
    assert data.week == "2"
    assert data.next_date == date(2025, 10, 23)
    assert data.bins == [BIN_RUBBISH, BIN_RECYCLING]
    assert data.night_before == "Wednesday"
    assert data.days_until == 3
    assert data.glass_week == "1"
    assert data.next_glass_date == date(2026, 11, 26)  # glass service not started yet


@freeze_time("2026-11-24")
async def test_glass_collection_week(hass: HomeAssistant) -> None:
    # Council: 42 Central Parkway (Thursday_2A) first glass collection 26 Nov 2026.
    await hass.config.async_set_time_zone("UTC")
    entry = _entry(hass)
    coordinator = CaseyWasteCoordinator(hass, entry)
    with _patch_area(ret=AREA_2A):
        data = await coordinator._async_update_data()

    assert data.next_date == date(2026, 11, 26)
    assert data.bins == [BIN_RUBBISH, BIN_GREEN, BIN_GLASS]
    assert data.next_glass_date == date(2026, 11, 26)


@freeze_time("2025-10-20")
async def test_cannot_connect_raises_update_failed(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    coordinator = CaseyWasteCoordinator(hass, entry)
    with _patch_area(exc=CannotConnect("boom")):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


@freeze_time("2025-10-20")
async def test_unparseable_collection_raises_update_failed(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    coordinator = CaseyWasteCoordinator(hass, entry)
    with _patch_area(ret=AreaResult(zonename="garbage", zonedesc="", postcode=None)):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
