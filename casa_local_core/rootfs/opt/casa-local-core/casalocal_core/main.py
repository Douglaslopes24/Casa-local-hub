from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from casalocal_core.config import settings
from casalocal_core.services.discovery import DiscoveryManager
from casalocal_core.services.registry import DeviceRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    registry = DeviceRegistry()
    app.state.registry = registry
    app.state.discovery = DiscoveryManager(registry)
    yield


app = FastAPI(
    title="Casa Local Core",
    version=settings.version,
    description="Local-first discovery bridge for Casa Local Hub.",
    lifespan=lifespan,
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
    }


@app.post("/api/v1/discovery")
async def discovery(payload: dict | None = None) -> dict:
    payload = payload or {}
    timeout = float(payload.get("timeout", 6))
    protocols = payload.get("protocols")
    devices, errors = await app.state.discovery.discover(timeout=timeout, protocols=protocols)
    return {
        "count": len(devices),
        "devices": [device.model_dump(mode="json") for device in devices],
        "errors": errors,
    }


def run() -> None:
    uvicorn.run("casalocal_core.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
