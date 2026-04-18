"""Config flow for Lutron Keypad Controller.

Queries the already-running lutron_caseta integration for all known
button-capable devices and presents them as a searchable dropdown.
The user picks one device, the keypad type is auto-detected from
the Lutron device type string, and serial + area are pre-filled.
"""
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
    ACTION_LABEL_TO_TYPE,
    get_button_list,
)

_LOGGER = logging.getLogger(__name__)

# ── Lutron device-type string → our keypad type constant ─────────────────────
LUTRON_TYPE_MAP: dict[str, str] = {
    # SeeTouch
    "SeeTouchKeypad":               KEYPAD_SEETOUCH,
    "SeeTouchHybridKeypad":         KEYPAD_SEETOUCH_HYBRID,
    "HybridSeeTouch":               KEYPAD_SEETOUCH_HYBRID,
    "SeeTouch":                     KEYPAD_SEETOUCH,
    # Sunnata
    "SunnataKeypad":                KEYPAD_SUNNATA,
    "SunnataHybridKeypad":          KEYPAD_SUNNATA_HYBRID,
    "SunnataSwitchingKeypad":       KEYPAD_SUNNATA,
    "Sunnata":                      KEYPAD_SUNNATA,
    # Alisee
    "AliseeKeypad":                 KEYPAD_ALISEE,
    "Alisee":                       KEYPAD_ALISEE,
    # Palladiom
    "PalladiomKeypad":              KEYPAD_PALLADIOM,
    "Palladiom":                    KEYPAD_PALLADIOM,
    "PalladiomWirelessKeypad":      KEYPAD_PALLADIOM,
    # Tabletop
    "TabletopSeeTouch":             KEYPAD_TABLETOP,
    "SeeTouchTabletop":             KEYPAD_TABLETOP,
    "TabletopKeypad":               KEYPAD_TABLETOP,
    # Pico
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


# ── Config Flow ───────────────────────────────────────────────────────────────

class LutronKeypadsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Lutron Keypad Controller."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_keypads: list[dict] = []
        self._selected_device: dict | None = None

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
                },
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {vol.Required("name", default=suggested_name): str}
            ),
            description_placeholders={
                "area":        area_name or "—",
                "device_name": device_name,
                "keypad_type": keypad_type,
                "serial":      serial,
                "lutron_type": device_type,
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
    """Single-page options form: label + action type for every button."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        keypad_type = self.config_entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
        all_buttons = get_button_list(keypad_type)
        existing    = dict(self.config_entry.options.get("buttons", {}))

        configurable = [b for b in all_buttons if not b["is_raise"] and not b["is_lower"]]
        fixed        = [b for b in all_buttons if b["is_raise"] or b["is_lower"]]

        if user_input is not None:
            new_buttons: dict[str, dict] = dict(existing)

            for btn in configurable:
                n          = str(btn["number"])
                label_key  = f"button_{n}_label"
                action_key = f"button_{n}_action_type"

                label        = user_input.get(label_key, "").strip()
                action_label = user_input.get(action_key, ACTION_TYPE_LABELS[ACTION_NONE])
                action       = ACTION_LABEL_TO_TYPE.get(action_label, ACTION_NONE)

                btn_data = dict(existing.get(n, {}))
                # Clear stale entity config when action type changes
                if btn_data.get(CONF_ACTION_TYPE) != action:
                    btn_data.pop(CONF_ACTION_TARGET, None)
                    btn_data.pop(CONF_LED_ENTITY, None)
                    btn_data.pop("scene_group", None)

                btn_data["label"]       = label or f"Button {btn['number']}"
                btn_data[CONF_ACTION_TYPE] = action
                new_buttons[n] = btn_data

            for btn in fixed:
                n      = str(btn["number"])
                action = ACTION_RAISE if btn["is_raise"] else ACTION_LOWER
                new_buttons[n] = {
                    "label":       action.capitalize(),
                    CONF_ACTION_TYPE: action,
                }

            return self.async_create_entry(title="", data={"buttons": new_buttons})

        # Build per-button fields
        fields: dict = {}
        action_labels = list(ACTION_TYPE_LABELS.values())

        for btn in configurable:
            n   = str(btn["number"])
            cur = existing.get(n, {})
            cur_label        = cur.get("label", "")
            cur_action_raw   = cur.get(CONF_ACTION_TYPE, ACTION_NONE)
            cur_action_label = ACTION_TYPE_LABELS.get(cur_action_raw, ACTION_TYPE_LABELS[ACTION_NONE])

            fields[vol.Optional(f"button_{n}_label", default=cur_label)] = str
            fields[vol.Optional(f"button_{n}_action_type", default=cur_action_label)] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=action_labels,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            )

        fixed_lines = []
        for btn in fixed:
            icon   = "⬆️" if btn["is_raise"] else "⬇️"
            action = "Raise" if btn["is_raise"] else "Lower"
            fixed_lines.append(f"Button {btn['number']}: {icon} {action} (auto-assigned)")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(fields),
            description_placeholders={
                "fixed_buttons": "\n".join(fixed_lines) if fixed_lines else "",
            },
        )
