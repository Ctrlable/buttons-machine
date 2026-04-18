"""
Lutron Keypad Controller — custom component for Home Assistant
==============================================================

Listens for ``lutron_caseta_button_event`` events fired by the built-in
``lutron_caseta`` integration and routes them to configurable HA actions.

Supported keypads:
  SeeTouch · Hybrid SeeTouch · Sunnata · Hybrid Sunnata ·
  Alisee · Palladiom · Tabletop · Pico

Supported action types per button:
  stateful_scene  — activates an HA scene and tracks it as "active" on the keypad
                    (other buttons in the same group deactivate); LED feedback optional
  ha_scene        — plain HA scene, no state tracking
  automation      — triggers an automation
  script          — runs a script
  entity_toggle   — toggles one or more entities (lights, switches, etc.)
  cover_cycle     — cycles a cover: open → stop → close (repeatable)
  light_cycle_dim — cycles a light through dim levels: 100 % → 75 % → 50 % → 25 % → off
  raise           — raises shades OR brightens lights based on the last active action
  lower           — lowers shades OR dims lights based on the last active action
  none            — no-op placeholder

Configuration (add to configuration.yaml):

lutron_keypad_controller:
  keypads:
    - name: "Living Room Keypad"
      device_serial: "12345678"          # serial from Lutron, or match by device_name + area_name
      device_name: "Living Room"         # optional: used to match if serial not unique
      area_name: "Living Room"           # optional: used to match events
      keypad_type: sunnata               # one of: seetouch, seetouch_hybrid, sunnata,
                                         #   sunnata_hybrid, alisee, palladiom, tabletop, pico, generic
      scene_group: "living_room"         # optional: keypads sharing a group share stateful-scene state
      buttons:
        - button_number: 1
          label: "Movie"
          action_type: stateful_scene
          action_target: scene.living_room_movie
          led_entity: switch.living_room_keypad_led_1  # optional
        - button_number: 2
          label: "Bright"
          action_type: stateful_scene
          action_target: scene.living_room_bright
          led_entity: switch.living_room_keypad_led_2
        - button_number: 3
          label: "Off"
          action_type: ha_scene
          action_target: scene.living_room_off
        - button_number: 4
          label: "Shades Up"
          action_type: raise
          # no target needed — raise/lower act on the last active scene's covers/lights
        - button_number: 5
          label: "Shades Down"
          action_type: lower
        - button_number: 6
          label: "Fan Toggle"
          action_type: entity_toggle
          action_target:
            - fan.living_room_fan
        - button_number: 7
          label: "Dim Cycle"
          action_type: light_cycle_dim
          action_target:
            - light.living_room_cans
          action_params:
            levels: [100, 75, 50, 25]   # optional: override default dim levels
        - button_number: 8
          label: "Curtain Cycle"
          action_type: cover_cycle
          action_target:
            - cover.living_room_curtain
        - button_number: 9
          label: "Evening"
          action_type: automation
          action_target: automation.living_room_evening
        - button_number: 10
          label: "Party Script"
          action_type: script
          action_target: script.party_mode
          action_params:
            variables:
              room: living_room
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers import entity_platform, entity_registry as er
from homeassistant.const import (
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    SERVICE_TOGGLE,
    ATTR_ENTITY_ID,
)

from .const import (
    DOMAIN,
    LUTRON_EVENT,
    CONF_BUTTONS,
    CONF_BUTTON_NUMBER,
    CONF_BUTTON_LABEL,
    CONF_ACTION_TYPE,
    CONF_ACTION_TARGET,
    CONF_ACTION_PARAMS,
    CONF_LED_ENTITY,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_NAME,
    CONF_AREA_NAME,
    CONF_KEYPAD_TYPE,
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
    COVER_STATE_OPEN,
    COVER_STATE_STOP,
    COVER_STATE_CLOSE,
    RAISE_LOWER_STEP,
    ATTR_ACTIVE_SCENE,
    ATTR_LAST_ACTION,
    ATTR_COVER_STATES,
    ATTR_LIGHT_DIM_STEPS,
)

_LOGGER = logging.getLogger(__name__)

# ── YAML schema ───────────────────────────────────────────────────────────────

BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BUTTON_NUMBER): cv.positive_int,
        vol.Optional(CONF_BUTTON_LABEL, default=""): cv.string,
        vol.Required(CONF_ACTION_TYPE): vol.In(
            [
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
            ]
        ),
        vol.Optional(CONF_ACTION_TARGET): vol.Any(
            cv.entity_id, [cv.entity_id], cv.string
        ),
        vol.Optional(CONF_ACTION_PARAMS, default={}): dict,
        vol.Optional(CONF_LED_ENTITY): cv.entity_id,
    }
)

KEYPAD_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional(CONF_DEVICE_SERIAL, default=""): cv.string,
        vol.Optional(CONF_DEVICE_NAME, default=""): cv.string,
        vol.Optional(CONF_AREA_NAME, default=""): cv.string,
        vol.Optional(CONF_KEYPAD_TYPE, default="generic"): cv.string,
        vol.Optional("scene_group", default=""): cv.string,
        vol.Required(CONF_BUTTONS): vol.All(cv.ensure_list, [BUTTON_SCHEMA]),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("keypads"): vol.All(cv.ensure_list, [KEYPAD_SCHEMA]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[str] = ["sensor", "switch", "select", "text"]


def _build_buttons_from_options(buttons_options: dict) -> list[dict]:
    """Convert options {"1": {…}, "2": {…}} to a list suitable for LutronKeypadsController."""
    result = []
    for btn_num_str, btn_data in buttons_options.items():
        try:
            btn_num = int(btn_num_str)
        except ValueError:
            continue
        if not btn_data.get("enabled", True):
            continue
        action_type = btn_data.get(CONF_ACTION_TYPE, ACTION_NONE)
        if not action_type or action_type == ACTION_NONE:
            continue
        btn_cfg: dict = {
            CONF_BUTTON_NUMBER: btn_num,
            CONF_BUTTON_LABEL:  btn_data.get(CONF_BUTTON_LABEL, ""),
            CONF_ACTION_TYPE:   action_type,
        }
        target = btn_data.get(CONF_ACTION_TARGET, "")
        if target:
            # Parse comma-separated entity lists entered from the UI
            if isinstance(target, str) and "," in target:
                btn_cfg[CONF_ACTION_TARGET] = [t.strip() for t in target.split(",") if t.strip()]
            else:
                btn_cfg[CONF_ACTION_TARGET] = target
        if btn_data.get(CONF_LED_ENTITY):
            btn_cfg[CONF_LED_ENTITY] = btn_data[CONF_LED_ENTITY]
        if btn_data.get("scene_group"):
            btn_cfg["scene_group"] = btn_data["scene_group"]
        result.append(btn_cfg)
    return result


# ── Shared scene-group state ───────────────────────────────────────────────────
# scene_groups[group_name] = button_number of the last activated stateful scene
_SCENE_GROUPS: dict[str, int | None] = {}


# ── Setup ─────────────────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    keypads_cfg: list[dict] = config[DOMAIN].get("keypads", [])
    controllers: list[LutronKeypadsController] = []

    for kp_cfg in keypads_cfg:
        ctrl = LutronKeypadsController(hass, kp_cfg)
        controllers.append(ctrl)
        ctrl.async_register()

    hass.data[DOMAIN]["controllers"] = controllers
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry; reads button config from options (UI) first."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("controllers", [])
    hass.data[DOMAIN].setdefault("entry_controllers", {})

    buttons_cfg = _build_buttons_from_options(entry.options.get("buttons", {}))

    kp_cfg: dict = {
        "name":           entry.title,
        CONF_DEVICE_SERIAL: entry.data.get(CONF_DEVICE_SERIAL, ""),
        CONF_DEVICE_NAME:   entry.data.get(CONF_DEVICE_NAME, ""),
        CONF_AREA_NAME:     entry.data.get(CONF_AREA_NAME, ""),
        CONF_KEYPAD_TYPE:   entry.data.get(CONF_KEYPAD_TYPE, "generic"),
        CONF_BUTTONS:       buttons_cfg,
    }

    ctrl = LutronKeypadsController(hass, kp_cfg)
    if buttons_cfg:
        ctrl.async_register()
        _LOGGER.info("Keypad '%s' loaded from UI options with %d button(s)", entry.title, len(buttons_cfg))
    else:
        _LOGGER.info(
            "Keypad '%s' loaded (no buttons configured yet). "
            "Click the gear icon to configure buttons, or add YAML under lutron_keypad_controller:",
            entry.title,
        )

    hass.data[DOMAIN]["entry_controllers"][entry.entry_id] = ctrl
    hass.data[DOMAIN]["controllers"].append(ctrl)

    await _cleanup_orphaned_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _cleanup_orphaned_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove stale entity registry entries from older versions."""
    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        uid = reg_entry.unique_id
        # v2.1.x multi-slot text entities
        if any(f"_entity_{n}" in uid for n in ("2", "3", "4")):
            ent_reg.async_remove(reg_entry.entity_id)
            _LOGGER.info("Removed orphaned multi-slot entity: %s", reg_entry.entity_id)
        # v2.3.x text entities now replaced by read-only sensors
        elif reg_entry.entity_id.startswith("text.") and any(
            uid.endswith(s) for s in ("_entity_1", "_led", "_scene_group")
        ):
            ent_reg.async_remove(reg_entry.entity_id)
            _LOGGER.info("Removed old text entity (now a sensor): %s", reg_entry.entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    ctrl = hass.data[DOMAIN].get("entry_controllers", {}).pop(entry.entry_id, None)
    if ctrl is not None:
        ctrl.async_unregister()
        try:
            hass.data[DOMAIN]["controllers"].remove(ctrl)
        except ValueError:
            pass
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options are saved so new button config takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)


