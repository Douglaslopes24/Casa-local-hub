from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError, ClientSession


class CasaLocalApiError(RuntimeError):
    pass


class CasaLocalAuthError(CasaLocalApiError):
    pass


class CasaLocalApi:
    def __init__(self, session: ClientSession, base_url: str, token: str | None = None) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    async def async_health(self) -> dict[str, Any]:
        async with self._session.get(f"{self.base_url}/health") as response:
            response.raise_for_status()
            return await response.json()

    async def async_pair(self, code: str) -> str:
        try:
            async with self._session.post(
                f"{self.base_url}/api/v1/pairing/complete",
                json={"code": code, "label": "Home Assistant Integration"},
            ) as response:
                if response.status in (400, 401):
                    raise CasaLocalAuthError("Invalid or expired pairing code")
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as exc:
            raise CasaLocalApiError(str(exc)) from exc

        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise CasaLocalApiError("Pairing response did not include a token")
        self.token = token
        return token

    async def async_devices(self) -> list[dict[str, Any]]:
        async with self._session.get(
            f"{self.base_url}/api/v1/integration/devices",
            headers=self._headers(),
        ) as response:
            if response.status == 401:
                raise CasaLocalAuthError("Authentication failed")
            response.raise_for_status()
            data = await response.json()
        return list(data.get("devices") or [])

    async def async_tuya_state(self, stable_id: str) -> dict[str, Any]:
        async with self._session.get(
            f"{self.base_url}/api/v1/devices/{stable_id}/tuya/state",
            headers=self._headers(),
        ) as response:
            if response.status == 401:
                raise CasaLocalAuthError("Authentication failed")
            response.raise_for_status()
            return await response.json()

    async def async_tuya_control(
        self,
        stable_id: str,
        value: bool,
        dps: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"value": value}
        if dps:
            payload["dps"] = dps

        async with self._session.post(
            f"{self.base_url}/api/v1/devices/{stable_id}/tuya/control",
            headers=self._headers(),
            json=payload,
        ) as response:
            if response.status == 401:
                raise CasaLocalAuthError("Authentication failed")
            response.raise_for_status()
            return await response.json()
