"""Select platform — action type dropdown per button."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_KEYPAD_TYPE,
    KEYPAD_GENERIC,
    CONF_ACTION_TYPE,
    CONF_ACTION_TARGET,
    ACTION_NONE,
    ACTION_TYPE_LABELS,
    ACTION_LABEL_TO_TYPE,
    get_button_layout,
)

_LOGGER = logging.getLogger(__name__)

_ALL_ACTION_LABELS = list(ACTION_TYPE_LABELS.values())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = [
        LutronButtonActionSelect(entry, btn["number"], btn["is_raise"], btn["is_lower"])
        for btn in get_button_layout(entry.data)
    ]
    async_add_entities(entities, True)


class LutronButtonActionSelect(SelectEntity):
    """Dropdown to change a button's action type inline on the device page."""

    _attr_has_entity_name = True
    _attr_should_poll     = False

    def __init__(
        self,
        entry: ConfigEntry,
        btn_number: int,
        is_raise: bool,
        is_lower: bool,
    ) -> None:
        self._entry      = entry
        self._btn_number = btn_number
        self._btn_key    = str(btn_number)
        self._is_raise   = is_raise
        self._is_lower   = is_lower
        self._attr_unique_id = f"{entry.entry_id}_button_{btn_number}_action_type"
        self._attr_options   = _ALL_ACTION_LABELS

    @property
    def name(self) -> str:
        cfg = self._entry.options.get("buttons", {}).get(self._btn_key, {})
        label = cfg.get("label") or f"Button {self._btn_number}"
        return f"{label} Action Type"

    @property
    def icon(self) -> str:
        return "mdi:gesture-tap"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    @property
    def current_option(self) -> str:
        raw = self._entry.options.get("buttons", {}).get(
            self._btn_key, {}
        ).get(CONF_ACTION_TYPE, ACTION_NONE)
        return ACTION_TYPE_LABELS.get(raw, ACTION_TYPE_LABELS[ACTION_NONE])

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._entry.add_update_listener(self._on_entry_updated)
        )

    async def _on_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        self._entry = entry
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        raw      = ACTION_LABEL_TO_TYPE.get(option, ACTION_NONE)
        buttons  = dict(self._entry.options.get("buttons", {}))
        btn_data = dict(buttons.get(self._btn_key, {}))
        btn_data[CONF_ACTION_TYPE] = raw
        btn_data.pop(CONF_ACTION_TARGET, None)
        buttons[self._btn_key] = btn_data
        self.hass.config_entries.async_update_entry(
            self._entry, options={"buttons": buttons}
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
