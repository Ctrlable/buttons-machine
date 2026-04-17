"""Sensor platform for Lutron Keypad Controller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, ATTR_ACTIVE_SCENE

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
        entities.append(LutronKeypadsStatusSensor(ctrl))
        entities.append(LutronKeypadsLastButtonSensor(ctrl))
    async_add_entities(entities, True)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    pass


class LutronKeypadsStatusSensor(RestoreEntity, SensorEntity):
    def __init__(self, controller) -> None:
        self._controller = controller
        self._attr_name = f"{controller.name} Status"
        self._attr_unique_id = f"lutron_keypad_{controller.name.lower().replace(' ', '_')}_status"

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last:
            pass

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
            ATTR_ACTIVE_SCENE: la.get("scene_id"),
            "active_button": la.get("button"),
            "last_action_type": la.get("type"),
        }

    @property
    def icon(self) -> str:
        return "mdi:remote"


class LutronKeypadsLastButtonSensor(RestoreEntity, SensorEntity):
    def __init__(self, controller) -> None:
        self._controller = controller
        self._attr_name = f"{controller.name} Last Button"
        self._attr_unique_id = f"lutron_keypad_{controller.name.lower().replace(' ', '_')}_last_button"

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last:
            pass

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
            "label": btn_cfg.get("label", ""),
            "action_type": btn_cfg.get("action_type", ""),
        }

    @property
    def icon(self) -> str:
        return "mdi:gesture-tap-button"
