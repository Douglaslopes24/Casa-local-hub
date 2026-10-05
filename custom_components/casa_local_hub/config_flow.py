from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CasaLocalApi, CasaLocalApiError, CasaLocalAuthError
from .const import CONF_CORE_URL, CONF_TOKEN, DEFAULT_CORE_URL, DOMAIN


class CasaLocalHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            core_url = str(user_input[CONF_CORE_URL]).strip().rstrip("/")
            pairing_code = str(user_input["pairing_code"]).strip()

            session = async_get_clientsession(self.hass)
            api = CasaLocalApi(session, core_url)

            try:
                async with asyncio.timeout(10):
                    health = await api.async_health()
                    token = await api.async_pair(pairing_code)
            except CasaLocalAuthError:
                errors["base"] = "invalid_pairing_code"
            except (CasaLocalApiError, ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if health.get("service") != "casa-local-core":
                    errors["base"] = "not_casa_local"
                else:
                    await self.async_set_unique_id("casa_local_hub")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Casa Local Hub",
                        data={
                            CONF_CORE_URL: core_url,
                            CONF_TOKEN: token,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CORE_URL,
                    default=(user_input or {}).get(CONF_CORE_URL, DEFAULT_CORE_URL),
                ): str,
                vol.Required("pairing_code"): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
