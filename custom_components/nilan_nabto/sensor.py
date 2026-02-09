from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_HOST, DOMAIN, INTEGRATION_VERSION
from .coordinator import NilanNabtoCoordinator
from .vendor.genvexnabto.models import GenvexNabtoDatapointKey, GenvexNabtoSetpointKey


@dataclass
class NilanSensorDescription:
    key: str
    source: str
    entity: SensorEntityDescription


def _all_class_values(cls) -> list[str]:
    values: list[str] = []
    for name, value in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            values.append(value)
    return values


def _friendly_name(key: str) -> str:
    parts = key.replace("_", " ").split()
    return " ".join(p.upper() if p in {"co2", "cts", "rpm"} else p.capitalize() for p in parts)


def _build_description(key: str, source: str) -> SensorEntityDescription:
    desc = SensorEntityDescription(
        key=f"{source}_{key}",
        name=_friendly_name(key),
    )

    if key.startswith("temp_") or key.endswith("_temp") or "temperature" in key:
        desc.device_class = SensorDeviceClass.TEMPERATURE
        desc.native_unit_of_measurement = UnitOfTemperature.CELSIUS
        desc.state_class = SensorStateClass.MEASUREMENT
    elif "humidity" in key:
        desc.device_class = SensorDeviceClass.HUMIDITY
        desc.native_unit_of_measurement = PERCENTAGE
        desc.state_class = SensorStateClass.MEASUREMENT
    elif "co2" in key:
        desc.device_class = SensorDeviceClass.CO2
        desc.native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
        desc.state_class = SensorStateClass.MEASUREMENT
    elif "rpm" in key:
        desc.native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
        desc.state_class = SensorStateClass.MEASUREMENT
    elif "pwm" in key:
        desc.native_unit_of_measurement = PERCENTAGE
        desc.state_class = SensorStateClass.MEASUREMENT
    elif key.endswith("_days") or "days" in key:
        desc.native_unit_of_measurement = "d"
        desc.state_class = SensorStateClass.MEASUREMENT

    return desc


class NilanNabtoSensor(CoordinatorEntity[NilanNabtoCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: NilanNabtoCoordinator,
        entry: ConfigEntry,
        description: NilanSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        host = entry.data.get(CONF_HOST, "unknown")
        self._attr_unique_id = f"{entry.entry_id}_{description.source}_{description.key}"
        self._attr_name = f"Nilan {description.entity.name}"
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
            "integration_version": INTEGRATION_VERSION,
            "timestamp_utc": data.get("timestamp_utc"),
            "connection_error": data.get("connection_error"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NilanNabtoCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [NilanStatusSensor(coordinator, entry)]

    datapoint_keys = sorted(set(_all_class_values(GenvexNabtoDatapointKey)))
    setpoint_keys = sorted(set(_all_class_values(GenvexNabtoSetpointKey)))

    for key in datapoint_keys:
        entities.append(
            NilanNabtoSensor(
                coordinator,
                entry,
                NilanSensorDescription(key=key, source="datapoints", entity=_build_description(key, "datapoints")),
            )
        )

    for key in setpoint_keys:
        entities.append(
            NilanNabtoSensor(
                coordinator,
                entry,
                NilanSensorDescription(key=key, source="setpoints", entity=_build_description(key, "setpoints")),
            )
        )

    async_add_entities(entities)
