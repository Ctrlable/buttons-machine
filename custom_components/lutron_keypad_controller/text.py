"""Text platform — per-button label, entity target, LED, and scene group fields."""
from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_KEYPAD_TYPE,
    KEYPAD_GENERIC,
    ACTION_STATEFUL_SCENE,
    CONF_ACTION_TYPE,
    CONF_ACTION_TARGET,
    CONF_LED_ENTITY,
    ACTION_NONE,
    ACTION_TYPE_DOMAINS,
    ACTION_TYPES_NEEDING_ENTITY,
    MULTI_ENTITY_ACTIONS,
    get_button_layout,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    buttons_cfg = entry.options.get("buttons", {})
    entities: list[TextEntity] = []

    for btn in get_button_layout(entry.data):
        n      = str(btn["number"])
        action = buttons_cfg.get(n, {}).get(CONF_ACTION_TYPE, "")

        entities.append(LutronButtonLabelText(entry, btn["number"]))

        if not btn["is_raise"] and not btn["is_lower"]:
            entities.append(ButtonEntityText(entry, btn["number"]))

        if action == ACTION_STATEFUL_SCENE:
            entities.append(LutronButtonLedText(entry, btn["number"]))
            entities.append(LutronButtonSceneGroupText(entry, btn["number"]))

    async_add_entities(entities, True)


# ── Base class ────────────────────────────────────────────────────────────────

class _LutronButtonTextBase(TextEntity):
    _attr_has_entity_name = True
    _attr_should_poll     = False
    _attr_mode            = TextMode.TEXT
    _attr_native_min      = 0
    _attr_native_max      = 255

    def __init__(self, entry: ConfigEntry, btn_number: int) -> None:
        self._entry      = entry
        self._btn_number = btn_number
        self._btn_key    = str(btn_number)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Lutron",
            model=self._entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
                      .replace("_", " ").title(),
        )

    def _get_btn_cfg(self) -> dict:
        return self._entry.options.get("buttons", {}).get(self._btn_key, {})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._entry.add_update_listener(self._on_entry_updated)
        )

    async def _on_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        self._entry = entry
        self.async_write_ha_state()

    async def _save(self, field: str, value: str) -> None:
        buttons  = dict(self._entry.options.get("buttons", {}))
        btn_data = dict(buttons.get(self._btn_key, {}))
        btn_data[field] = value
        buttons[self._btn_key] = btn_data
        self.hass.config_entries.async_update_entry(
            self._entry, options={"buttons": buttons}
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)


# ── Entity target text entity ─────────────────────────────────────────────────

class ButtonEntityText(_LutronButtonTextBase):
    """Typed entity field with domain validation and autocomplete suggestions.

    Available only when the button's action type requires an entity target.
    Accepts comma-separated entity IDs for multi-entity action types.
    """

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_button_{self._btn_number}_entity_1"

    @property
    def name(self) -> str:
        label = self._get_btn_cfg().get("label") or f"Button {self._btn_number}"
        return f"{label} Entity"

    @property
    def icon(self) -> str:
        return "mdi:target"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_action_type(self) -> str:
        return self._get_btn_cfg().get(CONF_ACTION_TYPE, ACTION_NONE)

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._get_action_type() in ACTION_TYPES_NEEDING_ENTITY

    @property
    def native_value(self) -> str:
        raw = self._get_btn_cfg().get(CONF_ACTION_TARGET, "")
        if isinstance(raw, list):
            return ", ".join(raw)
        return raw or ""

    @property
    def extra_state_attributes(self) -> dict:
        action_type = self._get_action_type()
        domains     = ACTION_TYPE_DOMAINS.get(action_type, [])
        suggestions: list[str] = []
        if domains and self.hass:
            suggestions = sorted(
                s.entity_id
                for s in self.hass.states.async_all()
                if s.entity_id.split(".")[0] in domains
            )
        return {"domain_filter": domains, "suggestions": suggestions}

    # ── Action ────────────────────────────────────────────────────────────────

    async def async_set_value(self, value: str) -> None:
        value       = value.strip()
        action_type = self._get_action_type()
        domains     = ACTION_TYPE_DOMAINS.get(action_type, [])

        if value and domains:
            parts   = [p.strip() for p in value.split(",") if p.strip()]
            invalid = [p for p in parts if not any(p.startswith(f"{d}.") for d in domains)]
            if invalid:
                _LOGGER.warning(
                    "Button %d Entity: %s don't match expected domains %s — saving anyway",
                    self._btn_number, invalid, domains,
                )

        stored: str | list
        if action_type in MULTI_ENTITY_ACTIONS:
            stored = [p.strip() for p in value.split(",") if p.strip()]
        else:
            stored = value

        buttons  = dict(self._entry.options.get("buttons", {}))
        btn_data = dict(buttons.get(self._btn_key, {}))
        btn_data[CONF_ACTION_TARGET] = stored
        buttons[self._btn_key] = btn_data
        self.hass.config_entries.async_update_entry(
            self._entry, options={"buttons": buttons}
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)


# ── Label / LED / Scene Group ─────────────────────────────────────────────────

class LutronButtonLabelText(_LutronButtonTextBase):
    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_button_{self._btn_number}_label"

    @property
    def name(self) -> str:
        return f"Button {self._btn_number} Label"

    @property
    def icon(self) -> str:
        return "mdi:label-outline"

    @property
    def native_value(self) -> str:
        return self._get_btn_cfg().get("label") or f"Button {self._btn_number}"

    async def async_set_value(self, value: str) -> None:
        await self._save("label", value.strip() or f"Button {self._btn_number}")


class LutronButtonLedText(_LutronButtonTextBase):
    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_button_{self._btn_number}_led"

    @property
    def name(self) -> str:
        label = self._get_btn_cfg().get("label") or f"Button {self._btn_number}"
        return f"{label} LED Entity"

    @property
    def icon(self) -> str:
        return "mdi:led-on"

    @property
    def native_value(self) -> str | None:
        return self._get_btn_cfg().get(CONF_LED_ENTITY) or None

    async def async_set_value(self, value: str) -> None:
        await self._save(CONF_LED_ENTITY, value.strip())


class LutronButtonSceneGroupText(_LutronButtonTextBase):
    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_button_{self._btn_number}_scene_group"

    @property
    def name(self) -> str:
        label = self._get_btn_cfg().get("label") or f"Button {self._btn_number}"
        return f"{label} Scene Group"

    @property
    def icon(self) -> str:
        return "mdi:group"

    @property
    def native_value(self) -> str | None:
        return self._get_btn_cfg().get("scene_group") or None

    async def async_set_value(self, value: str) -> None:
        await self._save("scene_group", value.strip())
