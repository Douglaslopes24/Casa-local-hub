from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CasaLocalApi, CasaLocalApiError

SCAN_INTERVAL = timedelta(seconds=20)


class CasaLocalCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, api: CasaLocalApi) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Casa Local Hub",
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.api.async_devices()
            by_id = {
                str(device["stable_id"]): device
                for device in devices
                if device.get("stable_id")
            }

            ready_tuya = [
                device
                for device in by_id.values()
                if device.get("capability") == "local_control_ready"
                and str(device.get("protocol") or "").startswith("tuya")
                and ((device.get("metadata") or {}).get("tuya_profile") or {}).get("primary_switch_dps")
            ]

            semaphore = asyncio.Semaphore(4)

            async def refresh(device: dict[str, Any]) -> None:
                async with semaphore:
                    try:
                        result = await self.api.async_tuya_state(str(device["stable_id"]))
                    except (CasaLocalApiError, ClientError):
                        return
                    updated = result.get("device")
                    if isinstance(updated, dict) and updated.get("stable_id"):
                        by_id[str(updated["stable_id"])] = updated

            await asyncio.gather(*(refresh(device) for device in ready_tuya))
            return by_id
        except (CasaLocalApiError, ClientError, TimeoutError) as exc:
            raise UpdateFailed(str(exc)) from exc
