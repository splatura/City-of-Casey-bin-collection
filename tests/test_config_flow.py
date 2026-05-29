"""Integration tests for the Casey waste config flow."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.casey_waste.client import (
    AddressNotFound,
    AreaNotFound,
    AreaResult,
    CannotConnect,
    GeoResult,
)
from custom_components.casey_waste.const import DOMAIN

ADDRESS = "2 Patrick Northeast Drive, Narre Warren, VIC"
GEO = GeoResult(lat=-38.10000, lon=145.30000)


def _patch(geocode_ret=None, geocode_exc=None, area_ret=None, area_exc=None):
    geocode = AsyncMock(side_effect=geocode_exc, return_value=geocode_ret)
    find_area = AsyncMock(side_effect=area_exc, return_value=area_ret)
    return (
        patch("custom_components.casey_waste.config_flow.geocode", geocode),
        patch(
            "custom_components.casey_waste.config_flow.find_collection_area", find_area
        ),
    )


async def _run(hass: HomeAssistant, **kwargs):
    p_geo, p_area = _patch(**kwargs)
    with p_geo, p_area:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], {"address": ADDRESS}
        )


async def test_happy_path_creates_entry(hass: HomeAssistant) -> None:
    result = await _run(
        hass,
        geocode_ret=GEO,
        area_ret=AreaResult(collection="Thursday_Week_2", postcode="3980"),
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == ADDRESS
    data = result["data"]
    assert data["latitude"] == GEO.lat
    assert data["longitude"] == GEO.lon
    assert data["collection_day"] == "Thursday"
    assert data["week"] == "2"
    assert data["postcode"] == "3980"


async def test_address_not_found(hass: HomeAssistant) -> None:
    result = await _run(hass, geocode_exc=AddressNotFound("nope"))
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "address_not_found"}


async def test_area_not_found(hass: HomeAssistant) -> None:
    result = await _run(hass, geocode_ret=GEO, area_exc=AreaNotFound("nope"))
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "area_not_found"}


async def test_cannot_connect(hass: HomeAssistant) -> None:
    result = await _run(hass, geocode_exc=CannotConnect("boom"))
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unparseable_collection(hass: HomeAssistant) -> None:
    result = await _run(
        hass,
        geocode_ret=GEO,
        area_ret=AreaResult(collection="garbage", postcode=None),
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "area_not_found"}


async def test_duplicate_aborts(hass: HomeAssistant) -> None:
    area = AreaResult(collection="Thursday_Week_2", postcode="3980")
    first = await _run(hass, geocode_ret=GEO, area_ret=area)
    assert first["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    second = await _run(hass, geocode_ret=GEO, area_ret=area)
    assert second["type"] == data_entry_flow.FlowResultType.ABORT
    assert second["reason"] == "already_configured"
