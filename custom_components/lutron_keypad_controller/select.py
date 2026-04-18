"""Select platform — action type dropdown and entity picker per button."""
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
    ACTION_TYPE_DOMAINS,
    MULTI_ENTITY_ACTIONS,
    get_button_list,
)

_LOGGER = logging.getLogger(__name__)

_ALL_ACTION_LABELS = list(ACTION_TYPE_LABELS.values())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    keypad_type = entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
    buttons_cfg = entry.options.get("buttons", {})
    entities = []

    for btn in get_button_list(keypad_type):
        n        = str(btn["number"])
        action   = buttons_cfg.get(n, {}).get(CONF_ACTION_TYPE, "")
        is_fixed = btn["is_raise"] or btn["is_lower"]

        entities.append(
            LutronButtonActionSelect(entry, btn["number"], btn["is_raise"], btn["is_lower"])
        )

        if not is_fixed and ACTION_TYPE_DOMAINS.get(action):
            entities.append(ButtonEntitySelect(entry, btn["number"], 1))
            if action in MULTI_ENTITY_ACTIONS:
                for slot in (2, 3, 4):
                    entities.append(ButtonEntitySelect(entry, btn["number"], slot))

    async_add_entities(entities, True)


# ── Action type select ────────────────────────────────────────────────────────

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


# ── Entity picker select ──────────────────────────────────────────────────────

class ButtonEntitySelect(SelectEntity):
    """Entity picker whose options are filtered by the button's current action type."""

    _attr_has_entity_name = True
    _attr_should_poll     = False

    def __init__(self, entry: ConfigEntry, btn_number: int, slot: int) -> None:
        self._entry      = entry
        self._btn_number = btn_number
        self._btn_key    = str(btn_number)
        self._slot       = slot
        self._attr_unique_id = f"{entry.entry_id}_button_{btn_number}_entity_{slot}"
        self._attr_options   = []

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        cfg   = self._entry.options.get("buttons", {}).get(self._btn_key, {})
        label = cfg.get("label") or f"Button {self._btn_number}"
        return f"{label} Entity" if self._slot == 1 else f"{label} Entity {self._slot}"

    @property
    def icon(self) -> str:
        return "mdi:target"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_action_type(self) -> str:
        return self._entry.options.get("buttons", {}).get(
            self._btn_key, {}
        ).get(CONF_ACTION_TYPE, ACTION_NONE)

    def _get_targets(self) -> list[str]:
        raw = self._entry.options.get("buttons", {}).get(
            self._btn_key, {}
        ).get(CONF_ACTION_TARGET, "")
        if isinstance(raw, list):
            return list(raw)
        if isinstance(raw, str) and raw:
            return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def options(self) -> list[str]:
        if not self.hass:
            return []
        domains = ACTION_TYPE_DOMAINS.get(self._get_action_type(), [])
        if not domains:
            return []
        return sorted(
            s.entity_id
            for s in self.hass.states.async_all()
            if s.entity_id.split(".")[0] in domains
        )

    @property
    def current_option(self) -> str | None:
        targets = self._get_targets()
        idx     = self._slot - 1
        return targets[idx] if idx < len(targets) else None

    @property
    def available(self) -> bool:
        if not ACTION_TYPE_DOMAINS.get(self._get_action_type()):
            return False
        if self._slot > 1:
            return len(self._get_targets()) >= self._slot - 1
        return True

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

    async def async_select_option(self, option: str) -> None:
        action_type = self._get_action_type()
        targets     = self._get_targets()

        idx = self._slot - 1
        while len(targets) <= idx:
            targets.append("")
        targets[idx] = option
        targets = targets[:idx + 1]  # clear any subsequent slots

        value: str | list
        if action_type in MULTI_ENTITY_ACTIONS:
            value = [t for t in targets if t]
        else:
            value = option

        buttons  = dict(self._entry.options.get("buttons", {}))
        btn_data = dict(buttons.get(self._btn_key, {}))
        btn_data[CONF_ACTION_TARGET] = value
        buttons[self._btn_key] = btn_data
        self.hass.config_entries.async_update_entry(
            self._entry, options={"buttons": buttons}
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
