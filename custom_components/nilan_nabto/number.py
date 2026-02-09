from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_HOST, DOMAIN
from .coordinator import NilanNabtoCoordinator


def _friendly_name(key: str) -> str:
    parts = key.replace("_", " ").split()
    return " ".join(p.upper() if p in {"co2", "cts", "rpm"} else p.capitalize() for p in parts)


@dataclass
class NilanSetpointNumberDescription:
    key: str
    entity: NumberEntityDescription


class NilanNabtoSetpointNumber(CoordinatorEntity[NilanNabtoCoordinator], NumberEntity):
    entity_description: NumberEntityDescription

    def __init__(
        self,
        coordinator: NilanNabtoCoordinator,
        entry: ConfigEntry,
        description: NilanSetpointNumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self._setpoint_key = description.key
        self.entity_description = description.entity

        host = entry.data.get(CONF_HOST, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_setpoint_{description.key}"
        self._attr_name = f"Nilan {_friendly_name(description.key)}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.data.get(CONF_DEVICE_ID) or host))},
            name=f"Nilan {host}",
            manufacturer="Nilan",
            model="Nabto Gateway",
        )

    @property
    def native_value(self) -> float | None:
        setpoint = (self.coordinator.data or {}).get("setpoints", {}).get(self._setpoint_key)
        if isinstance(setpoint, dict):
            value = setpoint.get("value")
            return float(value) if value is not None else None
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setpoint(self._setpoint_key, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NilanNabtoCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []
    for key, meta in sorted((coordinator.data or {}).get("setpoints", {}).items()):
        if not isinstance(meta, dict):
            continue
        minimum = meta.get("min")
        maximum = meta.get("max")
        step = meta.get("step")
        if minimum is None or maximum is None or step is None:
            continue

        desc = NilanSetpointNumberDescription(
            key=key,
            entity=NumberEntityDescription(
                key=f"setpoint_{key}",
                name=_friendly_name(key),
                native_min_value=float(minimum),
                native_max_value=float(maximum),
                native_step=float(step),
            ),
        )
        entities.append(NilanNabtoSetpointNumber(coordinator, entry, desc))

    async_add_entities(entities)
