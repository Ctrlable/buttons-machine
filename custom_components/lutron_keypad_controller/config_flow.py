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
    CONF_BUTTON_LABEL,
    CONF_ACTION_TYPE,
    CONF_ACTION_TARGET,
    CONF_ACTION_PARAMS,
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
    ACTION_STATEFUL_SCENE,
    ACTION_HA_SCENE,
    ACTION_AUTOMATION,
    ACTION_SCRIPT,
    ACTION_ENTITY_TOGGLE,
    ACTION_COVER_CYCLE,
    ACTION_LIGHT_CYCLE_DIM,
    ACTION_RAISE,
    ACTION_LOWER,
    ACTION_NONE,
    DIM_CYCLE_LEVELS,
)

_LOGGER = logging.getLogger(__name__)

# ── Lutron device-type string → our keypad type constant ─────────────────────
# Type strings as reported by pylutron-caseta in device["type"].
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

# Fuzzy fallback (substring match, lower-cased)
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

# Type-string keywords that flag a device as button-capable
BUTTON_TYPE_KEYWORDS = {
    "keypad", "pico", "remote", "seetouch", "sunnata",
    "alisee", "palladiom", "tabletop", "hybrid",
}

# ── Button layout per keypad type ─────────────────────────────────────────────
# (main_button_count, has_raise_lower)
_KEYPAD_LAYOUTS: dict[str, tuple[int, bool]] = {
    KEYPAD_SEETOUCH:        (6,  True),
    KEYPAD_SEETOUCH_HYBRID: (5,  True),
    KEYPAD_SUNNATA:         (4,  True),
    KEYPAD_SUNNATA_HYBRID:  (3,  True),
    KEYPAD_ALISEE:          (5,  True),
    KEYPAD_PALLADIOM:       (5,  True),
    KEYPAD_TABLETOP:        (10, False),
    KEYPAD_PICO:            (3,  False),
    KEYPAD_GENERIC:         (6,  True),
}

_SAVE_KEY = "__save__"

_ACTION_TYPE_OPTIONS: dict[str, str] = {
    ACTION_STATEFUL_SCENE:  "Stateful Scene (tracks active button, LED control)",
    ACTION_HA_SCENE:        "HA Scene",
    ACTION_AUTOMATION:      "Automation",
    ACTION_SCRIPT:          "Script",
    ACTION_ENTITY_TOGGLE:   "Entity Toggle",
    ACTION_COVER_CYCLE:     "Cover Cycle (open → stop → close)",
    ACTION_LIGHT_CYCLE_DIM: "Light Dim Cycle (100 → 75 → 50 → 25 → off)",
    ACTION_NONE:            "None (no action)",
}


def _get_button_list(keypad_type: str) -> list[dict]:
    """Return ordered button descriptors for the given keypad type."""
    main_count, has_rl = _KEYPAD_LAYOUTS.get(
        keypad_type, _KEYPAD_LAYOUTS[KEYPAD_GENERIC]
    )
    buttons = [
        {"number": i, "is_raise": False, "is_lower": False}
        for i in range(1, main_count + 1)
    ]
    if has_rl:
        buttons.append({"number": main_count + 1, "is_raise": True,  "is_lower": False})
        buttons.append({"number": main_count + 2, "is_raise": False, "is_lower": True})
    return buttons


def _infer_keypad_type(device_type: str) -> str:
    """Map a Lutron device type string to our keypad type constant."""
    if device_type in LUTRON_TYPE_MAP:
        return LUTRON_TYPE_MAP[device_type]
    lower = device_type.lower()
    for keyword, kp_type in LUTRON_TYPE_FUZZY:
        if keyword in lower:
            return kp_type
    return KEYPAD_GENERIC


def _is_keypad_device(device: dict) -> bool:
    """Return True if this device is a keypad or button remote."""
    device_type: str = device.get("type", "")
    if device_type in LUTRON_TYPE_MAP:
        return True
    lower = device_type.lower()
    return any(kw in lower for kw in BUTTON_TYPE_KEYWORDS)


