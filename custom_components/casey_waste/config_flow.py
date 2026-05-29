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
