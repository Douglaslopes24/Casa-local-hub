from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import CasaLocalEntity


def _is_switch(device: dict[str, Any]) -> bool:
    return (
        device.get("capability") == "local_control_ready"
        and device.get("kind") == "switch"
        and str(device.get("protocol") or "").startswith("tuya")
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    known: set[str] = set()

    @callback
    def add_new_entities() -> None:
        entities = []
        for stable_id, device in coordinator.data.items():
            if stable_id in known or not _is_switch(device):
                continue
            known.add(stable_id)
            entities.append(CasaLocalSwitch(coordinator, stable_id))
        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class CasaLocalSwitch(CasaLocalEntity, SwitchEntity):
    _attr_name = None

    @property
    def is_on(self) -> bool | None:
        metadata = self.device_data.get("metadata") or {}
        profile = metadata.get("tuya_profile") or {}
        dps = metadata.get("last_dps") or {}
        switch_dps = str(profile.get("primary_switch_dps") or "")
        value = dps.get(switch_dps)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_tuya_control(self.stable_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_tuya_control(self.stable_id, False)
        await self.coordinator.async_request_refresh()
