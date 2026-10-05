from __future__ import annotations

import asyncio

from casalocal_core.adapters.base import DiscoveryAdapter
from casalocal_core.adapters.onvif import OnvifAdapter
from casalocal_core.adapters.sonoff import SonoffAdapter
from casalocal_core.adapters.tuya import TuyaAdapter
from casalocal_core.models.device import DiscoveredDevice
from casalocal_core.services.registry import DeviceRegistry


class DiscoveryManager:
    def __init__(self, registry: DeviceRegistry) -> None:
        self.registry = registry
        self.adapters: dict[str, DiscoveryAdapter] = {
            adapter.name: adapter for adapter in (TuyaAdapter(), SonoffAdapter(), OnvifAdapter())
        }

    async def discover(
        self,
        timeout: float,
        protocols: list[str] | None = None,
    ) -> tuple[list[DiscoveredDevice], dict[str, str]]:
        selected = self.adapters
        if protocols:
            wanted = {item.lower() for item in protocols}
            selected = {name: adapter for name, adapter in self.adapters.items() if name in wanted}

        async def run_adapter(name: str, adapter: DiscoveryAdapter):
            try:
                return name, await adapter.discover(timeout), None
            except Exception as exc:
                return name, [], f"{type(exc).__name__}: {exc}"

        results = await asyncio.gather(
            *(run_adapter(name, adapter) for name, adapter in selected.items())
        )

        devices_by_id: dict[str, DiscoveredDevice] = {}
        errors: dict[str, str] = {}
        for name, devices, error in results:
            if error:
                errors[name] = error
            for device in devices:
                devices_by_id[device.stable_id] = device

        devices = list(devices_by_id.values())
        self.registry.upsert_many(devices)
        return devices, errors
