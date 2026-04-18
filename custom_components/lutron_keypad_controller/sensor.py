"""Sensor platform for Lutron Keypad Controller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_KEYPAD_TYPE, KEYPAD_GENERIC, ATTR_ACTIVE_SCENE

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Any = None,
) -> None:
    controllers = hass.data.get(DOMAIN, {}).get("controllers", [])
    entities = []
    for ctrl in controllers:
        entities.append(LutronKeypadsStatusSensor(None, ctrl))
        entities.append(LutronKeypadsLastButtonSensor(None, ctrl))
    async_add_entities(entities, True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    ctrl = hass.data.get(DOMAIN, {}).get("entry_controllers", {}).get(entry.entry_id)
    if ctrl is None:
        return
    async_add_entities([
        LutronKeypadsStatusSensor(entry, ctrl),
        LutronKeypadsLastButtonSensor(entry, ctrl),
    ], True)


class LutronKeypadsStatusSensor(RestoreEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry | None, controller) -> None:
        self._entry = entry
        self._controller = controller
        if entry is not None:
            self._attr_unique_id = f"{entry.entry_id}_status"
        else:
            self._attr_unique_id = f"lutron_keypad_{controller.name.lower().replace(' ', '_')}_status"

    @property
    def name(self) -> str:
        return "Status"

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._entry is None:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._entry is not None:
            self.async_on_remove(
                self._entry.add_update_listener(self._on_entry_updated)
            )

    async def _on_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        self._entry = entry
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        la = self._controller._last_action
        if la is None:
            return "idle"
        scene = la.get("scene_id", "")
        if scene:
            return scene.replace("scene.", "").replace("_", " ").title()
        return la.get("type", "active")

    @property
    def extra_state_attributes(self) -> dict:
        la = self._controller._last_action
        if la is None:
            return {ATTR_ACTIVE_SCENE: None, "active_button": None}
        return {
            ATTR_ACTIVE_SCENE:    la.get("scene_id"),
            "active_button":      la.get("button"),
            "last_action_type":   la.get("type"),
        }

    @property
    def icon(self) -> str:
        return "mdi:remote"


class LutronKeypadsLastButtonSensor(RestoreEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry | None, controller) -> None:
        self._entry = entry
        self._controller = controller
        if entry is not None:
            self._attr_unique_id = f"{entry.entry_id}_last_button"
        else:
            self._attr_unique_id = f"lutron_keypad_{controller.name.lower().replace(' ', '_')}_last_button"

    @property
    def name(self) -> str:
        return "Last Button"

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._entry is None:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._entry is not None:
            self.async_on_remove(
                self._entry.add_update_listener(self._on_entry_updated)
            )

    async def _on_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        self._entry = entry
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        la = self._controller._last_action
        if la is None:
            return None
        btn = la.get("button")
        if btn is None:
            return None
        btn_cfg = self._controller._buttons.get(btn, {})
        label = btn_cfg.get("label", "")
        return f"{btn}" + (f" — {label}" if label else "")

    @property
    def extra_state_attributes(self) -> dict:
        la = self._controller._last_action
        if la is None:
            return {}
        btn = la.get("button")
        if btn is None:
            return {}
        btn_cfg = self._controller._buttons.get(btn, {})
        return {
            "button_number": btn,
            "label":         btn_cfg.get("label", ""),
            "action_type":   btn_cfg.get("action_type", ""),
        }

    @property
    def icon(self) -> str:
        return "mdi:gesture-tap-button"