# ── Controller ────────────────────────────────────────────────────────────────

class LutronKeypadsController:
    """Manages a single Lutron keypad and dispatches button events."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass = hass
        self.name: str = config["name"]
        self.serial: str = config.get(CONF_DEVICE_SERIAL, "").strip()
        self.device_name: str = config.get(CONF_DEVICE_NAME, "").strip().lower()
        self.area_name: str = config.get(CONF_AREA_NAME, "").strip().lower()
        self.keypad_type: str = config.get(CONF_KEYPAD_TYPE, "generic")
        self.scene_group: str = config.get("scene_group", "").strip()

        # Index buttons by button_number
        self._buttons: dict[int, dict] = {}
        for btn in config.get(CONF_BUTTONS, []):
            self._buttons[btn[CONF_BUTTON_NUMBER]] = btn

        # Per-controller runtime state
        self._active_scene_btn: int | None = None   # stateful scene tracking
        self._last_action: dict | None = None        # last non-raise/lower action
        self._cover_states: dict[int, str] = {}     # cover cycle state per button
        self._light_dim_indices: dict[int, int] = {}# dim level index per button
        self._unsubscribe = None                     # event listener cancel handle

    # ── Registration ──────────────────────────────────────────────────────────

    @callback
    def async_register(self) -> None:
        """Subscribe to lutron_caseta_button_event events."""
        self._unsubscribe = self.hass.bus.async_listen(LUTRON_EVENT, self._handle_event)
        _LOGGER.info("Lutron Keypad Controller '%s' registered (serial=%s)", self.name, self.serial)

    @callback
    def async_unregister(self) -> None:
        """Unsubscribe from events (called on entry unload)."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
            _LOGGER.debug("Lutron Keypad Controller '%s' unregistered", self.name)

    # ── Event matching ────────────────────────────────────────────────────────

    def _matches_event(self, event_data: dict) -> bool:
        """Return True if this event belongs to our keypad."""
        # Match by serial number (most reliable)
        if self.serial:
            ev_serial = str(event_data.get("serial", "")).strip()
            if ev_serial == self.serial:
                return True

        # Fallback: match by device_name + area_name
        ev_device = str(event_data.get("device_name", "")).lower()
        ev_area   = str(event_data.get("area_name", "")).lower()

        if self.device_name and self.area_name:
            return ev_device == self.device_name and ev_area == self.area_name
        if self.device_name:
            return ev_device == self.device_name
        if self.area_name:
            return ev_area == self.area_name

        return False

    # ── Main event handler ────────────────────────────────────────────────────

    @callback
    def _handle_event(self, event: Event) -> None:
        """Called for every lutron_caseta_button_event on the bus."""
        data = event.data
        action_type = data.get("action", "press")   # "press" or "release"

        # Only act on press events (release events are ignored by default)
        if action_type == "release":
            return

        if not self._matches_event(data):
            return

        btn_num: int = int(data.get("button_number", -1))
        if btn_num < 0:
            _LOGGER.warning("'%s': got event with no button_number: %s", self.name, data)
            return

        btn_cfg = self._buttons.get(btn_num)
        if btn_cfg is None:
            _LOGGER.debug(
                "'%s': button %d pressed but not configured — ignoring", self.name, btn_num
            )
            return

        _LOGGER.info(
            "'%s': button %d (%s) pressed — action_type=%s",
            self.name,
            btn_num,
            btn_cfg.get(CONF_BUTTON_LABEL, ""),
            btn_cfg[CONF_ACTION_TYPE],
        )

        # Dispatch asynchronously so the event bus callback returns immediately
        self.hass.async_create_task(self._dispatch(btn_num, btn_cfg))

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(self, btn_num: int, btn_cfg: dict) -> None:
        action = btn_cfg[CONF_ACTION_TYPE]
        target = btn_cfg.get(CONF_ACTION_TARGET)
        params = btn_cfg.get(CONF_ACTION_PARAMS, {})

        if action == ACTION_NONE:
            return

        elif action == ACTION_HA_SCENE:
            await self._activate_scene(target)

        elif action == ACTION_STATEFUL_SCENE:
            await self._activate_stateful_scene(btn_num, btn_cfg, target)

        elif action == ACTION_AUTOMATION:
            await self._trigger_automation(target)

        elif action == ACTION_SCRIPT:
            await self._run_script(target, params)

        elif action == ACTION_ENTITY_TOGGLE:
            await self._entity_toggle(target)

        elif action == ACTION_COVER_CYCLE:
            await self._cover_cycle(btn_num, target)

        elif action == ACTION_LIGHT_CYCLE_DIM:
            levels = params.get("levels", DIM_CYCLE_LEVELS)
            await self._light_cycle_dim(btn_num, target, levels)

        elif action == ACTION_RAISE:
            await self._raise(params)

        elif action == ACTION_LOWER:
            await self._lower(params)

        else:
            _LOGGER.error("'%s': unknown action_type '%s'", self.name, action)

    # ── Action implementations ────────────────────────────────────────────────

    async def _activate_scene(self, scene_id: str) -> None:
        """Activate a plain HA scene."""
        await self.hass.services.async_call(
            "scene", "turn_on", {ATTR_ENTITY_ID: scene_id}, blocking=True
        )
        _LOGGER.debug("Scene activated: %s", scene_id)

    async def _activate_stateful_scene(
        self, btn_num: int, btn_cfg: dict, scene_id: str
    ) -> None:
        """Activate an HA scene and update stateful tracking + LEDs."""
        # 1. Activate the scene
        await self._activate_scene(scene_id)

        # 2. Update intra-keypad active scene
        prev_btn = self._active_scene_btn
        self._active_scene_btn = btn_num

        # 3. Update shared scene group if defined (per-button setting takes priority)
        group = btn_cfg.get("scene_group") or self.scene_group
        if group:
            _SCENE_GROUPS[group] = btn_num

        # 4. Update LEDs: turn off previous, turn on new
        await self._update_leds(prev_btn, btn_num)

        # 5. Record last non-raise/lower action for raise/lower context
        self._last_action = {
            "type": ACTION_STATEFUL_SCENE,
            "scene_id": scene_id,
            "button": btn_num,
        }
        _LOGGER.debug("Stateful scene '%s' activated on btn %d", scene_id, btn_num)

    async def _update_leds(self, deactivate_btn: int | None, activate_btn: int | None) -> None:
        """Toggle LED entities for a stateful scene transition."""
        if deactivate_btn is not None:
            old_btn_cfg = self._buttons.get(deactivate_btn, {})
            led = old_btn_cfg.get(CONF_LED_ENTITY)
            if led:
                await self.hass.services.async_call(
                    "switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: led}, blocking=False
                )

        if activate_btn is not None:
            new_btn_cfg = self._buttons.get(activate_btn, {})
            led = new_btn_cfg.get(CONF_LED_ENTITY)
            if led:
                await self.hass.services.async_call(
                    "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: led}, blocking=False
                )

    async def _trigger_automation(self, automation_id: str) -> None:
        """Trigger an HA automation."""
        await self.hass.services.async_call(
            "automation",
            "trigger",
            {ATTR_ENTITY_ID: automation_id, "skip_condition": True},
            blocking=True,
        )
        self._last_action = {"type": ACTION_AUTOMATION, "id": automation_id}

    async def _run_script(self, script_id: str, params: dict) -> None:
        """Run an HA script with optional variables."""
        service_data: dict[str, Any] = {ATTR_ENTITY_ID: script_id}
        if "variables" in params:
            service_data["variables"] = params["variables"]
        await self.hass.services.async_call(
            "script", "turn_on", service_data, blocking=False
        )
        self._last_action = {"type": ACTION_SCRIPT, "id": script_id}

    async def _entity_toggle(self, targets: Any) -> None:
        """Toggle one or more entities."""
        entity_ids = _normalize_targets(targets)
        for eid in entity_ids:
            domain = eid.split(".")[0]
            await self.hass.services.async_call(
                domain, SERVICE_TOGGLE, {ATTR_ENTITY_ID: eid}, blocking=True
            )
        self._last_action = {"type": ACTION_ENTITY_TOGGLE, "entities": entity_ids}

    async def _cover_cycle(self, btn_num: int, targets: Any) -> None:
        """Cycle a cover: open → stop → close → open ..."""
        entity_ids = _normalize_targets(targets)
        current = self._cover_states.get(btn_num, COVER_STATE_CLOSE)

        if current == COVER_STATE_CLOSE:
            next_state = COVER_STATE_OPEN
            service = "open_cover"
        elif current == COVER_STATE_OPEN:
            next_state = COVER_STATE_STOP
            service = "stop_cover"
        else:  # STOP
            next_state = COVER_STATE_CLOSE
            service = "close_cover"

        self._cover_states[btn_num] = next_state
        await self.hass.services.async_call(
            "cover", service, {ATTR_ENTITY_ID: entity_ids}, blocking=True
        )
        self._last_action = {
            "type": ACTION_COVER_CYCLE,
            "entities": entity_ids,
            "state": next_state,
        }
        _LOGGER.debug("Cover cycle: %s → %s on %s", current, next_state, entity_ids)

    async def _light_cycle_dim(
        self, btn_num: int, targets: Any, levels: list[int]
    ) -> None:
        """Cycle a light through dim levels, then off."""
        entity_ids = _normalize_targets(targets)
        idx = self._light_dim_indices.get(btn_num, len(levels))  # start past end = off state

        if idx >= len(levels):
            # Currently off (or past last level) → turn on at first level
            idx = 0
        else:
            idx += 1

        if idx >= len(levels):
            # Past the last level → turn off
            await self.hass.services.async_call(
                "light", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_ids}, blocking=True
            )
            self._light_dim_indices[btn_num] = len(levels)  # mark as off
            self._last_action = {
                "type": ACTION_LIGHT_CYCLE_DIM,
                "entities": entity_ids,
                "brightness": 0,
            }
            _LOGGER.debug("Light cycle: turned off %s", entity_ids)
        else:
            brightness_pct = levels[idx]
            brightness_255 = int(brightness_pct / 100 * 255)
            await self.hass.services.async_call(
                "light",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: entity_ids, "brightness": brightness_255},
                blocking=True,
            )
            self._light_dim_indices[btn_num] = idx
            self._last_action = {
                "type": ACTION_LIGHT_CYCLE_DIM,
                "entities": entity_ids,
                "brightness": brightness_pct,
            }
            _LOGGER.debug("Light cycle: %s → %d%%", entity_ids, brightness_pct)

    async def _raise(self, params: dict) -> None:
        """Raise shades or brighten lights based on last action context."""
        if self._last_action is None:
            _LOGGER.debug("'%s': RAISE pressed but no prior context", self.name)
            return

        last = self._last_action
        entities = last.get("entities", [])
        action_type = last.get("type")

        if action_type == ACTION_COVER_CYCLE or _entities_are_covers(entities):
            await self.hass.services.async_call(
                "cover", "open_cover", {ATTR_ENTITY_ID: entities}, blocking=True
            )
            # Reset cover cycle state to open
            for btn, cfg in self._buttons.items():
                if cfg.get(CONF_ACTION_TYPE) == ACTION_COVER_CYCLE and cfg.get(CONF_ACTION_TARGET):
                    tgts = _normalize_targets(cfg[CONF_ACTION_TARGET])
                    if any(t in entities for t in tgts):
                        self._cover_states[btn] = COVER_STATE_OPEN
        elif action_type in (ACTION_LIGHT_CYCLE_DIM, ACTION_STATEFUL_SCENE, ACTION_HA_SCENE):
            await self._adjust_light_brightness(entities, +RAISE_LOWER_STEP)
        else:
            _LOGGER.debug("'%s': RAISE — no applicable entities from last action", self.name)

    async def _lower(self, params: dict) -> None:
        """Lower shades or dim lights based on last action context."""
        if self._last_action is None:
            _LOGGER.debug("'%s': LOWER pressed but no prior context", self.name)
            return

        last = self._last_action
        entities = last.get("entities", [])
        action_type = last.get("type")

        if action_type == ACTION_COVER_CYCLE or _entities_are_covers(entities):
            await self.hass.services.async_call(
                "cover", "close_cover", {ATTR_ENTITY_ID: entities}, blocking=True
            )
            for btn, cfg in self._buttons.items():
                if cfg.get(CONF_ACTION_TYPE) == ACTION_COVER_CYCLE and cfg.get(CONF_ACTION_TARGET):
                    tgts = _normalize_targets(cfg[CONF_ACTION_TARGET])
                    if any(t in entities for t in tgts):
                        self._cover_states[btn] = COVER_STATE_CLOSE
        elif action_type in (ACTION_LIGHT_CYCLE_DIM, ACTION_STATEFUL_SCENE, ACTION_HA_SCENE):
            await self._adjust_light_brightness(entities, -RAISE_LOWER_STEP)
        else:
            _LOGGER.debug("'%s': LOWER — no applicable entities from last action", self.name)

    async def _adjust_light_brightness(
        self, entities: list[str], delta_pct: int
    ) -> None:
        """Adjust brightness of lights by delta_pct (positive = brighter)."""
        for eid in entities:
            state = self.hass.states.get(eid)
            if state is None:
                continue
            domain = eid.split(".")[0]
            if domain != "light":
                continue

            current_brightness = state.attributes.get("brightness", 0) or 0
            current_pct = round(current_brightness / 255 * 100)
            new_pct = max(0, min(100, current_pct + delta_pct))
            new_brightness = int(new_pct / 100 * 255)

            if new_brightness <= 0:
                await self.hass.services.async_call(
                    "light", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: eid}, blocking=True
                )
            else:
                await self.hass.services.async_call(
                    "light",
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: eid, "brightness": new_brightness},
                    blocking=True,
                )
            _LOGGER.debug(
                "Brightness adjust %s: %d%% → %d%%", eid, current_pct, new_pct
            )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_targets(targets: Any) -> list[str]:
    """Return a flat list of entity_id strings from scalar, comma-separated, or list target."""
    if targets is None:
        return []
    if isinstance(targets, str):
        if not targets:
            return []
        if "," in targets:
            return [t.strip() for t in targets.split(",") if t.strip()]
        return [targets]
    if isinstance(targets, (list, tuple)):
        return [str(t) for t in targets if t]
    return [str(targets)]


def _entities_are_covers(entities: list[str]) -> bool:
    """Return True if any entity in the list is a cover."""
    return any(e.startswith("cover.") for e in entities)
