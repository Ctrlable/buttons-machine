"""Constants for the Lutron Keypad Controller integration."""

DOMAIN = "lutron_keypad_controller"

# ── Event names ──────────────────────────────────────────────────────────────
LUTRON_EVENT = "lutron_caseta_button_event"

# ── Config / storage keys ────────────────────────────────────────────────────
CONF_DEVICE_SERIAL   = "device_serial"
CONF_DEVICE_NAME     = "device_name"
CONF_AREA_NAME       = "area_name"
CONF_KEYPAD_TYPE     = "keypad_type"
CONF_BUTTONS         = "buttons"

# Per-button keys
CONF_BUTTON_NUMBER   = "button_number"
CONF_BUTTON_LABEL    = "label"
CONF_ACTION_TYPE     = "action_type"
CONF_ACTION_TARGET   = "action_target"
CONF_ACTION_PARAMS   = "action_params"
CONF_LED_ENTITY      = "led_entity"

# ── Keypad models ─────────────────────────────────────────────────────────────
KEYPAD_SEETOUCH          = "seetouch"
KEYPAD_SEETOUCH_HYBRID   = "seetouch_hybrid"
KEYPAD_SUNNATA           = "sunnata"
KEYPAD_SUNNATA_HYBRID    = "sunnata_hybrid"
KEYPAD_ALISEE            = "alisee"
KEYPAD_PALLADIOM         = "palladiom"
KEYPAD_TABLETOP          = "tabletop"
KEYPAD_PICO              = "pico"
KEYPAD_GENERIC           = "generic"

KEYPAD_TYPES = [
    KEYPAD_SEETOUCH,
    KEYPAD_SEETOUCH_HYBRID,
    KEYPAD_SUNNATA,
    KEYPAD_SUNNATA_HYBRID,
    KEYPAD_ALISEE,
    KEYPAD_PALLADIOM,
    KEYPAD_TABLETOP,
    KEYPAD_PICO,
    KEYPAD_GENERIC,
]

RAISE_LOWER_BUTTON_TYPES = {
    "raise": [3, 5, 7, 17, 18],
    "lower": [4, 6, 8, 19, 20],
}

# ── Action types ──────────────────────────────────────────────────────────────
ACTION_STATEFUL_SCENE  = "stateful_scene"
ACTION_HA_SCENE        = "ha_scene"
ACTION_AUTOMATION      = "automation"
ACTION_SCRIPT          = "script"
ACTION_ENTITY_TOGGLE   = "entity_toggle"
ACTION_COVER_CYCLE     = "cover_cycle"
ACTION_LIGHT_CYCLE_DIM = "light_cycle_dim"
ACTION_RAISE           = "raise"
ACTION_LOWER           = "lower"
ACTION_NONE            = "none"

ACTION_TYPES = [
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

# ── Stateful scene tracking ───────────────────────────────────────────────────
ATTR_ACTIVE_SCENE    = "active_scene"
ATTR_LAST_ACTION     = "last_action"
ATTR_COVER_STATES    = "cover_states"
ATTR_LIGHT_DIM_STEPS = "light_dim_steps"

DIM_CYCLE_LEVELS = [100, 75, 50, 25]

COVER_STATE_OPEN  = "open"
COVER_STATE_STOP  = "stop"
COVER_STATE_CLOSE = "close"

RAISE_LOWER_STEP = 10

SENSOR_SUFFIX_STATUS     = "status"
SENSOR_SUFFIX_LAST_BTN   = "last_button"
