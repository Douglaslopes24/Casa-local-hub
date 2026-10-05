from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DeviceKind(StrEnum):
    UNKNOWN = "unknown"
    SWITCH = "switch"
    LIGHT = "light"
    SENSOR = "sensor"
    CAMERA = "camera"
    HUB = "hub"


class LocalCapability(StrEnum):
    DISCOVERED = "discovered"
    LOCAL_CONTROL_POSSIBLE = "local_control_possible"
    LOCAL_CONTROL_READY = "local_control_ready"
    CREDENTIALS_REQUIRED = "credentials_required"


class DiscoveredDevice(BaseModel):
    stable_id: str
    name: str | None = None
    friendly_name: str | None = None
    area: str | None = None
    vendor: str | None = None
    model: str | None = None
    kind: DeviceKind = DeviceKind.UNKNOWN
    protocol: str
    address: str | None = None
    port: int | None = None
    mac: str | None = None
    capability: LocalCapability = LocalCapability.DISCOVERED
    metadata: dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(UTC))
