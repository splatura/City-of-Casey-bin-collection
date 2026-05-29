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
