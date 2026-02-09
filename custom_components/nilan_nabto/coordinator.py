from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DEVICE_ID, CONF_EMAIL, CONF_HOST, CONF_PORT, DOMAIN
from .nabto_client import run_nabto_probe

_LOGGER = logging.getLogger(__name__)


class NilanNabtoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, config: dict[str, Any], interval_seconds: int) -> None:
        self._config = config
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval_seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        report = await run_nabto_probe(
            email=self._config[CONF_EMAIL],
            device_id=self._config.get(CONF_DEVICE_ID),
            host=self._config.get(CONF_HOST),
            port=int(self._config.get(CONF_PORT)),
        )
        if not report.get("ok"):
            raise UpdateFailed(
                f"Nilan Nabto update failed: {report.get('connection_error') or report.get('error') or 'unknown_error'}"
            )
        return report
