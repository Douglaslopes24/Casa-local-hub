from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CasaLocalCoordinator


class CasaLocalEntity(CoordinatorEntity[CasaLocalCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CasaLocalCoordinator, stable_id: str) -> None:
        super().__init__(coordinator)
        self.stable_id = stable_id
        self._attr_unique_id = stable_id

    @property
    def device_data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self.stable_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        device = self.device_data
        metadata = device.get("metadata") or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self.stable_id)},
            name=device.get("friendly_name") or device.get("name") or "Casa Local device",
            manufacturer=device.get("vendor") or "Casa Local Hub",
            model=device.get("model") or device.get("protocol") or "Local device",
            sw_version=str(metadata.get("version") or "") or None,
        )

    @property
    def available(self) -> bool:
        return bool(self.device_data) and super().available
