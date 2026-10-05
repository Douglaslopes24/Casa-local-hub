from __future__ import annotations

import asyncio
from typing import Any

import tinytuya

from casalocal_core.models.device import DiscoveredDevice
from casalocal_core.services.tuya_profile import analyze_tuya_dps


class TuyaValidationError(RuntimeError):
    pass


class TuyaControlError(RuntimeError):
    pass


class TuyaController:
    def _build_client(self, device: DiscoveredDevice, local_key: str) -> tinytuya.Device:
        if not device.address:
            raise TuyaValidationError("Device has no local IP address.")

        device_id = str(device.metadata.get("device_id") or "")
        if not device_id:
            raise TuyaValidationError("Device ID is missing.")

        version_raw = device.metadata.get("version")
        try:
            version = float(version_raw)
        except (TypeError, ValueError):
            version = 3.3

        client = tinytuya.Device(device_id, device.address, local_key)
        client.set_version(version)
        client.set_socketTimeout(5)
        return client

    @staticmethod
    def _ensure_valid_status(result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise TuyaValidationError("Unexpected response from device.")
        if result.get("Error") or result.get("Err"):
            raise TuyaValidationError(str(result.get("Error") or result.get("Err")))
        return result

    async def read_status(
        self,
        device: DiscoveredDevice,
        local_key: str,
    ) -> dict[str, Any]:
        def _status() -> dict[str, Any]:
            client = self._build_client(device, local_key)
            return self._ensure_valid_status(client.status())

        return await asyncio.to_thread(_status)

    async def validate_local_key(
        self,
        device: DiscoveredDevice,
        local_key: str,
    ) -> dict[str, Any]:
        return await self.read_status(device, local_key)

    async def inspect(
        self,
        device: DiscoveredDevice,
        local_key: str,
    ) -> dict[str, Any]:
        status = await self.read_status(device, local_key)
        return analyze_tuya_dps(status)

    async def set_boolean(
        self,
        device: DiscoveredDevice,
        local_key: str,
        dps: str,
        value: bool,
    ) -> dict[str, Any]:
        try:
            dps_index = int(dps)
        except (TypeError, ValueError) as exc:
            raise TuyaControlError("Invalid DPS index.") from exc

        def _set() -> None:
            client = self._build_client(device, local_key)
            result = client.set_status(bool(value), switch=dps_index)
            if isinstance(result, dict) and (result.get("Error") or result.get("Err")):
                raise TuyaControlError(str(result.get("Error") or result.get("Err")))

        await asyncio.to_thread(_set)
        return await self.inspect(device, local_key)
