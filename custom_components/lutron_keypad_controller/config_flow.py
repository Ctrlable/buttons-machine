"""Config flow for Lutron Keypad Controller."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_NAME,
    CONF_AREA_NAME,
    CONF_KEYPAD_TYPE,
    KEYPAD_TYPES,
    KEYPAD_GENERIC,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Required(CONF_DEVICE_SERIAL): str,
        vol.Optional(CONF_DEVICE_NAME, default=""): str,
        vol.Optional(CONF_AREA_NAME, default=""): str,
        vol.Optional(CONF_KEYPAD_TYPE, default=KEYPAD_GENERIC): vol.In(KEYPAD_TYPES),
    }
)


def _lutron_caseta_loaded(hass: HomeAssistant) -> bool:
    return "lutron_caseta" in hass.data


class LutronKeypadsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _lutron_caseta_loaded(self.hass):
                errors["base"] = "lutron_not_loaded"
            else:
                serial = user_input[CONF_DEVICE_SERIAL].strip()
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["name"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return LutronKeypadsOptionsFlow(config_entry)


class LutronKeypadsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "note": "Button assignments are configured in YAML. See the documentation for the full schema."
            },
        )