def _get_lutron_bridge(hass: HomeAssistant):
    """Return the first Smartbridge from a fully-loaded lutron_caseta entry.

    Modern HA (2023.6+) stores integration data in entry.runtime_data, not
    hass.data[DOMAIN].  We walk config entries first, then fall back to the
    old hass.data dict layout for installations on older HA versions.
    Returns None if no entry is loaded yet (caller treats this as "retry").
    """
    for entry in hass.config_entries.async_entries("lutron_caseta"):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        # Modern layout: entry.runtime_data is a LutronCasetaData dataclass
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            bridge = getattr(runtime, "bridge", None)
            if bridge is not None:
                return bridge
        # Legacy layout: hass.data["lutron_caseta"][entry_id]["bridge"]
        entry_data = hass.data.get("lutron_caseta", {}).get(entry.entry_id)
        if entry_data is not None:
            bridge = getattr(entry_data, "bridge", None)
            if bridge is None and isinstance(entry_data, dict):
                bridge = entry_data.get("bridge")
            if bridge is not None:
                return bridge
    return None


def _discover_keypads(hass: HomeAssistant) -> list[dict]:
    """Return all keypad/remote devices from the connected Lutron bridge."""
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
    """Build {serial: display_label} for the dropdown selector."""
    options: dict[str, str] = {}
    for device in keypads:
        serial = str(device.get("serial", ""))
        if not serial:
            continue
        area      = device.get("area_name", "Unknown Area")
        name      = device.get("name", "Unknown")
        ktype     = _infer_keypad_type(device.get("type", ""))
        options[serial] = f"{area} — {name}  [{ktype}]"
    return options


# ── Config Flow ───────────────────────────────────────────────────────────────

class LutronKeypadsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Lutron Keypad Controller.

    Step 1 (user)    — searchable dropdown of all keypads on the bridge
    Step 2 (confirm) — auto-filled summary; user sets a friendly name
    Fallback (manual)— shown when the bridge is unavailable
    """

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_keypads: list[dict] = []
        self._selected_device: dict | None = None

    # ── Step 1: device picker ─────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        # Hard abort only when lutron_caseta is not configured at all.
        lutron_entries = self.hass.config_entries.async_entries("lutron_caseta")
        if not lutron_entries:
            return self.async_abort(reason="lutron_not_loaded")

        # Discover on first visit (reset if we previously got nothing)
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

    # ── Step 2: confirm / name ────────────────────────────────────────────────

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

    # ── Fallback: manual entry ────────────────────────────────────────────────

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Shown when the bridge is unreachable and auto-discovery failed."""
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

    # ── Options flow ──────────────────────────────────────────────────────────

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LutronKeypadsOptionsFlow()


