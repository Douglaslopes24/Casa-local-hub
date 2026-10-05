from __future__ import annotations

import asyncio
from typing import Any

import tinytuya

from casalocal_core.models.device import DiscoveredDevice


class TuyaValidationError(RuntimeError):
    pass


class TuyaController:
    async def validate_local_key(
        self,
        device: DiscoveredDevice,
        local_key: str,
    ) -> dict[str, Any]:
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

        def _status() -> dict[str, Any]:
            client = tinytuya.Device(device_id, device.address, local_key)
            client.set_version(version)
            client.set_socketTimeout(5)
            result = client.status()
            if not isinstance(result, dict):
                raise TuyaValidationError("Unexpected response from device.")
            if result.get("Error") or result.get("Err"):
                raise TuyaValidationError(str(result.get("Error") or result.get("Err")))
            return result

        return await asyncio.to_thread(_status)
