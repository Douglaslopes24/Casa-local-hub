from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from casalocal_core.config import settings
from casalocal_core.models.device import LocalCapability
from casalocal_core.services.discovery import DiscoveryManager
from casalocal_core.services.registry import DeviceRegistry
from casalocal_core.services.pairing import PairingError, PairingService
from casalocal_core.services.tuya_control import (
    TuyaControlError,
    TuyaController,
    TuyaValidationError,
)
from casalocal_core.services.tuya_profile import analyze_tuya_dps
from casalocal_core.services.vault import LocalVault


WEB_INDEX = Path(__file__).parent / "web" / "index.html"


def is_ingress_request(request: Request) -> bool:
    client_host = request.client.host if request.client else ""
    return client_host == "172.30.32.2" and bool(request.headers.get("x-ingress-path"))


def bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization[7:].strip() or None


def is_api_authenticated(request: Request) -> bool:
    token = bearer_token(request)
    return bool(token and app.state.pairing.validate_token(token))


def require_ingress(request: Request) -> None:
    if not is_ingress_request(request):
        raise HTTPException(
            status_code=403,
            detail="This action is only available through Home Assistant Ingress.",
        )


def require_ingress_or_api(request: Request) -> None:
    if is_ingress_request(request) or is_api_authenticated(request):
        return
    raise HTTPException(status_code=401, detail="Authentication required")


def persist_tuya_profile(stable_id: str, profile: dict) -> None:
    profile_metadata = {key: value for key, value in profile.items() if key != "dps"}
    app.state.registry.apply_profile(
        stable_id,
        kind=str(profile.get("kind") or "unknown"),
        metadata_updates={
            "tuya_profile": profile_metadata,
            "last_dps": profile.get("dps") or {},
            "last_polled_at": datetime.now(UTC).isoformat(),
        },
    )


def get_ready_tuya(stable_id: str):
    device = app.state.registry.get(stable_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.protocol.startswith("tuya"):
        raise HTTPException(status_code=400, detail="Device is not a Tuya device")

    local_key = app.state.vault.get_secret(stable_id, "tuya_local_key")
    if not local_key:
        raise HTTPException(status_code=409, detail="Local key is not configured")
    return device, local_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    registry = DeviceRegistry(settings.database_path)
    app.state.registry = registry
    app.state.discovery = DiscoveryManager(registry)
    app.state.vault = LocalVault(settings.database_path, settings.master_key_path)
    app.state.tuya = TuyaController()
    app.state.pairing = PairingService(settings.database_path)
    yield


app = FastAPI(
    title="Casa Local Core",
    version=settings.version,
    description="Local-first discovery bridge for Casa Local Hub.",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    html = WEB_INDEX.read_text(encoding="utf-8")
    html = html.replace("__VERSION__", settings.version)
    html = html.replace("__INGRESS__", "true" if is_ingress_request(request) else "false")
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "casa-local-core", "version": settings.version}


@app.get("/api/v1/status")
async def status() -> dict:
    return {
        "service": "casa-local-core",
        "version": settings.version,
        "known_devices": len(app.state.registry.all()),
        "adapters": list(app.state.discovery.adapters.keys()),
        "vault": "ready",
    }


@app.post("/api/v1/pairing/start")
async def start_pairing(request: Request) -> dict:
    require_ingress(request)
    return app.state.pairing.start()


@app.post("/api/v1/pairing/complete")
async def complete_pairing(payload: dict) -> dict:
    code = str(payload.get("code") or "").strip()
    label = str(payload.get("label") or "Home Assistant").strip()
    if len(code) != 8 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid pairing code format")
    try:
        token = app.state.pairing.complete(code, label=label)
    except PairingError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"token": token, "token_type": "bearer"}


@app.get("/api/v1/integration/devices")
async def integration_devices(request: Request) -> dict:
    require_ingress_or_api(request)
    known = app.state.registry.all()
    return {
        "count": len(known),
        "devices": [device.model_dump(mode="json") for device in known],
    }


@app.get("/api/v1/devices")
async def devices() -> dict:
    known = app.state.registry.all()
    return {
        "count": len(known),
        "devices": [device.model_dump(mode="json") for device in known],
    }


