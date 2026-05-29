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
