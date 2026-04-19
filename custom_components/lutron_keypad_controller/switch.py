"""Switch platform — per-button active-scene indicators.

State ON  = this button's scene is the currently active scene.
State OFF = a different scene is active (or none).

Turning ON  → triggers the button's configured action (same as a physical press).
Turning OFF → no-op (another button's scene must be activated to change state).

State is driven exclusively by LutronKeypadsController._sync_leds, which is
called on every button press (physical or via this switch).  The physical
Lutron LEDs are managed by the bridge as part of scene activation and do not
need to be written to from HA.
"""
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
        LutronButtonSwitch(hass, entry, btn["number"], btn["is_raise"], btn["is_lower"])
        for btn in get_button_layout(entry.data)
    ]
    async_add_entities(entities, True)


class LutronButtonSwitch(SwitchEntity):
    """LED state indicator for a single keypad button.

    ON  = LED lit on physical keypad / this scene is active.
    Turning ON  triggers the button action (same as physical press).
    Turning OFF extinguishes the physical LED only.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        btn_number: int,
        is_raise: bool,
        is_lower: bool,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._btn_number = btn_number
        self._btn_key = str(btn_number)
        self._is_raise = is_raise
        self._is_lower = is_lower
        self._led_state: bool = False
        self._attr_unique_id = f"{entry.entry_id}_button_{btn_number}_led"

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
        return "mdi:circle-slice-8" if self._led_state else "mdi:circle-outline"

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
        return self._led_state

    def update_led_state(self, is_on: bool) -> None:
        """Called by the controller when LED state changes."""
        self._led_state = is_on
        self.async_write_ha_state()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _get_controller(self):
        return self._hass.data.get(DOMAIN, {}).get(
            "entry_controllers", {}
        ).get(self._entry.entry_id)

    async def async_added_to_hass(self) -> None:
        ctrl = self._get_controller()
        if ctrl is None:
            return

        ctrl.register_button_switch(self._btn_number, self)

        # Restore initial state from physical LED entity (read-only at startup)
        led_entity = ctrl._get_led_entity(self._btn_number)
        if led_entity:
            state = self.hass.states.get(led_entity)
            if state is not None:
                self._led_state = state.state == "on"

    # ── Actions ───────────────────────────────────────────────────────────────

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Trigger this button's configured action (same as a physical press)."""
        ctrl = self._get_controller()
        if ctrl is None:
            _LOGGER.debug("Button %d: no controller available", self._btn_number)
            return
        btn_cfg = ctrl._buttons.get(self._btn_number)
        if btn_cfg is None:
            _LOGGER.debug("Button %d: no action configured", self._btn_number)
            return
        await ctrl._dispatch(self._btn_number, btn_cfg)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """No-op — scene state is only cleared by activating another scene."""
        pass
