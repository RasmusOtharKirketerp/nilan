from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import NilanNabtoCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_SET_SETPOINT = "set_setpoint"
ATTR_KEY = "key"
ATTR_VALUE = "value"
ATTR_ENTRY_ID = "entry_id"

SERVICE_SET_SETPOINT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_KEY): cv.string,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)


def _resolve_coordinator(
    hass: HomeAssistant, entry_id: str | None, fallback_entry_id: str
) -> NilanNabtoCoordinator:
    coordinators: dict[str, NilanNabtoCoordinator] = hass.data.get(DOMAIN, {})
    target_entry_id = entry_id or fallback_entry_id
    coordinator = coordinators.get(target_entry_id)
    if coordinator is None:
        raise HomeAssistantError(
            f"Unknown or unavailable {DOMAIN} entry_id: {target_entry_id}"
        )
    return coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = NilanNabtoCoordinator(
        hass,
        dict(entry.data),
        int(entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, SERVICE_SET_SETPOINT):
        async def _async_handle_set_setpoint(call: ServiceCall) -> None:
            coordinator_for_call = _resolve_coordinator(
                hass,
                call.data.get(ATTR_ENTRY_ID),
                entry.entry_id,
            )
            key = call.data[ATTR_KEY]
            value = float(call.data[ATTR_VALUE])
            await coordinator_for_call.async_set_setpoint(key, value)
            await coordinator_for_call.async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_SETPOINT,
            _async_handle_set_setpoint,
            schema=SERVICE_SET_SETPOINT_SCHEMA,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_SET_SETPOINT):
            hass.services.async_remove(DOMAIN, SERVICE_SET_SETPOINT)
    return unload_ok
