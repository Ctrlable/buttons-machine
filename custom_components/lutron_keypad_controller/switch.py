"""Switch platform — per-button enabled toggles."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_KEYPAD_TYPE,
    KEYPAD_GENERIC,
    get_button_layout,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = [
        LutronButtonSwitch(entry, btn["number"], btn["is_raise"], btn["is_lower"])
        for btn in get_button_layout(entry.data)
    ]
    async_add_entities(entities, True)


class LutronButtonSwitch(SwitchEntity):
    """Toggle to enable or disable a keypad button's action."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        btn_number: int,
        is_raise: bool,
        is_lower: bool,
    ) -> None:
        self._entry = entry
        self._btn_number = btn_number
        self._btn_key = str(btn_number)
        self._is_raise = is_raise
        self._is_lower = is_lower
        self._attr_unique_id = f"{entry.entry_id}_button_{btn_number}_enabled"

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        cfg = self._entry.options.get("buttons", {}).get(self._btn_key, {})
        return cfg.get("label") or f"Button {self._btn_number}"

    @property
    def icon(self) -> str:
        if self._is_raise:
            return "mdi:arrow-up-circle"
        if self._is_lower:
            return "mdi:arrow-down-circle"
        return "mdi:button-pointer"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def is_on(self) -> bool:
        return self._entry.options.get("buttons", {}).get(
            self._btn_key, {}
        ).get("enabled", True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._entry.add_update_listener(self._on_entry_updated)
        )

    async def _on_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        self._entry = entry
        self.async_write_ha_state()

    # ── Actions ───────────────────────────────────────────────────────────────

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_enabled(False)

    async def _set_enabled(self, value: bool) -> None:
        buttons = dict(self._entry.options.get("buttons", {}))
        btn_data = dict(buttons.get(self._btn_key, {}))
        btn_data["enabled"] = value
        buttons[self._btn_key] = btn_data
        self.hass.config_entries.async_update_entry(
            self._entry, options={"buttons": buttons}
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
