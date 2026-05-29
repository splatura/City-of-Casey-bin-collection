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
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> CaseyWasteData:
        lat = self.config_entry.data[CONF_LATITUDE]
        lon = self.config_entry.data[CONF_LONGITUDE]
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
