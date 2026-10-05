from __future__ import annotations

import asyncio
import threading
from typing import Any

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

from casalocal_core.adapters.base import DiscoveryAdapter
from casalocal_core.models.device import DiscoveredDevice, LocalCapability


class _EwelinkListener(ServiceListener):
    def __init__(self, zc: Zeroconf) -> None:
        self.zc = zc
        self.services: dict[str, Any] = {}
        self.lock = threading.Lock()

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name, timeout=1500)
        if info:
            with self.lock:
                self.services[name] = info

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        return None


class SonoffAdapter(DiscoveryAdapter):
    name = "sonoff"
    service_type = "_ewelink._tcp.local."

    async def discover(self, timeout: float) -> list[DiscoveredDevice]:
        return await asyncio.to_thread(self._discover_sync, timeout)

    def _discover_sync(self, timeout: float) -> list[DiscoveredDevice]:
        zc = Zeroconf()
        listener = _EwelinkListener(zc)
        browser = ServiceBrowser(zc, self.service_type, listener)
        try:
            threading.Event().wait(timeout)
            with listener.lock:
                items = list(listener.services.items())
        finally:
            browser.cancel()
            zc.close()

        devices: list[DiscoveredDevice] = []
        for service_name, info in items:
            addresses = info.parsed_addresses()
            props = {
                (k.decode(errors="replace") if isinstance(k, bytes) else str(k)):
                (v.decode(errors="replace") if isinstance(v, bytes) else v)
                for k, v in info.properties.items()
            }
            device_id = str(props.get("id") or props.get("deviceid") or service_name)
            devices.append(
                DiscoveredDevice(
                    stable_id=f"ewelink:{device_id}",
                    name=service_name.removesuffix("._ewelink._tcp.local."),
                    vendor="SONOFF/eWeLink",
                    protocol="ewelink-lan",
                    address=addresses[0] if addresses else None,
                    port=info.port or None,
                    capability=LocalCapability.CREDENTIALS_REQUIRED,
                    metadata={"service": service_name, "properties": props},
                )
            )
        return devices
