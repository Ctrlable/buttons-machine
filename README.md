# Lutron Keypad Controller — Home Assistant Custom Component

A custom integration that takes full control of Lutron **SeeTouch**, **Hybrid SeeTouch**, **Sunnata**, **Alisee**, **Palladiom**, and **Tabletop** keypads (and Pico remotes) through the existing `lutron_caseta` integration.

## Philosophy

Leave every keypad button **completely blank** in Lutron Designer / RadioRA3 / HomeWorks QSX programming. This component intercepts the `lutron_caseta_button_event` events fired by the built-in Lutron Caséta integration and dispatches the actions entirely from Home Assistant.

Benefits:
- All logic lives in one place (HA), no split brain between Lutron and HA
- Buttons can trigger any HA entity, scene, script, or automation
- Stateful feedback: LEDs track which scene is active
- Raise/Lower buttons are context-aware (act on the last scene's entities)
- Easy to change without re-programming the Lutron processor

---

## Requirements

- Home Assistant 2023.6 or newer
- The built-in `lutron_caseta` integration set up and working
- RadioRA3, HomeWorks QSX, or RA2 Select processor (Pico works on Caseta bridge too)
- Keypad buttons left unprogrammed in Lutron software

---

## Installation

1. Copy the `lutron_keypad_controller/` folder into your `custom_components/` directory:
   ```
   /config/custom_components/lutron_keypad_controller/
   ```
2. Restart Home Assistant.
3. Add configuration to `configuration.yaml` (see below).
4. Restart Home Assistant again (or reload YAML integrations).

---

## Finding Your Keypad's Serial Number and Button Numbers

Enable debug logging temporarily:

```yaml
# configuration.yaml
logger:
  logs:
    homeassistant.components.lutron_caseta: debug
```

Then press any button on your keypad and look in the HA logs for:

```
homeassistant.components.lutron_caseta: Sending event for button press: 
{'serial': 12345678, 'type': 'SeeTouchKeypad', 'button_number': 1, 
 'device_name': 'Living Room Keypad', 'area_name': 'Living Room', 
 'action': 'press'}
```

Note the `serial` and the `button_number` for each physical button.

Alternatively, use **Developer Tools → Events → Listen → `lutron_caseta_button_event`** and press each button.

---

## Configuration Schema

```yaml
lutron_keypad_controller:
  keypads:
    - name: "Human-readable keypad name"
      device_serial: "12345678"       # from lutron_caseta_button_event
      device_name: "Living Room"      # optional: backup matching
      area_name: "Living Room"        # optional: backup matching
      keypad_type: sunnata            # see Keypad Types below
      scene_group: "downstairs"       # optional: share active-scene state across keypads
      buttons:
        - button_number: 1
          label: "Movie"
          action_type: stateful_scene
          action_target: scene.living_room_movie
          led_entity: switch.living_room_keypad_button_1_led  # optional
        - button_number: 2
          ...
```

### Keypad Types

| Value             | Keypad                              |
|-------------------|-------------------------------------|
| `seetouch`        | SeeTouch (wall-mount)               |
| `seetouch_hybrid` | Hybrid SeeTouch                     |
| `sunnata`         | Sunnata                             |
| `sunnata_hybrid`  | Hybrid Sunnata                      |
| `alisee`          | Alisee                              |
| `palladiom`       | Palladiom                           |
| `tabletop`        | Tabletop SeeTouch / RF              |
| `pico`            | Pico Remote                         |
| `generic`         | Any other / unknown                 |

---

## Action Types

### `stateful_scene`

Activates an HA scene **and** tracks which button/scene is currently "on". Other `stateful_scene` buttons on the same keypad (or scene_group) are considered inactive. Optional LED feedback.

```yaml
- button_number: 1
  label: "Movie"
  action_type: stateful_scene
  action_target: scene.living_room_movie
  led_entity: switch.living_room_keypad_button_1_led
```

> **LED entities**: The built-in `lutron_caseta` integration exposes keypad LEDs as `switch.*` entities on RA3/QSX systems. Use those entity IDs here.

---

### `ha_scene`

Activates an HA scene. No state tracking or LED feedback.

```yaml
- button_number: 3
  label: "All Off"
  action_type: ha_scene
  action_target: scene.all_off
```

---

### `automation`

Triggers an automation (bypasses conditions).

```yaml
- button_number: 4
  label: "Good Night"
  action_type: automation
  action_target: automation.good_night_routine
```

---

### `script`

Runs a script. Optionally pass variables.

```yaml
- button_number: 5
  label: "Party Mode"
  action_type: script
  action_target: script.party_mode
  action_params:
    variables:
      room: living_room
      color: blue
```

---

### `entity_toggle`

Toggles one or more entities (lights, switches, fans, etc.).

```yaml
- button_number: 6
  label: "Fan"
  action_type: entity_toggle
  action_target:
    - fan.living_room_fan
    - switch.living_room_fan_light
```

---

### `cover_cycle`

Cycles covers through: **open → stop → close → open ...**

Press once: open. Press again: stop. Press again: close. Press again: open.

```yaml
- button_number: 7
  label: "Shades"
  action_type: cover_cycle
  action_target:
    - cover.living_room_east_shade
    - cover.living_room_west_shade
```

---

### `light_cycle_dim`

Cycles lights through brightness levels then off:
**100% → 75% → 50% → 25% → off → 100% ...**

Customize levels with `action_params.levels`.

```yaml
- button_number: 8
  label: "Dim"
  action_type: light_cycle_dim
  action_target:
    - light.living_room_cans
  action_params:
    levels: [100, 75, 50, 25]  # optional, these are the defaults
```

---

### `raise` and `lower`

Context-aware raise/lower. The component remembers the **last action** performed by a non-raise/lower button and acts accordingly:

- If the last action involved **covers** → raises/lowers those covers
- If the last action involved **lights** → brightens/dims those lights by 10%

This mirrors how a Lutron raise/lower button works natively, but entirely in HA.

```yaml
- button_number: 9
  label: "Raise"
  action_type: raise

- button_number: 10
  label: "Lower"
  action_type: lower
```

> **Tip**: Place raise/lower as the last two buttons, as is standard on Lutron keypads.

---

## Full Example — 10-Button Sunnata Keypad

```yaml
lutron_keypad_controller:
  keypads:
    - name: "Living Room Sunnata"
      device_serial: "28786608"
      area_name: "Living Room"
      keypad_type: sunnata
      scene_group: "main_floor"
      buttons:
        - button_number: 1
          label: "Movie"
          action_type: stateful_scene
          action_target: scene.living_room_movie
          led_entity: switch.living_room_sunnata_button_1_led
        - button_number: 2
          label: "Entertain"
          action_type: stateful_scene
          action_target: scene.living_room_entertain
          led_entity: switch.living_room_sunnata_button_2_led
        - button_number: 3
          label: "Relax"
          action_type: stateful_scene
          action_target: scene.living_room_relax
          led_entity: switch.living_room_sunnata_button_3_led
        - button_number: 4
          label: "All Off"
          action_type: ha_scene
          action_target: scene.living_room_off
        - button_number: 5
          label: "Shades"
          action_type: cover_cycle
          action_target:
            - cover.living_room_east
            - cover.living_room_west
        - button_number: 6
          label: "Accent Dim"
          action_type: light_cycle_dim
          action_target:
            - light.living_room_accent
          action_params:
            levels: [100, 60, 30]
        - button_number: 7
          label: "Fan"
          action_type: entity_toggle
          action_target: fan.living_room_fan
        - button_number: 8
          label: "Good Night"
          action_type: automation
          action_target: automation.good_night
        - button_number: 9
          label: "Raise"
          action_type: raise
        - button_number: 10
          label: "Lower"
          action_type: lower
```

---

## Sensor Entities

For each configured keypad, two sensor entities are created:

| Entity | Description |
|--------|-------------|
| `sensor.<name>_status` | Active scene name or last action type |
| `sensor.<name>_last_button` | Last button number and label pressed |

---

## Scene Groups

When multiple keypads serve the same space (e.g., a room with two SeeTouch keypads), assign them the same `scene_group`. The stateful scene tracking is shared — pressing a scene button on one keypad will deactivate the LED on the other keypad.

```yaml
# Keypad A
scene_group: "master_suite"

# Keypad B (same room)  
scene_group: "master_suite"
```

---

## How Raise/Lower Context Works

The component tracks a `_last_action` dict for each keypad. When a `stateful_scene`, `ha_scene`, `entity_toggle`, `cover_cycle`, or `light_cycle_dim` button is pressed, the component records:
- The action type
- The entities that were acted upon

When `raise` or `lower` is pressed next, the component looks at this context:

```
last_action = cover_cycle  →  open/close the covers in that action
last_action = light_cycle_dim  →  brighten/dim those lights by 10%
last_action = stateful_scene  →  attempt to brighten/dim lights involved
```

If no prior context exists (fresh start), raise/lower is silently ignored.

---

## Troubleshooting

**No events firing at all:**
- Confirm the `lutron_caseta` integration is connected and keypads show up as devices in HA
- Listen for `lutron_caseta_button_event` in Developer Tools → Events
- RA3/QSX: press and hold buttons 1+2 for 3 seconds to factory reset a keypad that isn't communicating

**Wrong button numbers:**
- Button numbering varies by model. Use the event listener to find exact numbers.
- On Sunnata, the raise button is typically the last + bottom button; lower is the one above it.

**LEDs not updating:**
- LED switch entities are only available on RA3 and HomeWorks QSX, not Caseta bridge
- Find your LED entities in Settings → Devices & Services → Lutron → Entities, filter by "LED"

**Sunnata only fires press, no release:**
- This is expected for Sunnata keypads (known Lutron/pylutron-caseta behavior)
- The component ignores release events by default, so this is fine

**Scene group LEDs out of sync after restart:**
- LEDs are not restored on startup yet (planned). Press any scene button to re-sync.
