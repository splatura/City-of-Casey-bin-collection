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
    _attr_icon = "mdi:calendar-clock"

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
    _attr_icon = "mdi:trash-can"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bins_out"

    @property
    def native_value(self):
        return ", ".join(self.coordinator.data.bins)

    @property
    def extra_state_attributes(self):
        return {"bins": self.coordinator.data.bins}
