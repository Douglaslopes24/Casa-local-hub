from __future__ import annotations

from datetime import UTC, datetime

from casalocal_core.models.device import DiscoveredDevice


class DeviceRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, DiscoveredDevice] = {}

    def upsert_many(self, devices: list[DiscoveredDevice]) -> None:
        now = datetime.now(UTC)
        for device in devices:
            current = self._devices.get(device.stable_id)
            if current:
                device.first_seen = current.first_seen
            device.last_seen = now
            self._devices[device.stable_id] = device

    def all(self) -> list[DiscoveredDevice]:
        return sorted(self._devices.values(), key=lambda item: item.stable_id)
