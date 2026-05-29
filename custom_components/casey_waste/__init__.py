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
