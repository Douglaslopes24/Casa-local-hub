from __future__ import annotations

import asyncio
from typing import Any

import tinytuya

from casalocal_core.models.device import LocalCapability
from casalocal_core.services.registry import DeviceRegistry
from casalocal_core.services.tuya_control import TuyaController, TuyaValidationError
from casalocal_core.services.tuya_profile import analyze_tuya_dps
from casalocal_core.services.vault import LocalVault


class TuyaCloudError(RuntimeError):
    pass


class TuyaCloudSync:
    def __init__(
        self,
        registry: DeviceRegistry,
        vault: LocalVault,
        controller: TuyaController,
    ) -> None:
        self.registry = registry
        self.vault = vault
        self.controller = controller

    async def sync(
        self,
        *,
        api_key: str,
        api_secret: str,
        region: str,
        device_id: str,
    ) -> dict[str, Any]:
        if region not in {"cn", "us", "us-e", "eu", "eu-w", "in", "sg"}:
            raise TuyaCloudError("Unsupported Tuya region.")

        def _cloud_devices() -> list[dict[str, Any]]:
            cloud = tinytuya.Cloud(
                apiRegion=region,
                apiKey=api_key,
                apiSecret=api_secret,
                apiDeviceID=device_id,
            )
            result = cloud.getdevices()
            if not isinstance(result, list):
                raise TuyaCloudError("Tuya Cloud did not return a device list.")
            return result

        try:
            cloud_devices = await asyncio.to_thread(_cloud_devices)
        except TuyaCloudError:
            raise
        except Exception as exc:
            raise TuyaCloudError("Tuya Cloud authentication or device sync failed.") from exc

        by_id = {
            str(item.get("id") or ""): item
            for item in cloud_devices
            if item.get("id")
        }

        local_tuya = [
            device
            for device in self.registry.all()
            if device.protocol.startswith("tuya")
        ]

        matched = 0
        communication_validated = 0
        missing_key = 0
        validation_failed = 0
        results: list[dict[str, Any]] = []

        for device in local_tuya:
            cloud_device = by_id.get(str(device.metadata.get("device_id") or ""))
            if not cloud_device:
                results.append(
                    {
                        "stable_id": device.stable_id,
                        "name": device.friendly_name or device.name,
                        "status": "not_in_cloud_project",
                    }
                )
                continue

            local_key = str(cloud_device.get("key") or "").strip()
            if not local_key:
                missing_key += 1
                results.append(
                    {
                        "stable_id": device.stable_id,
                        "name": device.friendly_name or device.name,
                        "status": "cloud_key_missing",
                    }
                )
                continue

            matched += 1
            self.vault.set_secret(device.stable_id, "tuya_local_key", local_key)

            try:
                status = await self.controller.validate_local_key(device, local_key)
                profile = analyze_tuya_dps(status)
            except (TuyaValidationError, OSError, ValueError):
                validation_failed += 1
                self.registry.set_capability(
                    device.stable_id,
                    LocalCapability.CREDENTIALS_REQUIRED,
                    {
                        "validation": {
                            "communication": "failed",
                            "control": "not_tested",
                            "integratable": False,
                        },
                        "credential_source": "tuya_cloud_mobile",
                    },
                )
                results.append(
                    {
                        "stable_id": device.stable_id,
                        "name": device.friendly_name or device.name,
                        "status": "local_validation_failed",
                    }
                )
                continue

            communication_validated += 1
            profile_metadata = {key: value for key, value in profile.items() if key != "dps"}
            self.registry.apply_profile(
                device.stable_id,
                kind=str(profile.get("kind") or "unknown"),
                metadata_updates={
                    "tuya_profile": profile_metadata,
                    "last_dps": profile.get("dps") or {},
                },
            )
            self.registry.set_capability(
                device.stable_id,
                LocalCapability.LOCAL_CONTROL_POSSIBLE,
                {
                    "credential_source": "tuya_cloud_mobile",
                    "validation": {
                        "communication": "passed",
                        "control": "not_tested",
                        "integratable": False,
                    },
                },
            )
            results.append(
                {
                    "stable_id": device.stable_id,
                    "name": device.friendly_name or device.name,
                    "status": "communication_validated",
                    "kind": profile.get("kind") or "unknown",
                }
            )

        return {
            "cloud_devices": len(cloud_devices),
            "local_tuya_devices": len(local_tuya),
            "matched": matched,
            "communication_validated": communication_validated,
            "missing_key": missing_key,
            "validation_failed": validation_failed,
            "devices": results,
        }