@app.patch("/api/v1/devices/{stable_id}")
async def update_device(stable_id: str, payload: dict) -> dict:
    friendly_name = payload.get("friendly_name")
    area = payload.get("area")

    if friendly_name is not None and not isinstance(friendly_name, str):
        raise HTTPException(status_code=400, detail="friendly_name must be a string")
    if area is not None and not isinstance(area, str):
        raise HTTPException(status_code=400, detail="area must be a string")

    device = app.state.registry.update_preferences(
        stable_id=stable_id,
        friendly_name=friendly_name,
        area=area,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"device": device.model_dump(mode="json")}


@app.post("/api/v1/discovery")
async def discovery(payload: dict | None = None) -> dict:
    payload = payload or {}
    timeout = min(max(float(payload.get("timeout", 6)), 1), 20)
    protocols = payload.get("protocols")
    devices_found, errors = await app.state.discovery.discover(
        timeout=timeout,
        protocols=protocols,
    )
    return {
        "count": len(devices_found),
        "devices": [device.model_dump(mode="json") for device in devices_found],
        "errors": errors,
    }


@app.post("/api/v1/devices/{stable_id}/tuya/credentials")
async def set_tuya_credentials(stable_id: str, payload: dict, request: Request) -> dict:
    require_ingress(request)

    device = app.state.registry.get(stable_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.protocol.startswith("tuya"):
        raise HTTPException(status_code=400, detail="Device is not a Tuya device")

    local_key = payload.get("local_key")
    if not isinstance(local_key, str) or not 8 <= len(local_key.strip()) <= 128:
        raise HTTPException(status_code=400, detail="Invalid local key")

    local_key = local_key.strip()
    try:
        status_result = await app.state.tuya.validate_local_key(device, local_key)
        profile = analyze_tuya_dps(status_result)
    except (TuyaValidationError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Local key validation failed") from exc

    app.state.vault.set_secret(stable_id, "tuya_local_key", local_key)
    app.state.registry.set_capability(
        stable_id,
        LocalCapability.LOCAL_CONTROL_READY,
        {
            "credential_validated_at": datetime.now(UTC).isoformat(),
            "credential_source": "manual_ingress",
        },
    )
    persist_tuya_profile(stable_id, profile)
    updated = app.state.registry.get(stable_id)

    return {
        "status": "ready",
        "profile": {key: value for key, value in profile.items() if key != "dps"},
        "device": updated.model_dump(mode="json") if updated else None,
    }


@app.get("/api/v1/devices/{stable_id}/tuya/state")
async def get_tuya_state(stable_id: str, request: Request) -> dict:
    require_ingress_or_api(request)
    device, local_key = get_ready_tuya(stable_id)

    try:
        profile = await app.state.tuya.inspect(device, local_key)
    except (TuyaValidationError, OSError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not read device state") from exc

    persist_tuya_profile(stable_id, profile)
    updated = app.state.registry.get(stable_id)
    return {
        "profile": {key: value for key, value in profile.items() if key != "dps"},
        "dps": profile.get("dps") or {},
        "device": updated.model_dump(mode="json") if updated else None,
    }


@app.post("/api/v1/devices/{stable_id}/tuya/control")
async def control_tuya(stable_id: str, payload: dict, request: Request) -> dict:
    require_ingress_or_api(request)
    device, local_key = get_ready_tuya(stable_id)

    profile = device.metadata.get("tuya_profile")
    if not isinstance(profile, dict):
        raise HTTPException(status_code=409, detail="Device profile is not ready")

    requested_dps = str(payload.get("dps") or profile.get("primary_switch_dps") or "")
    allowed_boolean_dps = {str(item) for item in profile.get("boolean_dps") or []}
    if not requested_dps or requested_dps not in allowed_boolean_dps:
        raise HTTPException(status_code=400, detail="DPS is not an approved boolean control")

    value = payload.get("value")
    if not isinstance(value, bool):
        raise HTTPException(status_code=400, detail="value must be boolean")

    try:
        refreshed_profile = await app.state.tuya.set_boolean(
            device,
            local_key,
            requested_dps,
            value,
        )
    except (TuyaValidationError, TuyaControlError, OSError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Local command failed") from exc

    persist_tuya_profile(stable_id, refreshed_profile)
    updated = app.state.registry.get(stable_id)
    return {
        "status": "ok",
        "dps": refreshed_profile.get("dps") or {},
        "device": updated.model_dump(mode="json") if updated else None,
    }


def run() -> None:
    uvicorn.run("casalocal_core.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
