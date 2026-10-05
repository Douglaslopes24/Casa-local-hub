from __future__ import annotations

import asyncio
from typing import Any

import tinytuya

from casalocal_core.adapters.base import DiscoveryAdapter
from casalocal_core.models.device import DiscoveredDevice, LocalCapability


class TuyaAdapter(DiscoveryAdapter):
    name = "tuya"

    async def discover(self, timeout: float) -> list[DiscoveredDevice]:
        raw: dict[str, Any] = await asyncio.to_thread(
            tinytuya.deviceScan,
            False,
            int(timeout),
        )

        devices: list[DiscoveredDevice] = []
        for ip, info in (raw or {}).items():
            device_id = str(info.get("gwId") or info.get("id") or ip)
            version = info.get("version")
            devices.append(
                DiscoveredDevice(
                    stable_id=f"tuya:{device_id}",
                    name=info.get("name"),
                    vendor="Tuya/OEM",
                    protocol=f"tuya-{version}" if version else "tuya-lan",
                    address=str(info.get("ip") or ip),
                    port=6668,
                    mac=info.get("mac"),
                    capability=LocalCapability.CREDENTIALS_REQUIRED,
                    metadata={
                        "device_id": device_id,
                        "product_key": info.get("productKey"),
                        "version": version,
                    },
                )
            )
        return devices