class LutronKeypadsOptionsFlow(config_entries.OptionsFlow):
    """Wizard-style options flow: one button at a time, native entity pickers."""

    def __init__(self) -> None:
        self._button_list: list[dict] = []
        self._wizard: dict[str, Any] = {}
        self._editing_from_review: bool = False

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _btn_info(self) -> dict:
        n = self._wizard["current_button"]
        return next(b for b in self._button_list if b["number"] == n)

    def _btn_index(self) -> int:
        n = self._wizard["current_button"]
        return next(i for i, b in enumerate(self._button_list) if b["number"] == n)

    def _advance(self) -> bool:
        """Move to next button; return False when past the last one."""
        idx = self._btn_index()
        if idx + 1 < len(self._button_list):
            self._wizard["current_button"] = self._button_list[idx + 1]["number"]
            return True
        return False

    def _progress(self) -> dict[str, str]:
        n   = self._wizard["current_button"]
        idx = self._btn_index()
        return {
            "current_button": str(n),
            "button_index":   str(idx + 1),
            "total_buttons":  str(self._wizard["total_buttons"]),
        }

    def _suggest_label(self, target: Any) -> str:
        entity_id: str = target[0] if isinstance(target, list) and target else (target or "")
        if not entity_id:
            return ""
        name = entity_id.split(".", 1)[-1]
        area = self.config_entry.data.get(CONF_AREA_NAME, "").lower().replace(" ", "_")
        if area and name.lower().startswith(area + "_"):
            name = name[len(area) + 1:]
        return name.replace("_", " ").title()

    def _build_summary(self) -> str:
        lines: list[str] = []
        for btn in self._button_list:
            n   = str(btn["number"])
            cfg = self._wizard["buttons"].get(n, {})
            if btn["is_raise"]:
                lines.append(f"Button {n}: Raise  ⬆️  [raise]")
            elif btn["is_lower"]:
                lines.append(f"Button {n}: Lower  ⬇️  [lower]")
            else:
                lbl   = cfg.get(CONF_BUTTON_LABEL) or "—"
                atype = cfg.get(CONF_ACTION_TYPE)  or "unassigned"
                tgt   = cfg.get(CONF_ACTION_TARGET, "")
                if isinstance(tgt, list):
                    tgt = ", ".join(tgt)
                suffix = f" → {tgt}" if tgt else ""
                lines.append(f"Button {n}: {lbl}  [{atype}{suffix}]")
        return "\n".join(lines)

    def _entity_schema(self, action: str, current: dict) -> vol.Schema:
        """Build the entity-picker schema for the given action type."""
        cur_tgt = current.get(CONF_ACTION_TARGET)

        if action == ACTION_STATEFUL_SCENE:
            led = current.get(CONF_LED_ENTITY)
            led_key = (vol.Optional(CONF_LED_ENTITY, default=led)
                       if led else vol.Optional(CONF_LED_ENTITY))
            fields: dict = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, str) and cur_tgt else vol.UNDEFINED,
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="scene")),
                led_key: selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional("scene_group", default=current.get("scene_group", "")): str,
            }

        elif action == ACTION_HA_SCENE:
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, str) and cur_tgt else vol.UNDEFINED,
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="scene")),
            }

        elif action == ACTION_AUTOMATION:
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, str) and cur_tgt else vol.UNDEFINED,
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="automation")),
            }

        elif action == ACTION_SCRIPT:
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, str) and cur_tgt else vol.UNDEFINED,
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="script")),
            }

        elif action == ACTION_ENTITY_TOGGLE:
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, list) else [],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch", "fan", "cover", "input_boolean"],
                        multiple=True,
                    )
                ),
            }

        elif action == ACTION_COVER_CYCLE:
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, list) else [],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover", multiple=True)
                ),
            }

        elif action == ACTION_LIGHT_CYCLE_DIM:
            existing = current.get(CONF_ACTION_PARAMS, {}).get("levels", DIM_CYCLE_LEVELS)
            fields = {
                vol.Required(
                    CONF_ACTION_TARGET,
                    default=cur_tgt if isinstance(cur_tgt, list) else [],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
                vol.Optional(
                    "dim_levels",
                    default=", ".join(str(l) for l in existing),
                ): str,
            }

        else:
            fields = {}

        return vol.Schema(fields)

    # ─────────────────────────────────────────────────────────────────────────
    # Init — bootstrap wizard from saved options, jump to button 1
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        keypad_type = self.config_entry.data.get(CONF_KEYPAD_TYPE, KEYPAD_GENERIC)
        self._button_list = _get_button_list(keypad_type)
        self._wizard = {
            "current_button": self._button_list[0]["number"],
            "total_buttons":  len(self._button_list),
            "buttons":        dict(self.config_entry.options.get("buttons", {})),
        }
        self._editing_from_review = False
        return await self.async_step_action()

    # ─────────────────────────────────────────────────────────────────────────
    # Page 1 — Choose action type
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_action(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        btn_info = self._btn_info()
        btn_key  = str(self._wizard["current_button"])

        # Raise/lower buttons are auto-assigned — show confirmation only
        if btn_info["is_raise"] or btn_info["is_lower"]:
            action = ACTION_RAISE if btn_info["is_raise"] else ACTION_LOWER
            self._wizard["buttons"][btn_key] = {
                CONF_BUTTON_LABEL: action.capitalize(),
                CONF_ACTION_TYPE:  action,
            }
            return await self.async_step_auto()

        current_action = self._wizard["buttons"].get(btn_key, {}).get(CONF_ACTION_TYPE, ACTION_NONE)

        if user_input is not None:
            chosen = user_input[CONF_ACTION_TYPE]
            old    = self._wizard["buttons"].get(btn_key, {}).get(CONF_ACTION_TYPE)
            # Clear stale entity config when action type changes
            if chosen != old:
                self._wizard["buttons"][btn_key] = {CONF_ACTION_TYPE: chosen}
            else:
                self._wizard["buttons"].setdefault(btn_key, {})[CONF_ACTION_TYPE] = chosen

            if chosen in (ACTION_NONE,):
                self._wizard["buttons"][btn_key] = {
                    CONF_BUTTON_LABEL: "", CONF_ACTION_TYPE: ACTION_NONE
                }
                if self._editing_from_review:
                    self._editing_from_review = False
                    return await self.async_step_review()
                if not self._advance():
                    return await self.async_step_review()
                return await self.async_step_action()

            if chosen in (ACTION_RAISE, ACTION_LOWER):
                self._wizard["buttons"][btn_key] = {
                    CONF_BUTTON_LABEL: chosen.capitalize(), CONF_ACTION_TYPE: chosen
                }
                if self._editing_from_review:
                    self._editing_from_review = False
                    return await self.async_step_review()
                if not self._advance():
                    return await self.async_step_review()
                return await self.async_step_action()

            return await self.async_step_entity()

        return self.async_show_form(
            step_id="action",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACTION_TYPE, default=current_action): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=ACTION_STATEFUL_SCENE,  label="🎬  Scene (stateful)     — tracks active button, LED feedback"),
                                selector.SelectOptionDict(value=ACTION_HA_SCENE,        label="💡  Scene (simple)       — activates a scene"),
                                selector.SelectOptionDict(value=ACTION_AUTOMATION,      label="▶️   Automation           — triggers an automation"),
                                selector.SelectOptionDict(value=ACTION_SCRIPT,          label="📜  Script               — runs a script"),
                                selector.SelectOptionDict(value=ACTION_ENTITY_TOGGLE,   label="🔀  Toggle Entities      — lights, switches, fans, covers"),
                                selector.SelectOptionDict(value=ACTION_COVER_CYCLE,     label="🪟  Shade Cycle          — open → stop → close"),
                                selector.SelectOptionDict(value=ACTION_LIGHT_CYCLE_DIM, label="🔆  Dim Cycle            — 100% → 75% → 50% → 25% → off"),
                                selector.SelectOptionDict(value=ACTION_RAISE,           label="⬆️   Raise                — context-aware raise"),
                                selector.SelectOptionDict(value=ACTION_LOWER,           label="⬇️   Lower                — context-aware lower"),
                                selector.SelectOptionDict(value=ACTION_NONE,            label="➖  None / Skip          — no action assigned"),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
            description_placeholders=self._progress(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Auto-assign confirmation (raise/lower buttons)
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_auto(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        btn_info = self._btn_info()
        action   = ACTION_RAISE if btn_info["is_raise"] else ACTION_LOWER

        if user_input is not None:
            if self._editing_from_review:
                self._editing_from_review = False
                return await self.async_step_review()
            if not self._advance():
                return await self.async_step_review()
            return await self.async_step_action()

        return self.async_show_form(
            step_id="auto",
            data_schema=vol.Schema({}),
            description_placeholders={
                **self._progress(),
                "action": action,
                "icon":   "⬆️" if action == ACTION_RAISE else "⬇️",
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Page 2 — Pick entity / target
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        btn_key = str(self._wizard["current_button"])
        action  = self._wizard["buttons"].get(btn_key, {}).get(CONF_ACTION_TYPE, ACTION_NONE)
        current = self._wizard["buttons"].get(btn_key, {})

        if user_input is not None:
            cfg = self._wizard["buttons"].setdefault(btn_key, {})

            tgt = user_input.get(CONF_ACTION_TARGET)
            if tgt is not None:
                cfg[CONF_ACTION_TARGET] = tgt

            led = user_input.get(CONF_LED_ENTITY)
            if led:
                cfg[CONF_LED_ENTITY] = led
            elif CONF_LED_ENTITY in user_input:
                cfg.pop(CONF_LED_ENTITY, None)

            grp = user_input.get("scene_group", "").strip()
            if grp:
                cfg["scene_group"] = grp
            else:
                cfg.pop("scene_group", None)

            raw_levels = user_input.get("dim_levels", "")
            if raw_levels:
                parsed = [int(x.strip()) for x in str(raw_levels).split(",")
                          if x.strip().isdigit()]
                if parsed:
                    cfg.setdefault(CONF_ACTION_PARAMS, {})["levels"] = parsed

            return await self.async_step_label()

        return self.async_show_form(
            step_id="entity",
            data_schema=self._entity_schema(action, current),
            description_placeholders={**self._progress(), "action_type": action},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Page 3 — Label & confirm
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_label(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        btn_key   = str(self._wizard["current_button"])
        cfg       = self._wizard["buttons"].get(btn_key, {})
        action    = cfg.get(CONF_ACTION_TYPE, "")
        target    = cfg.get(CONF_ACTION_TARGET, "")
        suggested = cfg.get(CONF_BUTTON_LABEL) or self._suggest_label(target)

        if user_input is not None:
            label = (user_input.get(CONF_BUTTON_LABEL) or suggested).strip()
            self._wizard["buttons"][btn_key][CONF_BUTTON_LABEL] = label
            if self._editing_from_review:
                self._editing_from_review = False
                return await self.async_step_review()
            if not self._advance():
                return await self.async_step_review()
            return await self.async_step_action()

        target_str = ", ".join(target) if isinstance(target, list) else (target or "—")
        return self.async_show_form(
            step_id="label",
            data_schema=vol.Schema(
                {vol.Required(CONF_BUTTON_LABEL, default=suggested): str}
            ),
            description_placeholders={
                **self._progress(),
                "action_type":   action,
                "action_target": target_str,
                "led_entity":    cfg.get(CONF_LED_ENTITY, "") or "—",
                "scene_group":   cfg.get("scene_group", "") or "—",
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Final — Review & Save
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            if user_input.get("action") == "save":
                return self.async_create_entry(
                    title="", data={"buttons": self._wizard["buttons"]}
                )
            return await self.async_step_edit()

        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="save"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value="save", label="✓  Save"),
                                selector.SelectOptionDict(value="edit", label="← Edit a button"),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={"summary": self._build_summary()},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Edit — Pick which button to re-configure
    # ─────────────────────────────────────────────────────────────────────────

    async def async_step_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._wizard["current_button"] = int(user_input["button"])
            self._editing_from_review = True
            return await self.async_step_action()

        options: dict[str, str] = {}
        for btn in self._button_list:
            n   = str(btn["number"])
            cfg = self._wizard["buttons"].get(n, {})
            if btn["is_raise"]:
                options[n] = f"Button {n} — Raise ⬆️  (auto)"
            elif btn["is_lower"]:
                options[n] = f"Button {n} — Lower ⬇️  (auto)"
            else:
                lbl   = cfg.get(CONF_BUTTON_LABEL, "")
                atype = cfg.get(CONF_ACTION_TYPE, "")
                options[n] = (
                    f"Button {n}" +
                    (f" — {lbl}" if lbl else "") +
                    (f"  [{atype}]" if atype else "  (unassigned)")
                )

        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema({vol.Required("button"): vol.In(options)}),
        )
