"""Config flow for Lutron Keypad Controller."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_NAME,
    CONF_AREA_NAME,
    CONF_KEYPAD_TYPE,
    CONF_ACTION_TYPE,
    CONF_ACTION_TARGET,
    CONF_LED_ENTITY,
    ACTION_STATEFUL_SCENE,
    KEYPAD_SEETOUCH,
    KEYPAD_SEETOUCH_HYBRID,
    KEYPAD_SUNNATA,
    KEYPAD_SUNNATA_HYBRID,
    KEYPAD_ALISEE,
    KEYPAD_PALLADIOM,
    KEYPAD_TABLETOP,
    KEYPAD_PICO,
    KEYPAD_GENERIC,
    ACTION_NONE,
    ACTION_RAISE,
    ACTION_LOWER,
    ACTION_TYPE_LABELS,
    ACTION_TYPE_DOMAINS,
    MULTI_ENTITY_ACTIONS,
    get_button_list,
    get_button_layout,
)

_LOGGER = logging.getLogger(__name__)

# ── Lutron device-type string → our keypad type ───────────────────────────────
LUTRON_TYPE_MAP: dict[str, str] = {
    "SeeTouchKeypad":               KEYPAD_SEETOUCH,
    "SeeTouchHybridKeypad":         KEYPAD_SEETOUCH_HYBRID,
    "HybridSeeTouch":               KEYPAD_SEETOUCH_HYBRID,
    "SeeTouch":                     KEYPAD_SEETOUCH,
    "SunnataKeypad":                KEYPAD_SUNNATA,
    "SunnataHybridKeypad":          KEYPAD_SUNNATA_HYBRID,
    "SunnataSwitchingKeypad":       KEYPAD_SUNNATA,
    "Sunnata":                      KEYPAD_SUNNATA,
    "AliseeKeypad":                 KEYPAD_ALISEE,
    "Alisee":                       KEYPAD_ALISEE,
    "PalladiomKeypad":              KEYPAD_PALLADIOM,
    "Palladiom":                    KEYPAD_PALLADIOM,
    "PalladiomWirelessKeypad":      KEYPAD_PALLADIOM,
    "TabletopSeeTouch":             KEYPAD_TABLETOP,
    "SeeTouchTabletop":             KEYPAD_TABLETOP,
    "TabletopKeypad":               KEYPAD_TABLETOP,
    "Pico1Button":                  KEYPAD_PICO,
    "Pico2Button":                  KEYPAD_PICO,
    "Pico2ButtonRaiseLower":        KEYPAD_PICO,
    "Pico3Button":                  KEYPAD_PICO,
    "Pico3ButtonRaiseLower":        KEYPAD_PICO,
    "Pico4Button":                  KEYPAD_PICO,
    "Pico4ButtonScene":             KEYPAD_PICO,
    "Pico4ButtonZone":              KEYPAD_PICO,
    "Pico4Button2Group":            KEYPAD_PICO,
    "FourGroupRemote":              KEYPAD_PICO,
    "PaddleRemote":                 KEYPAD_PICO,
}

LUTRON_TYPE_FUZZY: list[tuple[str, str]] = [
    ("hybrid",     KEYPAD_SEETOUCH_HYBRID),
    ("seetouch",   KEYPAD_SEETOUCH),
    ("sunnata",    KEYPAD_SUNNATA),
    ("alisee",     KEYPAD_ALISEE),
    ("palladiom",  KEYPAD_PALLADIOM),
    ("tabletop",   KEYPAD_TABLETOP),
    ("pico",       KEYPAD_PICO),
    ("remote",     KEYPAD_PICO),
    ("keypad",     KEYPAD_SEETOUCH),
]

BUTTON_TYPE_KEYWORDS = {
    "keypad", "pico", "remote", "seetouch", "sunnata",
    "alisee", "palladiom", "tabletop", "hybrid",
}


def _infer_keypad_type(device_type: str) -> str:
    if device_type in LUTRON_TYPE_MAP:
        return LUTRON_TYPE_MAP[device_type]
    lower = device_type.lower()
    for keyword, kp_type in LUTRON_TYPE_FUZZY:
        if keyword in lower:
            return kp_type
    return KEYPAD_GENERIC


def _is_keypad_device(device: dict) -> bool:
    device_type: str = device.get("type", "")
    if device_type in LUTRON_TYPE_MAP:
        return True
    lower = device_type.lower()
    return any(kw in lower for kw in BUTTON_TYPE_KEYWORDS)


def _get_lutron_bridge(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries("lutron_caseta"):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            bridge = getattr(runtime, "bridge", None)
            if bridge is not None:
                return bridge
        entry_data = hass.data.get("lutron_caseta", {}).get(entry.entry_id)
        if entry_data is not None:
            bridge = getattr(entry_data, "bridge", None)
            if bridge is None and isinstance(entry_data, dict):
                bridge = entry_data.get("bridge")
            if bridge is not None:
                return bridge
    return None


def _discover_keypads(hass: HomeAssistant) -> list[dict]:
    bridge = _get_lutron_bridge(hass)
    if bridge is None:
        return []
    try:
        all_devices: dict = bridge.get_devices()
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not query Lutron bridge devices: %s", exc)
        return []
    keypads = [d for d in all_devices.values() if _is_keypad_device(d)]
    keypads.sort(key=lambda d: (d.get("area_name", ""), d.get("name", "")))
    return keypads


def _build_device_options(keypads: list[dict]) -> dict[str, str]:
    options: dict[str, str] = {}
    for device in keypads:
        serial = str(device.get("serial", ""))
        if not serial:
            continue
        area  = device.get("area_name", "Unknown Area")
        name  = device.get("name", "Unknown")
        ktype = _infer_keypad_type(device.get("type", ""))
        options[serial] = f"{area} — {name}  [{ktype}]"
    return options


def _detect_button_layout(hass: HomeAssistant, serial: str, keypad_type: str) -> dict:
    """Query bridge.button_devices for the actual buttons on this device.

    Returns a dict with button_numbers / configurable_buttons / raise_button /
    lower_button to be stored in config entry data.  Returns {} on failure so
    the caller falls back to the family-based count.
    """
    bridge = _get_lutron_bridge(hass)
    if bridge is None:
        return {}

    button_devices: dict = getattr(bridge, "button_devices", None) or {}
    if not button_devices:
        _LOGGER.warning(
            "bridge.button_devices not available for serial %s; using fallback button count",
            serial,
        )
        return {}

    matching = [
        bd for bd in button_devices.values()
        if str(bd.get("serial", "")) == serial
    ]
    if not matching:
        _LOGGER.warning(
            "No button_devices matched serial %s; using fallback button count", serial
        )
        return {}

    button_numbers: list[int] = sorted(
        {int(bd["button_number"]) for bd in matching if "button_number" in bd}
    )
    if not button_numbers:
        return {}

    raise_btn: int | None = None
    lower_btn: int | None = None
    for bd in matching:
        name  = bd.get("name", "").lower()
        bnum  = int(bd.get("button_number", -1))
        if name.endswith((" raise", "-raise", " up", "-up")):
            raise_btn = bnum
        elif name.endswith((" lower", "-lower", " down", "-down")):
            lower_btn = bnum

    configurable = [n for n in button_numbers if n not in (raise_btn, lower_btn)]

    _LOGGER.debug(
        "Detected %d button(s) for serial %s: configurable=%s raise=%s lower=%s",
        len(button_numbers), serial, configurable, raise_btn, lower_btn,
    )
    return {
        "button_numbers":      button_numbers,
        "configurable_buttons": configurable,
        "raise_button":        raise_btn,
        "lower_button":        lower_btn,
    }


# ── Config Flow ───────────────────────────────────────────────────────────────

class LutronKeypadsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Lutron Keypad Controller."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_keypads: list[dict] = []
        self._selected_device: dict | None = None
        self._detected_layout: dict = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        lutron_entries = self.hass.config_entries.async_entries("lutron_caseta")
        if not lutron_entries:
            return self.async_abort(reason="lutron_not_loaded")

        if not self._discovered_keypads:
            self._discovered_keypads = await self.hass.async_add_executor_job(
                _discover_keypads, self.hass
            )

        if not self._discovered_keypads:
            return await self.async_step_manual()

        device_options = _build_device_options(self._discovered_keypads)
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_serial = user_input.get("device_serial", "")
            self._selected_device = next(
                (d for d in self._discovered_keypads
                 if str(d.get("serial", "")) == selected_serial),
                None,
            )
            if self._selected_device is None:
                errors["base"] = "device_not_found"
            else:
                await self.async_set_unique_id(selected_serial)
                self._abort_if_unique_id_configured()
                # Detect actual button layout from bridge
                serial      = str(self._selected_device.get("serial", ""))
                ktype       = _infer_keypad_type(self._selected_device.get("type", ""))
                self._detected_layout = _detect_button_layout(self.hass, serial, ktype)
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("device_serial"): vol.In(device_options)}
            ),
            errors=errors,
            description_placeholders={"count": str(len(self._discovered_keypads))},
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        device = self._selected_device
        if device is None:
            return await self.async_step_user()

        device_type    = device.get("type", "")
        keypad_type    = _infer_keypad_type(device_type)
        area_name      = device.get("area_name", "")
        device_name    = device.get("name", "")
        serial         = str(device.get("serial", ""))
        suggested_name = f"{area_name} — {device_name}" if area_name else device_name

        if user_input is not None:
            friendly_name = user_input.get("name", suggested_name).strip()
            return self.async_create_entry(
                title=friendly_name,
                data={
                    "name":             friendly_name,
                    CONF_DEVICE_SERIAL: serial,
                    CONF_DEVICE_NAME:   device_name,
                    CONF_AREA_NAME:     area_name,
                    CONF_KEYPAD_TYPE:   keypad_type,
                    "lutron_type":      device_type,
                    **self._detected_layout,
                },
            )

        btn_nums = self._detected_layout.get("button_numbers", [])
        if btn_nums:
            btn_str = f"{len(btn_nums)} buttons detected from bridge"
        else:
            fallback = get_button_list(keypad_type)
            btn_str  = f"{len(fallback)} buttons (estimated from keypad type)"

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {vol.Required("name", default=suggested_name): str}
            ),
            description_placeholders={
                "area":         area_name or "—",
                "device_name":  device_name,
                "keypad_type":  keypad_type,
                "serial":       serial,
                "lutron_type":  device_type,
                "button_count": btn_str,
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            serial = user_input.get(CONF_DEVICE_SERIAL, "").strip()
            if not serial:
                errors[CONF_DEVICE_SERIAL] = "serial_required"
            else:
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                name = user_input.get("name", serial).strip()
                return self.async_create_entry(
                    title=name,
                    data={
                        "name":             name,
                        CONF_DEVICE_SERIAL: serial,
                        CONF_DEVICE_NAME:   user_input.get(CONF_DEVICE_NAME, ""),
                        CONF_AREA_NAME:     user_input.get(CONF_AREA_NAME, ""),
                        CONF_KEYPAD_TYPE:   KEYPAD_GENERIC,
                        "lutron_type":      "",
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required(CONF_DEVICE_SERIAL): str,
                    vol.Optional(CONF_DEVICE_NAME, default=""): str,
                    vol.Optional(CONF_AREA_NAME, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "note": (
                    "Auto-discovery failed — the Lutron bridge may not be "
                    "reachable yet. Enter the serial manually: press any "
                    "button on the keypad and check "
                    "Developer Tools → Events → lutron_caseta_button_event."
                )
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LutronKeypadsOptionsFlow()


# ── Options Flow ──────────────────────────────────────────────────────────────

class LutronKeypadsOptionsFlow(config_entries.OptionsFlow):
    """Single-page options form with EntitySelector per button.

    Re-renders automatically when an action type changes so the entity
    selector domain filter updates to match the new action type.
    """

    # ── Internal helper ───────────────────────────────────────────────────────

    def _build_buttons_from_input(
        self,
        user_input: dict[str, Any],
        configurable: list[dict],
        fixed: list[dict],
        existing: dict,
    ) -> dict[str, dict]:
        new_buttons: dict[str, dict] = {}

        for btn in configurable:
            n          = str(btn["number"])
            btn_data   = dict(existing.get(n, {}))
            old_action = btn_data.get(CONF_ACTION_TYPE)

            label  = user_input.get(f"button_{n}_label", "").strip()
            action = user_input.get(f"button_{n}_action_type", ACTION_NONE)

            if old_action != action:
                btn_data.pop(CONF_ACTION_TARGET, None)
                btn_data.pop(CONF_LED_ENTITY, None)
                btn_data.pop("scene_group", None)

            btn_data["label"]          = label or f"Button {btn['number']}"
            btn_data[CONF_ACTION_TYPE] = action

            target_key = f"button_{n}_action_target"
            if target_key in user_input:
                target = user_input[target_key]
                if target:
                    btn_data[CONF_ACTION_TARGET] = target
                else:
                    btn_data.pop(CONF_ACTION_TARGET, None)

            led_key = f"button_{n}_led_entity"
            if led_key in user_input:
                led = user_input[led_key]
                if led:
                    btn_data[CONF_LED_ENTITY] = led
                else:
                    btn_data.pop(CONF_LED_ENTITY, None)

            sg_key = f"button_{n}_scene_group"
            if sg_key in user_input:
                sg = user_input[sg_key].strip() if isinstance(user_input[sg_key], str) else ""
                if sg:
                    btn_data["scene_group"] = sg
                else:
                    btn_data.pop("scene_group", None)

            new_buttons[n] = btn_data

        for btn in fixed:
            n      = str(btn["number"])
            action = ACTION_RAISE if btn["is_raise"] else ACTION_LOWER
            new_buttons[n] = {"label": action.capitalize(), CONF_ACTION_TYPE: action}

        return new_buttons

    # ── Main step ─────────────────────────────────────────────────────────────

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        all_buttons  = get_button_layout(self.config_entry.data)
        existing     = dict(self.config_entry.options.get("buttons", {}))
        configurable = [b for b in all_buttons if not b["is_raise"] and not b["is_lower"]]
        fixed        = [b for b in all_buttons if b["is_raise"] or b["is_lower"]]

        if user_input is not None:
            new_buttons = self._build_buttons_from_input(
                user_input, configurable, fixed, existing
            )

            # If any action type changed, save partial state and re-render so
            # the EntitySelector domain filter reflects the new action type.
            action_type_changed = any(
                user_input.get(f"button_{str(b['number'])}_action_type", ACTION_NONE)
                != existing.get(str(b["number"]), {}).get(CONF_ACTION_TYPE, ACTION_NONE)
                for b in configurable
            )
            if action_type_changed:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options={**self.config_entry.options, "buttons": new_buttons},
                )
                return await self.async_step_init()

            return self.async_create_entry(title="", data={"buttons": new_buttons})

        # Build form schema dynamically based on current action types
        fields: dict = {}
        action_options = [
            {"value": raw, "label": label}
            for raw, label in ACTION_TYPE_LABELS.items()
        ]

        for btn in configurable:
            n   = str(btn["number"])
            cur = existing.get(n, {})
            cur_label      = cur.get("label", "")
            cur_action_raw = cur.get(CONF_ACTION_TYPE, ACTION_NONE)
            domains        = ACTION_TYPE_DOMAINS.get(cur_action_raw, [])
            is_multi       = cur_action_raw in MULTI_ENTITY_ACTIONS

            fields[vol.Optional(f"button_{n}_label", default=cur_label)] = (
                selector.TextSelector()
            )
            fields[vol.Optional(f"button_{n}_action_type", default=cur_action_raw)] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=action_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            )

            if domains:
                cur_target = cur.get(CONF_ACTION_TARGET)
                target_key = (
                    vol.Optional(f"button_{n}_action_target", default=cur_target)
                    if cur_target
                    else vol.Optional(f"button_{n}_action_target")
                )
                fields[target_key] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=domains, multiple=is_multi)
                )

            if cur_action_raw == ACTION_STATEFUL_SCENE:
                cur_led = cur.get(CONF_LED_ENTITY)
                led_key = (
                    vol.Optional(f"button_{n}_led_entity", default=cur_led)
                    if cur_led
                    else vol.Optional(f"button_{n}_led_entity")
                )
                fields[led_key] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                )
                cur_sg = cur.get("scene_group", "")
                fields[vol.Optional(f"button_{n}_scene_group", default=cur_sg)] = (
                    selector.TextSelector()
                )

        fixed_lines = [
            f"Button {b['number']}: {'⬆️' if b['is_raise'] else '⬇️'} "
            f"{'Raise' if b['is_raise'] else 'Lower'} (auto-assigned)"
            for b in fixed
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(fields),
            description_placeholders={
                "fixed_buttons": "\n".join(fixed_lines) if fixed_lines else "",
            },
        )
