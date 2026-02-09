from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_HOST, DOMAIN
from .coordinator import NilanNabtoCoordinator


@dataclass
class NilanSensorDescription:
    key: str
    source: str


class NilanNabtoSensor(CoordinatorEntity[NilanNabtoCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: NilanNabtoCoordinator,
        entry: ConfigEntry,
        description: NilanSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

        host = entry.data.get(CONF_HOST, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_{description.source}_{description.key}"
        self._attr_name = f"Nilan {description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.data.get(CONF_DEVICE_ID) or host))},
            name=f"Nilan {host}",
            manufacturer="Nilan",
            model="Nabto Gateway",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self.entity_description.source == "datapoints":
            return data.get("datapoints", {}).get(self.entity_description.key)

        setpoint = data.get("setpoints", {}).get(self.entity_description.key)
        if isinstance(setpoint, dict):
            return setpoint.get("value")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.source != "setpoints":
            return None

        setpoint = (self.coordinator.data or {}).get("setpoints", {}).get(self.entity_description.key)
        if not isinstance(setpoint, dict):
            return None

        return {
            "min": setpoint.get("min"),
            "max": setpoint.get("max"),
            "step": setpoint.get("step"),
        }


class NilanStatusSensor(CoordinatorEntity[NilanNabtoCoordinator], SensorEntity):
    def __init__(self, coordinator: NilanNabtoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        host = entry.data.get(CONF_HOST, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = "Nilan status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.data.get(CONF_DEVICE_ID) or host))},
            name=f"Nilan {host}",
            manufacturer="Nilan",
            model="Nabto Gateway",
        )

    @property
    def native_value(self):
        return "ok" if (self.coordinator.data or {}).get("ok") else "error"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "timestamp_utc": data.get("timestamp_utc"),
            "connection_error": data.get("connection_error"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NilanNabtoCoordinator = hass.data[DOMAIN][entry.entry_id]

    data = coordinator.data or {}
    entities: list[SensorEntity] = [NilanStatusSensor(coordinator, entry)]

    for key in sorted((data.get("datapoints") or {}).keys()):
        entities.append(
            NilanNabtoSensor(
                coordinator,
                entry,
                NilanSensorDescription(key=key, source="datapoints"),
            )
        )

    for key in sorted((data.get("setpoints") or {}).keys()):
        entities.append(
            NilanNabtoSensor(
                coordinator,
                entry,
                NilanSensorDescription(key=key, source="setpoints"),
            )
        )

    async_add_entities(entities)
