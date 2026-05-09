// ================================================================
// Lutron Keypad Programming Panel
// A custom HA panel element inspired by the Lutron Designer UI.
// ================================================================

const DOMAIN = "lutron_keypad_controller";

// ── Keypad layout geometry ────────────────────────────────────────
const KEYPAD_LAYOUTS = {
  seetouch:        { mainCount: 6, hasRL: true,  cols: 2 },
  seetouch_hybrid: { mainCount: 5, hasRL: true,  cols: 2 },
  sunnata:         { mainCount: 4, hasRL: true,  cols: 1 },
  sunnata_hybrid:  { mainCount: 3, hasRL: true,  cols: 1 },
  alisee:          { mainCount: 5, hasRL: true,  cols: 1 },
  palladiom:       { mainCount: 5, hasRL: true,  cols: 1 },
  tabletop:        { mainCount: 10, hasRL: false, cols: 2 },
  pico:            { mainCount: 3,  hasRL: false, cols: 1 },
  generic:         { mainCount: 6,  hasRL: true,  cols: 2 },
};

// ── Action types ──────────────────────────────────────────────────
const ACTION_TYPES = {
  none:            { label: "None",           domains: [],       multi: false },
  stateful_scene:  { label: "Stateful Scene", domains: ["scene"],       multi: false },
  ha_scene:        { label: "HA Scene",       domains: ["scene"],       multi: false },
  automation:      { label: "Automation",     domains: ["automation"],  multi: false },
  script:          { label: "Script",         domains: ["script"],      multi: false },
  entity_toggle:   { label: "Entity Toggle",  domains: ["light","switch","fan","input_boolean","media_player","cover"], multi: true },
  cover_cycle:     { label: "Cover Cycle",    domains: ["cover"],       multi: true },
  light_cycle_dim: { label: "Dim Cycle",      domains: ["light"],       multi: true },
  raise:           { label: "Raise",          domains: [],              multi: false },
  lower:           { label: "Lower",          domains: [],              multi: false },
};

// ── LED Logic options ─────────────────────────────────────────────
const LED_LOGIC = {
  room:  "Room",
  scene: "Scene",
  none:  "No Integration",
};

// ── Entity-domain display labels ──────────────────────────────────
const DOMAIN_LABELS = {
  scene: "Scenes", light: "Lighting", switch: "Switches",
  cover: "Covers", automation: "Automations", script: "Scripts",
  fan: "Fans", media_player: "Media Players", input_boolean: "Input Booleans",
};

// ── CSS ───────────────────────────────────────────────────────────
const STYLES = `
  :host {
    display: flex;
    flex-direction: column;
    height: 100%;
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    font-size: 14px;
    color: var(--primary-text-color, #212121);
    background: var(--secondary-background-color, #f0f2f5);
    overflow: hidden;
  }

  /* ── Top nav bar (Lutron Designer style) ── */
  .panel-header {
    display: flex;
    align-items: center;
    background: #1a3d2b;
    color: #fff;
    padding: 0 16px;
    height: 56px;
    flex-shrink: 0;
    gap: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    z-index: 10;
  }
  .panel-header .logo {
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.5px;
    color: #81c784;
  }
  .panel-header .subtitle {
    font-size: 12px;
    color: #a5d6a7;
    flex: 1;
    padding-left: 8px;
  }
  .btn-save {
    background: #2e7d32;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }
  .btn-save:hover { background: #388e3c; }
  .btn-save:disabled { background: #555; cursor: default; }
  .save-status {
    font-size: 12px;
    color: #a5d6a7;
    min-width: 120px;
    text-align: right;
  }

  /* ── Body layout ── */
  .panel-body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* ── Resize handles ── */
  .resize-handle-v {
    width: 5px;
    cursor: ew-resize;
    background: var(--divider-color, #e0e0e0);
    flex-shrink: 0;
    transition: background 0.15s;
    user-select: none;
  }
  .resize-handle-v:hover, .resize-handle-v.dragging { background: #4caf50; }

  .resize-handle-h {
    height: 5px;
    cursor: ns-resize;
    background: var(--divider-color, #e0e0e0);
    flex-shrink: 0;
    transition: background 0.15s;
    user-select: none;
  }
  .resize-handle-h:hover, .resize-handle-h.dragging { background: #4caf50; }

  /* ── Left sidebar: keypad list ── */
  .sidebar {
    width: 220px;
    min-width: 140px;
    background: #1e2a22;
    color: #c8e6c9;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex-shrink: 0;
  }
  .sidebar-header {
    padding: 12px 14px 8px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #81c784;
    border-bottom: 1px solid #2d4a35;
  }
  .sidebar-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
  }
  .sidebar-area {
    padding: 6px 14px 2px;
    font-size: 10px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #4caf50;
    font-weight: 600;
    margin-top: 4px;
  }
  .sidebar-entry {
    display: flex;
    flex-direction: column;
    padding: 8px 14px 8px 20px;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: background 0.15s;
    gap: 2px;
  }
  .sidebar-entry:hover { background: rgba(255,255,255,0.06); }
  .sidebar-entry.active {
    background: rgba(76,175,80,0.18);
    border-left-color: #4caf50;
  }
  .sidebar-entry .entry-name { font-size: 13px; color: #e8f5e9; font-weight: 500; }
  .sidebar-entry .entry-type {
    font-size: 10px; color: #81c784;
    background: rgba(76,175,80,0.2);
    border-radius: 3px;
    padding: 1px 5px;
    display: inline-block;
    width: fit-content;
  }

  /* ── Main programming area ── */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .welcome {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color, #757575);
    gap: 12px;
  }
  .welcome .welcome-icon { font-size: 64px; opacity: 0.3; }
  .welcome h2 { font-size: 22px; font-weight: 300; margin: 0; }
  .welcome p { font-size: 14px; margin: 0; }

  /* ── Breadcrumb ── */
  .breadcrumb {
    background: rgba(76,175,80,0.07);
    border-bottom: 1px solid rgba(76,175,80,0.2);
    padding: 6px 16px;
    font-size: 12px;
    color: #4caf50;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .breadcrumb span { color: #66bb6a; }

  /* ── Programming layout ── */
  .prog-body {
    display: flex;
    flex: 1;
    overflow: hidden;
    gap: 0;
  }

  /* ── Left column: keypad visual ── */
  .col-keypad {
    width: 186px;
    min-width: 120px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px;
    background: var(--card-background-color, #fff);
    overflow-y: auto;
    gap: 10px;
  }
  .kp-nav {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--secondary-text-color, #757575);
  }
  .kp-nav button {
    background: none;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    padding: 2px 8px;
    cursor: pointer;
    font-size: 14px;
    color: var(--primary-text-color, #212121);
    transition: background 0.15s;
  }
  .kp-nav button:hover { background: rgba(76,175,80,0.1); border-color: #a5d6a7; }
  .kp-nav button:disabled { opacity: 0.3; cursor: default; }
  .kp-nav .btn-num {
    font-weight: 600;
    min-width: 48px;
    text-align: center;
    color: var(--primary-text-color);
  }

  /* ── Keypad visual (device drawing) ── */
  .keypad-device {
    background: #242424;
    border-radius: 10px;
    padding: 10px 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    width: 140px;
    position: relative;
  }
  .keypad-device .kp-logo {
    font-size: 8px;
    color: #555;
    letter-spacing: 1px;
    text-transform: uppercase;
    align-self: flex-start;
    padding-left: 2px;
    margin-bottom: 2px;
  }
  .kp-main-buttons {
    display: grid;
    gap: 5px;
    width: 100%;
  }
  .kp-btn {
    background: #3a3a3a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 6px 4px;
    min-height: 32px;
    font-size: 9px;
    color: #bdbdbd;
    line-height: 1.2;
    box-shadow: inset 0 -2px 0 rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.04);
    word-break: break-word;
    overflow: hidden;
  }
  .kp-btn:hover { background: #4a4a4a; color: #e0e0e0; }
  .kp-btn.selected {
    background: #2e7d32;
    color: #fff;
    border-color: #1b5e20;
    box-shadow: inset 0 -2px 0 rgba(0,0,0,0.3), 0 0 0 2px rgba(76,175,80,0.4);
  }
  .kp-btn.configured::after {
    content: "•";
    color: #81c784;
    position: absolute;
    top: 2px;
    right: 3px;
    font-size: 8px;
  }
  .kp-btn.raise-lower {
    background: #2a2a2a;
    font-size: 12px;
    color: #666;
    min-height: 22px;
    padding: 2px;
  }
  .kp-btn.raise-lower:hover { color: #aaa; background: #333; }
  .kp-btn.raise-lower.selected { background: #1b5e20; color: #81c784; }
  .kp-rl-row {
    display: flex;
    gap: 4px;
    width: 100%;
    margin-top: 2px;
  }
  .kp-rl-row .kp-btn { flex: 1; }

  /* ── Button engraving fields ── */
  .engraving-section {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .engraving-section label {
    font-size: 10px;
    color: var(--secondary-text-color, #757575);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .engraving-section input {
    width: 100%;
    padding: 5px 7px;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    font-size: 12px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
    box-sizing: border-box;
  }
  .engraving-section input:focus {
    outline: none;
    border-color: #4caf50;
    box-shadow: 0 0 0 2px rgba(76,175,80,0.15);
  }

  /* ── Right column: config + tree ── */
  .col-right {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Button configuration strip ── */
  .btn-config-strip {
    background: var(--card-background-color, #fff);
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    padding: 10px 16px;
    flex-shrink: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
  }
  .config-field {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .config-field label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--secondary-text-color, #757575);
  }
  .config-field select, .config-field input[type="number"] {
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 13px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
    cursor: pointer;
    min-width: 120px;
  }
  .config-field select:focus, .config-field input:focus {
    outline: none;
    border-color: #4caf50;
    box-shadow: 0 0 0 2px rgba(76,175,80,0.15);
  }
  .checkbox-field {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-top: 14px;
    font-size: 13px;
    cursor: pointer;
  }
  .checkbox-field input[type="checkbox"] { accent-color: #2e7d32; width: 15px; height: 15px; }

  /* ── Extra config fields (brightness, cct, scene group) ── */
  .extra-config {
    background: var(--secondary-background-color, #f5f5f5);
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    padding: 8px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    align-items: center;
    flex-shrink: 0;
  }
  .extra-config.hidden { display: none; }

  /* ── Entity tree ── */
  .tree-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--secondary-background-color, #f5f5f5);
  }
  .tree-filter-bar {
    background: var(--card-background-color, #fff);
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    padding: 8px 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    font-size: 12px;
  }
  .tree-filter-bar label { color: var(--secondary-text-color, #757575); font-weight: 500; }
  .tree-filter-bar select {
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
    cursor: pointer;
  }
  .tree-filter-bar select:focus { outline: none; border-color: #4caf50; }
  .tree-filter-bar .expand-all {
    margin-left: auto;
    background: none;
    border: none;
    color: #4caf50;
    cursor: pointer;
    font-size: 12px;
    text-decoration: underline;
  }
  .tree-container {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
  }
  .tree-empty {
    padding: 32px 16px;
    text-align: center;
    color: var(--secondary-text-color, #757575);
    font-size: 13px;
  }
  .area-node { border-bottom: 1px solid var(--divider-color, #ebebeb); }
  .area-header {
    display: flex;
    align-items: center;
    padding: 7px 16px;
    cursor: pointer;
    background: var(--card-background-color, #fff);
    user-select: none;
    transition: background 0.12s;
    gap: 8px;
  }
  .area-header:hover { background: rgba(76,175,80,0.06); }
  .area-expand { font-size: 10px; color: var(--secondary-text-color, #aaa); width: 14px; }
  .area-check { accent-color: #2e7d32; width: 14px; height: 14px; cursor: pointer; }
  .area-name { font-weight: 600; font-size: 13px; flex: 1; }
  .area-count { font-size: 11px; color: var(--secondary-text-color, #757575); }
  .area-entities { display: none; background: var(--secondary-background-color, #fafafa); }
  .area-entities.open { display: block; }
  .entity-row {
    display: flex;
    align-items: center;
    padding: 5px 16px 5px 38px;
    gap: 8px;
    cursor: pointer;
    transition: background 0.1s;
    border-top: 1px solid var(--divider-color, #f0f0f0);
  }
  .entity-row:hover { background: rgba(76,175,80,0.06); }
  .entity-row.selected { background: rgba(76,175,80,0.12); }
  .entity-check { accent-color: #2e7d32; width: 14px; height: 14px; cursor: pointer; flex-shrink: 0; }
  .entity-icon { font-size: 14px; width: 20px; text-align: center; flex-shrink: 0; }
  .entity-name { flex: 1; font-size: 13px; }
  .entity-state {
    font-size: 11px;
    color: var(--secondary-text-color, #757575);
    text-align: right;
    min-width: 50px;
  }
  .entity-state.on { color: #4caf50; font-weight: 500; }

  /* ── Programming summary table (bottom) ── */
  .summary-section {
    background: var(--card-background-color, #fff);
    flex-shrink: 0;
    min-height: 60px;
    overflow-y: auto;
  }
  .summary-header {
    padding: 6px 16px;
    background: var(--secondary-background-color, #f5f5f5);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    color: var(--secondary-text-color, #757575);
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  .summary-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  .summary-table th {
    text-align: left;
    padding: 5px 12px;
    background: var(--secondary-background-color, #f5f5f5);
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    font-weight: 500;
    color: var(--secondary-text-color, #757575);
    font-size: 11px;
    position: sticky;
    top: 37px;
  }
  .summary-table td {
    padding: 5px 12px;
    border-bottom: 1px solid var(--divider-color, #f0f0f0);
  }
  .summary-table tr:hover td { background: rgba(76,175,80,0.06); }
  .summary-empty {
    padding: 12px 16px;
    font-size: 12px;
    color: var(--secondary-text-color, #bbb);
    font-style: italic;
  }
  .type-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    background: rgba(76,175,80,0.15);
    color: #4caf50;
    font-weight: 500;
  }
  .remove-entity {
    background: none;
    border: none;
    color: #ef5350;
    cursor: pointer;
    font-size: 14px;
    padding: 0 4px;
    opacity: 0.6;
  }
  .remove-entity:hover { opacity: 1; }
`;

// ── Helpers ───────────────────────────────────────────────────────

function entityIcon(entityId, state) {
  const domain = entityId.split(".")[0];
  const isOn = state && !["off","closed","unavailable","unknown"].includes(state);
  const icons = {
    light: isOn ? "💡" : "🔦",
    switch: isOn ? "🔵" : "⚪",
    scene: "🎬",
    automation: "⚙️",
    script: "📜",
    cover: state === "open" ? "🪟" : "🔲",
    fan: isOn ? "🌀" : "💨",
    media_player: "📺",
    input_boolean: isOn ? "✅" : "⭕",
  };
  return icons[domain] || "▪️";
}

function entityStateLabel(entityId, state, attributes) {
  if (!state) return "";
  const domain = entityId.split(".")[0];
  if (domain === "light" && state === "on") {
    const bri = attributes?.brightness;
    if (bri != null) return Math.round(bri / 255 * 100) + "%";
    return "On";
  }
  if (domain === "cover") return state.charAt(0).toUpperCase() + state.slice(1);
  if (state === "unavailable") return "N/A";
  return state.charAt(0).toUpperCase() + state.slice(1);
}

function friendlyName(hass, entityId, entityEntry) {
  if (entityEntry?.name) return entityEntry.name;
  const state = hass.states?.[entityId];
  if (state?.attributes?.friendly_name) return state.attributes.friendly_name;
  return entityId.split(".")[1].replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function resolveAreaId(entityId, hass) {
  const ent = hass.entities?.[entityId];
  if (!ent) return null;
  if (ent.area_id) return ent.area_id;
  if (ent.device_id) {
    const dev = hass.devices?.[ent.device_id];
    if (dev?.area_id) return dev.area_id;
  }
  return null;
}

function areaName(hass, areaId) {
  if (!areaId) return "No Area";
  return hass.areas?.[areaId]?.name || areaId;
}

function getLayout(keypadType) {
  return KEYPAD_LAYOUTS[keypadType] || KEYPAD_LAYOUTS.generic;
}

function getButtonsFromEntry(entryData) {
  // Build button list from entry data (mirrors Python get_button_layout)
  const btnNums = entryData.button_numbers;
  if (btnNums && btnNums.length > 0) {
    const raise = entryData.raise_button;
    const lower = entryData.lower_button;
    return btnNums.map(n => ({
      number: n,
      is_raise: n === raise,
      is_lower: n === lower,
    }));
  }
  const kt = entryData.keypad_type || "generic";
  const layout = getLayout(kt);
  const buttons = [];
  for (let i = 1; i <= layout.mainCount; i++) {
    buttons.push({ number: i, is_raise: false, is_lower: false });
  }
  if (layout.hasRL) {
    buttons.push({ number: layout.mainCount + 1, is_raise: true, is_lower: false });
    buttons.push({ number: layout.mainCount + 2, is_raise: false, is_lower: true });
  }
  return buttons;
}

function defaultBtnCfg() {
  return {
    label: "",
    action_type: "none",
    action_target: "",
    led_entity: "",
    led_invert: false,
    led_mode: "room",
    target_brightness: 0,
    target_color_temp: 0,
    scene_group: "",
    cycle_dim: false,
    enabled: true,
  };
}

// ── Panel web component ───────────────────────────────────────────

class LutronKeypadsPanel extends HTMLElement {

  constructor() {
    super();
    this._hass = null;
    this._entries = [];
    this._selectedEntryId = null;
    this._selectedButton = 1;
    this._pendingConfig = {};   // entryId → { btnNum: cfg }
    this._dirty = {};           // entryId → bool
    this._expandedAreas = new Set();
    this._filterArea = "";
    this._initialized = false;
    this._saveStatus = "";
    this._shadow = this.attachShadow({ mode: "open" });

    // Resizable panel sizes (px)
    this._sidebarWidth = 220;
    this._keypayWidth = 186;
    this._summaryHeight = 180;
    this._sidebarResizerBound = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this._setup();
    }
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (this._hass && !this._initialized) {
      this._initialized = true;
      this._setup();
    }
  }

  async _setup() {
    this._injectStyles();
    this._buildSkeleton();
    await this._loadEntries();

    // Pre-select entry from URL query param
    const params = new URLSearchParams(window.location.search);
    const paramEntry = params.get("entry");
    if (paramEntry && this._entries.find(e => e.entry_id === paramEntry)) {
      this._selectEntry(paramEntry);
    } else if (this._entries.length === 1) {
      this._selectEntry(this._entries[0].entry_id);
    }

    this._renderSidebar();
    this._renderMain();
  }

  _injectStyles() {
    const style = document.createElement("style");
    style.textContent = STYLES;
    this._shadow.appendChild(style);
  }

  _buildSkeleton() {
    const root = document.createElement("div");
    root.className = "panel-body";
    root.innerHTML = `
      <div class="sidebar" id="sidebar" style="width:${this._sidebarWidth}px">
        <div class="sidebar-header">Lutron Keypads</div>
        <div class="sidebar-list" id="sidebar-list"></div>
      </div>
      <div class="resize-handle-v" id="sidebar-resizer"></div>
      <div class="main" id="main-content">
        <div class="welcome">
          <div class="welcome-icon">⌨️</div>
          <h2>Lutron Keypad Programming</h2>
          <p>Select a keypad from the left to begin programming</p>
        </div>
      </div>
    `;

    const header = document.createElement("div");
    header.className = "panel-header";
    header.innerHTML = `
      <span class="logo">Lutron</span>
      <span class="subtitle" id="header-subtitle">Keypad Programming</span>
      <span class="save-status" id="save-status"></span>
      <button class="btn-save" id="btn-save" disabled>Save Changes</button>
    `;

    this._shadow.appendChild(header);
    this._shadow.appendChild(root);

    this._shadow.getElementById("btn-save").addEventListener("click", () => this._saveConfig());
    this._initResizers();
  }

  async _loadEntries() {
    try {
      this._entries = await this._hass.callWS({
        type: "lutron_keypad_controller/get_entries",
      });
    } catch (e) {
      console.error("LutronPanel: failed to load entries", e);
      this._entries = [];
    }
  }

  // ── Sidebar ────────────────────────────────────────────────────

  _renderSidebar() {
    const list = this._shadow.getElementById("sidebar-list");
    if (!list) return;

    if (this._entries.length === 0) {
      list.innerHTML = `<div style="padding:14px;color:#81c784;font-size:12px;">No keypads configured.<br>Add one via Settings → Integrations.</div>`;
      return;
    }

    // Group entries by area
    const byArea = {};
    for (const entry of this._entries) {
      const area = entry.data?.area_name || "";
      if (!byArea[area]) byArea[area] = [];
      byArea[area].push(entry);
    }

    let html = "";
    for (const [area, entries] of Object.entries(byArea)) {
      if (area) html += `<div class="sidebar-area">${area}</div>`;
      for (const entry of entries) {
        const active = entry.entry_id === this._selectedEntryId ? "active" : "";
        const ktype = (entry.data?.keypad_type || "generic").replace(/_/g, " ");
        html += `
          <div class="sidebar-entry ${active}" data-entry="${entry.entry_id}">
            <span class="entry-name">${entry.title}</span>
            <span class="entry-type">${ktype}</span>
          </div>`;
      }
    }
    list.innerHTML = html;

    list.querySelectorAll(".sidebar-entry").forEach(el => {
      el.addEventListener("click", () => {
        this._selectEntry(el.dataset.entry);
        this._renderSidebar();
        this._renderMain();
      });
    });
  }

  _selectEntry(entryId) {
    this._selectedEntryId = entryId;
    const entry = this._getEntry(entryId);
    if (!entry) return;

    if (!this._pendingConfig[entryId]) {
      this._loadPendingFromEntry(entryId, entry);
    }

    const buttons = getButtonsFromEntry(entry.data);
    const firstConfigurable = buttons.find(b => !b.is_raise && !b.is_lower);
    this._selectedButton = firstConfigurable?.number || buttons[0]?.number || 1;

    const subtitle = this._shadow.getElementById("header-subtitle");
    if (subtitle) {
      subtitle.textContent = `${entry.data?.area_name ? entry.data.area_name + " › " : ""}${entry.title}`;
    }
  }

  _loadPendingFromEntry(entryId, entry) {
    const savedButtons = entry.options?.buttons || {};
    const all = getButtonsFromEntry(entry.data);
    const pending = {};
    const names = entry.data?.button_names || {};
    for (const btn of all) {
      const saved = savedButtons[String(btn.number)] || {};
      pending[btn.number] = {
        ...defaultBtnCfg(),
        ...saved,
        label: saved.label || names[String(btn.number)] || "",
      };
      if (btn.is_raise)  { pending[btn.number].action_type = "raise";  pending[btn.number].label = pending[btn.number].label || "Raise"; }
      if (btn.is_lower)  { pending[btn.number].action_type = "lower";  pending[btn.number].label = pending[btn.number].label || "Lower"; }
    }
    this._pendingConfig[entryId] = pending;
  }

  // ── Main programming area ──────────────────────────────────────

  _renderMain() {
    const main = this._shadow.getElementById("main-content");
    if (!main) return;
    if (!this._selectedEntryId) {
      main.innerHTML = `
        <div class="welcome">
          <div class="welcome-icon">⌨️</div>
          <h2>Lutron Keypad Programming</h2>
          <p>Select a keypad from the left to begin programming</p>
        </div>`;
      return;
    }

    const entry = this._getEntry(this._selectedEntryId);
    if (!entry) return;

    const buttons = getButtonsFromEntry(entry.data);
    const btn = buttons.find(b => b.number === this._selectedButton);
    const isRL = btn?.is_raise || btn?.is_lower;
    const pending = this._pendingConfig[this._selectedEntryId] || {};
    const btnCfg = pending[this._selectedButton] || defaultBtnCfg();

    main.innerHTML = `
      <div class="breadcrumb">
        ${entry.data?.area_name ? `<span>${entry.data.area_name}</span> ›` : ""}
        <span>${entry.title}</span>
      </div>
      <div class="prog-body" id="prog-body">
        ${this._renderKeypadColumn(entry, buttons, btnCfg)}
        <div class="resize-handle-v" id="keypad-resizer"></div>
        <div class="col-right" id="col-right">
          ${this._renderConfigStrip(entry, btnCfg, isRL)}
          ${this._renderExtraConfig(btnCfg, isRL)}
          ${this._renderTreeSection(entry, btnCfg, isRL)}
        </div>
      </div>
      <div class="resize-handle-h" id="summary-resizer"></div>
      ${this._renderSummarySection(entry, btnCfg)}
    `;

    this._attachMainListeners(entry, buttons, btnCfg);
  }

  // ── Keypad visual column ───────────────────────────────────────

  _renderKeypadColumn(entry, buttons, btnCfg) {
    const ktype = entry.data?.keypad_type || "generic";
    const layout = getLayout(ktype);
    const pending = this._pendingConfig[this._selectedEntryId] || {};
    const names = entry.data?.button_names || {};

    const mainButtons = buttons.filter(b => !b.is_raise && !b.is_lower);
    const raiseBtn = buttons.find(b => b.is_raise);
    const lowerBtn = buttons.find(b => b.is_lower);

    const colsStyle = `grid-template-columns: repeat(${layout.cols}, 1fr)`;

    let btnHtml = mainButtons.map(b => {
      const cfg = pending[b.number] || {};
      const label = cfg.label || names[String(b.number)] || `Btn ${b.number}`;
      const sel = b.number === this._selectedButton ? "selected" : "";
      const conf = cfg.action_type && cfg.action_type !== "none" ? "configured" : "";
      return `<div class="kp-btn ${sel} ${conf}" data-kp-btn="${b.number}" style="position:relative">${this._esc(label)}</div>`;
    }).join("");

    let rlHtml = "";
    if (raiseBtn || lowerBtn) {
      rlHtml = `<div class="kp-rl-row">`;
      if (raiseBtn) {
        const sel = raiseBtn.number === this._selectedButton ? "selected" : "";
        rlHtml += `<div class="kp-btn raise-lower ${sel}" data-kp-btn="${raiseBtn.number}" title="Raise">▲</div>`;
      }
      if (lowerBtn) {
        const sel = lowerBtn.number === this._selectedButton ? "selected" : "";
        rlHtml += `<div class="kp-btn raise-lower ${sel}" data-kp-btn="${lowerBtn.number}" title="Lower">▼</div>`;
      }
      rlHtml += `</div>`;
    }

    // Prev/Next navigation
    const allNums = buttons.map(b => b.number);
    const curIdx = allNums.indexOf(this._selectedButton);
    const prevDisabled = curIdx <= 0 ? "disabled" : "";
    const nextDisabled = curIdx >= allNums.length - 1 ? "disabled" : "";
    const prevNum = curIdx > 0 ? allNums[curIdx - 1] : null;
    const nextNum = curIdx < allNums.length - 1 ? allNums[curIdx + 1] : null;

    const label1 = (this._pendingConfig[this._selectedEntryId] || {})[this._selectedButton]?.label || "";

    return `
      <div class="col-keypad" style="width:${this._keypayWidth}px">
        <div class="kp-nav">
          <button id="btn-prev" ${prevDisabled} data-prev="${prevNum}">◀</button>
          <span class="btn-num">Button ${this._selectedButton}</span>
          <button id="btn-next" ${nextDisabled} data-next="${nextNum}">▶</button>
        </div>
        <div class="keypad-device">
          <div class="kp-logo">LUTRON</div>
          <div class="kp-main-buttons" style="${colsStyle}">
            ${btnHtml}
          </div>
          ${rlHtml}
        </div>
        <div class="engraving-section">
          <label>Button Label (Engraving)</label>
          <input id="inp-label" type="text" placeholder="Line 1" maxlength="20"
                 value="${this._esc(label1)}">
        </div>
      </div>`;
  }

  // ── Config strip ───────────────────────────────────────────────

  _renderConfigStrip(entry, btnCfg, isRL) {
    const at = btnCfg.action_type || "none";
    const ledMode = btnCfg.led_mode || "room";
    const cycleDim = btnCfg.cycle_dim ? "checked" : "";

    const atOptions = Object.entries(ACTION_TYPES).map(([val, info]) =>
      `<option value="${val}" ${val === at ? "selected" : ""}>${info.label}</option>`
    ).join("");

    const ledOptions = Object.entries(LED_LOGIC).map(([val, label]) =>
      `<option value="${val}" ${val === ledMode ? "selected" : ""}>${label}</option>`
    ).join("");

    const ledDisabled = isRL ? "disabled" : "";
    const atDisabled = isRL ? "disabled" : "";

    return `
      <div class="btn-config-strip">
        <div class="config-field">
          <label>Action Type</label>
          <select id="sel-action-type" ${atDisabled}>${atOptions}</select>
        </div>
        <div class="config-field">
          <label>LED Logic</label>
          <select id="sel-led-logic" ${ledDisabled}>${ledOptions}</select>
        </div>
        <label class="checkbox-field">
          <input id="chk-cycle-dim" type="checkbox" ${cycleDim} ${isRL ? "disabled" : ""}>
          Cycle Dim
        </label>
        <label class="checkbox-field">
          <input id="chk-led-invert" type="checkbox" ${btnCfg.led_invert ? "checked" : ""} ${isRL ? "disabled" : ""}>
          Invert LED
        </label>
      </div>`;
  }

  // ── Extra config (brightness, CCT, scene group) ────────────────

  _renderExtraConfig(btnCfg, isRL) {
    const at = btnCfg.action_type || "none";
    const showBri = !isRL && at === "entity_toggle";
    const showSg  = !isRL && at === "stateful_scene";
    const showLed = !isRL && at === "stateful_scene";

    if (isRL || (!showBri && !showSg && !showLed)) {
      return `<div class="extra-config hidden"></div>`;
    }

    let inner = "";
    if (showBri) {
      inner += `
        <div class="config-field">
          <label>Target Brightness %</label>
          <input id="inp-brightness" type="number" min="0" max="100" value="${btnCfg.target_brightness || 0}" style="min-width:80px">
        </div>
        <div class="config-field">
          <label>Target Color Temp K</label>
          <input id="inp-cct" type="number" min="0" max="10000" step="100" value="${btnCfg.target_color_temp || 0}" style="min-width:90px">
        </div>`;
    }
    if (showSg) {
      inner += `
        <div class="config-field">
          <label>Scene Group</label>
          <input id="inp-scene-group" type="text" value="${this._esc(btnCfg.scene_group || "")}" placeholder="e.g. living_room" style="min-width:120px">
        </div>`;
    }
    if (showLed) {
      inner += `
        <div class="config-field">
          <label>LED Switch Override</label>
          <input id="inp-led-entity" type="text" value="${this._esc(btnCfg.led_entity || "")}" placeholder="switch.keypad_led_1" style="min-width:160px">
        </div>`;
    }

    return `<div class="extra-config">${inner}</div>`;
  }

  // ── Entity tree ────────────────────────────────────────────────

  _renderTreeSection(entry, btnCfg, isRL) {
    const at = btnCfg.action_type || "none";
    const info = ACTION_TYPES[at];
    const domains = info?.domains || [];

    if (isRL || domains.length === 0) {
      const msg = isRL
        ? "Raise/Lower buttons use the last active button's context — no direct assignment needed."
        : at === "none"
          ? "Select an Action Type above to assign entities."
          : "This action type requires no entity assignment.";
      return `
        <div class="tree-section">
          <div class="tree-empty">${msg}</div>
        </div>`;
    }

    const entities = this._getEntitiesForAction(at);
    const byArea = this._groupByArea(entities);
    const areaKeys = Object.keys(byArea).sort((a, b) => {
      if (a === "_none") return 1;
      if (b === "_none") return -1;
      return areaName(this._hass, a).localeCompare(areaName(this._hass, b));
    });

    const isMulti = info?.multi || false;
    const selectedTargets = this._getSelectedTargets(btnCfg);

    // Area filter options
    const areaOpts = areaKeys
      .filter(k => k !== "_none")
      .map(k => `<option value="${k}" ${k === this._filterArea ? "selected" : ""}>${areaName(this._hass, k)}</option>`)
      .join("");

    let treeHtml = "";
    for (const areaId of areaKeys) {
      if (this._filterArea && areaId !== this._filterArea && areaId !== "_none") continue;

      const areaEntities = byArea[areaId];
      const expanded = this._expandedAreas.has(areaId);
      const selCount = areaEntities.filter(e => selectedTargets.includes(e.entity_id)).length;
      const allSel = selCount === areaEntities.length && areaEntities.length > 0;
      const someSel = selCount > 0 && !allSel;
      const label = areaId === "_none" ? "No Area" : areaName(this._hass, areaId);

      treeHtml += `
        <div class="area-node">
          <div class="area-header" data-area-toggle="${areaId}">
            <span class="area-expand">${expanded ? "▼" : "▶"}</span>
            <input type="checkbox" class="area-check" data-area-check="${areaId}"
                   ${allSel ? "checked" : ""} ${someSel ? "data-indeterminate" : ""}>
            <span class="area-name">${this._esc(label)}</span>
            <span class="area-count">${selCount > 0 ? selCount + " of " : ""}${areaEntities.length} ${selCount > 0 ? "Active" : "Zones"}</span>
          </div>
          <div class="area-entities ${expanded ? "open" : ""}" id="area-ents-${areaId}">
            ${areaEntities.map(ent => this._renderEntityRow(ent, selectedTargets, isMulti)).join("")}
          </div>
        </div>`;
    }

    if (!treeHtml) {
      treeHtml = `<div class="tree-empty">No entities found for this action type.</div>`;
    }

    return `
      <div class="tree-section">
        <div class="tree-filter-bar">
          <label>Show in:</label>
          <select id="sel-filter-area">
            <option value="">All Areas</option>
            ${areaOpts}
          </select>
          <button class="expand-all" id="btn-expand-all">Expand All</button>
        </div>
        <div class="tree-container">
          ${treeHtml}
        </div>
      </div>`;
  }

  _renderEntityRow(ent, selectedTargets, isMulti) {
    const sel = selectedTargets.includes(ent.entity_id);
    const stateVal = this._hass.states?.[ent.entity_id]?.state;
    const attrs = this._hass.states?.[ent.entity_id]?.attributes || {};
    const stateLabel = entityStateLabel(ent.entity_id, stateVal, attrs);
    const icon = entityIcon(ent.entity_id, stateVal);
    const isOn = stateVal && !["off","closed","unavailable","unknown"].includes(stateVal);
    const inputType = isMulti ? "checkbox" : "radio";
    const inputName = isMulti ? "" : `name="radio-entity-${this._selectedEntryId}-${this._selectedButton}"`;

    return `
      <div class="entity-row ${sel ? "selected" : ""}" data-entity="${ent.entity_id}">
        <input type="${inputType}" ${inputName} class="entity-check" ${sel ? "checked" : ""}
               data-entity-check="${ent.entity_id}">
        <span class="entity-icon">${icon}</span>
        <span class="entity-name">${this._esc(ent.name)}</span>
        <span class="entity-state ${isOn ? "on" : ""}">${stateLabel}</span>
      </div>`;
  }

  // ── Summary table ──────────────────────────────────────────────

  _renderSummarySection(entry, btnCfg) {
    const at = btnCfg.action_type || "none";
    const info = ACTION_TYPES[at];
    const targets = this._getSelectedTargets(btnCfg);

    if (!targets.length) {
      return `
        <div class="summary-section" id="summary-section" style="height:${this._summaryHeight}px">
          <div class="summary-header">
            <span>Programming — Button ${this._selectedButton}</span>
          </div>
          <div class="summary-empty">No items programmed for this button.</div>
        </div>`;
    }

    const rows = targets.map(entityId => {
      const stateObj = this._hass.states?.[entityId];
      const stateVal = stateObj?.state;
      const attrs = stateObj?.attributes || {};
      const entEntry = this._hass.entities?.[entityId];
      const name = friendlyName(this._hass, entityId, entEntry);
      const areaId = resolveAreaId(entityId, this._hass);
      const area = areaId ? areaName(this._hass, areaId) : "";
      const domain = entityId.split(".")[0];
      const domLabel = DOMAIN_LABELS[domain] || domain;
      const stateLabel = entityStateLabel(entityId, stateVal, attrs);
      const desc = area ? `${area} › ${name}` : name;

      return `
        <tr>
          <td><span class="type-badge">${domLabel}</span></td>
          <td>${this._esc(desc)}</td>
          <td>${stateLabel}</td>
          <td><button class="remove-entity" data-remove="${entityId}" title="Remove">✕</button></td>
        </tr>`;
    }).join("");

    return `
      <div class="summary-section" id="summary-section" style="height:${this._summaryHeight}px">
        <div class="summary-header">
          <span>Programming — Button ${this._selectedButton} (${info?.label || at})</span>
        </div>
        <table class="summary-table">
          <thead><tr>
            <th>Type</th><th>Item Description</th><th>Setting</th><th></th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  // ── Event wiring ───────────────────────────────────────────────

  _attachMainListeners(entry, buttons, btnCfg) {
    const shadow = this._shadow;

    // Keypad button clicks
    shadow.querySelectorAll("[data-kp-btn]").forEach(el => {
      el.addEventListener("click", () => {
        this._selectedButton = parseInt(el.dataset.kpBtn, 10);
        this._renderMain();
      });
    });

    // Prev/Next navigation
    const prev = shadow.getElementById("btn-prev");
    const next = shadow.getElementById("btn-next");
    if (prev) prev.addEventListener("click", () => {
      const n = parseInt(prev.dataset.prev, 10);
      if (!isNaN(n)) { this._selectedButton = n; this._renderMain(); }
    });
    if (next) next.addEventListener("click", () => {
      const n = parseInt(next.dataset.next, 10);
      if (!isNaN(n)) { this._selectedButton = n; this._renderMain(); }
    });

    // Label field
    const inpLabel = shadow.getElementById("inp-label");
    if (inpLabel) {
      inpLabel.addEventListener("change", () => {
        this._setBtnProp("label", inpLabel.value);
        // Refresh keypad visual only (avoid full re-render on every keystroke)
        shadow.querySelectorAll(`[data-kp-btn="${this._selectedButton}"]`).forEach(el => {
          if (!el.classList.contains("raise-lower")) el.textContent = inpLabel.value || `Btn ${this._selectedButton}`;
        });
      });
    }

    // Action type
    const selAction = shadow.getElementById("sel-action-type");
    if (selAction) {
      selAction.addEventListener("change", () => {
        this._setBtnProp("action_type", selAction.value);
        this._setBtnProp("action_target", "");
        this._renderMain();
      });
    }

    // LED logic
    const selLed = shadow.getElementById("sel-led-logic");
    if (selLed) {
      selLed.addEventListener("change", () => this._setBtnProp("led_mode", selLed.value));
    }

    // Cycle dim
    const chkCycle = shadow.getElementById("chk-cycle-dim");
    if (chkCycle) chkCycle.addEventListener("change", () => this._setBtnProp("cycle_dim", chkCycle.checked));

    // LED invert
    const chkInvert = shadow.getElementById("chk-led-invert");
    if (chkInvert) chkInvert.addEventListener("change", () => this._setBtnProp("led_invert", chkInvert.checked));

    // Extra config fields
    const inpBri = shadow.getElementById("inp-brightness");
    if (inpBri) inpBri.addEventListener("change", () => this._setBtnProp("target_brightness", parseInt(inpBri.value) || 0));

    const inpCCT = shadow.getElementById("inp-cct");
    if (inpCCT) inpCCT.addEventListener("change", () => this._setBtnProp("target_color_temp", parseInt(inpCCT.value) || 0));

    const inpSG = shadow.getElementById("inp-scene-group");
    if (inpSG) inpSG.addEventListener("change", () => this._setBtnProp("scene_group", inpSG.value.trim()));

    const inpLedEnt = shadow.getElementById("inp-led-entity");
    if (inpLedEnt) inpLedEnt.addEventListener("change", () => this._setBtnProp("led_entity", inpLedEnt.value.trim()));

    // Area filter
    const selArea = shadow.getElementById("sel-filter-area");
    if (selArea) {
      selArea.addEventListener("change", () => {
        this._filterArea = selArea.value;
        this._renderMain();
      });
    }

    // Expand all
    const btnExpand = shadow.getElementById("btn-expand-all");
    if (btnExpand) {
      btnExpand.addEventListener("click", () => {
        const at = (this._pendingConfig[this._selectedEntryId] || {})[this._selectedButton]?.action_type || "none";
        const entities = this._getEntitiesForAction(at);
        const byArea = this._groupByArea(entities);
        const allExpanded = Object.keys(byArea).every(k => this._expandedAreas.has(k));
        if (allExpanded) {
          Object.keys(byArea).forEach(k => this._expandedAreas.delete(k));
        } else {
          Object.keys(byArea).forEach(k => this._expandedAreas.add(k));
        }
        this._renderMain();
      });
    }

    // Area toggle (expand/collapse)
    shadow.querySelectorAll("[data-area-toggle]").forEach(el => {
      el.addEventListener("click", (e) => {
        if (e.target.type === "checkbox") return; // let checkbox handle it
        const areaId = el.dataset.areaToggle;
        if (this._expandedAreas.has(areaId)) {
          this._expandedAreas.delete(areaId);
        } else {
          this._expandedAreas.add(areaId);
        }
        this._renderMain();
      });
    });

    // Area checkboxes (select/deselect all in area)
    shadow.querySelectorAll("[data-area-check]").forEach(el => {
      el.addEventListener("change", (e) => {
        e.stopPropagation();
        const areaId = el.dataset.areaCheck;
        const at = (this._pendingConfig[this._selectedEntryId] || {})[this._selectedButton]?.action_type || "none";
        const entities = this._getEntitiesForAction(at);
        const areaEnts = entities.filter(ent => (resolveAreaId(ent.entity_id, this._hass) || "_none") === areaId);
        if (el.checked) {
          areaEnts.forEach(ent => this._selectEntity(ent.entity_id, true));
        } else {
          areaEnts.forEach(ent => this._selectEntity(ent.entity_id, false));
        }
        this._renderMain();
      });
    });

    // Entity checkboxes/radios
    shadow.querySelectorAll("[data-entity-check]").forEach(el => {
      el.addEventListener("change", () => {
        const entityId = el.dataset.entityCheck;
        const at = (this._pendingConfig[this._selectedEntryId] || {})[this._selectedButton]?.action_type || "none";
        const isMulti = ACTION_TYPES[at]?.multi || false;
        if (!isMulti) {
          this._setBtnProp("action_target", entityId);
        } else {
          this._selectEntity(entityId, el.checked);
        }
        this._renderMain();
      });
    });

    // Entity row click (also triggers checkbox)
    shadow.querySelectorAll(".entity-row").forEach(el => {
      el.addEventListener("click", (e) => {
        if (e.target.type === "checkbox" || e.target.type === "radio") return;
        const chk = el.querySelector("[data-entity-check]");
        if (chk) { chk.checked = !chk.checked; chk.dispatchEvent(new Event("change")); }
      });
    });

    // Remove from summary
    shadow.querySelectorAll("[data-remove]").forEach(el => {
      el.addEventListener("click", () => {
        this._selectEntity(el.dataset.remove, false);
        this._renderMain();
      });
    });

    // Set indeterminate on area checkboxes
    shadow.querySelectorAll("[data-indeterminate]").forEach(el => {
      el.indeterminate = true;
    });

    // Wire up keypad and summary resizers (re-bound each render)
    this._initResizers();
  }

  // ── Resize handling ────────────────────────────────────────────

  _initResizers() {
    const shadow = this._shadow;

    // Sidebar ↔ Main — bound once; the sidebar element persists across renders
    if (!this._sidebarResizerBound) {
      const sidebarResizer = shadow.getElementById("sidebar-resizer");
      const sidebar = shadow.getElementById("sidebar");
      if (sidebarResizer && sidebar) {
        this._setupHorizontalResizer(sidebarResizer, sidebar, 140, 450, w => {
          this._sidebarWidth = w;
        });
        this._sidebarResizerBound = true;
      }
    }

    // Keypad column ↔ Right column — re-bound each render
    const keypayResizer = shadow.getElementById("keypad-resizer");
    const colKeypad = shadow.querySelector(".col-keypad");
    if (keypayResizer && colKeypad) {
      this._setupHorizontalResizer(keypayResizer, colKeypad, 120, 380, w => {
        this._keypayWidth = w;
      });
    }

    // Prog-body ↔ Summary — re-bound each render; drag upward expands summary
    const summaryResizer = shadow.getElementById("summary-resizer");
    const summarySection = shadow.getElementById("summary-section");
    if (summaryResizer && summarySection) {
      this._setupVerticalResizer(summaryResizer, summarySection, 60, 600, h => {
        this._summaryHeight = h;
      });
    }
  }

  _setupHorizontalResizer(handle, target, min, max, onResize) {
    let startX, startW;
    handle.addEventListener("mousedown", e => {
      startX = e.clientX;
      startW = target.getBoundingClientRect().width;
      handle.classList.add("dragging");
      const onMove = ev => {
        const w = Math.max(min, Math.min(max, startW + ev.clientX - startX));
        target.style.width = w + "px";
        onResize(w);
      };
      const onUp = () => {
        handle.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
  }

  _setupVerticalResizer(handle, target, min, max, onResize) {
    let startY, startH;
    handle.addEventListener("mousedown", e => {
      startY = e.clientY;
      startH = target.getBoundingClientRect().height;
      handle.classList.add("dragging");
      const onMove = ev => {
        // Drag upward (negative delta) increases the summary height
        const h = Math.max(min, Math.min(max, startH + startY - ev.clientY));
        target.style.height = h + "px";
        onResize(h);
      };
      const onUp = () => {
        handle.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
  }

  // ── State helpers ──────────────────────────────────────────────

  _getEntry(entryId) {
    return this._entries.find(e => e.entry_id === entryId);
  }

  _setBtnProp(key, value) {
    const entryId = this._selectedEntryId;
    if (!this._pendingConfig[entryId]) return;
    if (!this._pendingConfig[entryId][this._selectedButton]) {
      this._pendingConfig[entryId][this._selectedButton] = defaultBtnCfg();
    }
    this._pendingConfig[entryId][this._selectedButton][key] = value;
    this._dirty[entryId] = true;
    this._updateSaveButton();
  }

  _selectEntity(entityId, selected) {
    const entryId = this._selectedEntryId;
    if (!entryId || !this._pendingConfig[entryId]) return;
    const btnCfg = this._pendingConfig[entryId][this._selectedButton];
    if (!btnCfg) return;

    const at = btnCfg.action_type || "none";
    const isMulti = ACTION_TYPES[at]?.multi || false;

    if (!isMulti) {
      btnCfg.action_target = selected ? entityId : "";
    } else {
      let targets = Array.isArray(btnCfg.action_target)
        ? [...btnCfg.action_target]
        : (btnCfg.action_target ? [btnCfg.action_target] : []);
      if (selected) {
        if (!targets.includes(entityId)) targets.push(entityId);
      } else {
        targets = targets.filter(t => t !== entityId);
      }
      btnCfg.action_target = targets;
    }
    this._dirty[entryId] = true;
    this._updateSaveButton();
  }

  _getSelectedTargets(btnCfg) {
    const raw = btnCfg.action_target;
    if (!raw) return [];
    if (Array.isArray(raw)) return raw.filter(Boolean);
    if (typeof raw === "string" && raw.includes(",")) return raw.split(",").map(s => s.trim()).filter(Boolean);
    if (typeof raw === "string" && raw) return [raw];
    return [];
  }

  _getEntitiesForAction(actionType) {
    const info = ACTION_TYPES[actionType];
    if (!info || !info.domains.length) return [];

    const result = [];
    const allEntities = this._hass.entities || {};
    for (const [entityId, ent] of Object.entries(allEntities)) {
      if (!info.domains.some(d => entityId.startsWith(d + "."))) continue;
      result.push({
        entity_id: entityId,
        name: friendlyName(this._hass, entityId, ent),
      });
    }
    result.sort((a, b) => a.name.localeCompare(b.name));
    return result;
  }

  _groupByArea(entities) {
    const byArea = {};
    for (const ent of entities) {
      const areaId = resolveAreaId(ent.entity_id, this._hass) || "_none";
      if (!byArea[areaId]) byArea[areaId] = [];
      byArea[areaId].push(ent);
    }
    return byArea;
  }

  // ── Save ──────────────────────────────────────────────────────

  _updateSaveButton() {
    const btn = this._shadow.getElementById("btn-save");
    if (btn) btn.disabled = !this._dirty[this._selectedEntryId];
  }

  async _saveConfig() {
    const entryId = this._selectedEntryId;
    if (!entryId) return;

    const pending = this._pendingConfig[entryId] || {};
    const buttons = {};
    for (const [btnNum, cfg] of Object.entries(pending)) {
      buttons[String(btnNum)] = cfg;
    }

    const saveBtn = this._shadow.getElementById("btn-save");
    const statusEl = this._shadow.getElementById("save-status");
    if (saveBtn) saveBtn.disabled = true;
    if (statusEl) statusEl.textContent = "Saving…";

    try {
      await this._hass.callWS({
        type: "lutron_keypad_controller/save_keypad_config",
        entry_id: entryId,
        buttons,
      });
      this._dirty[entryId] = false;
      if (statusEl) {
        statusEl.textContent = "✓ Saved";
        setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
      }
      // Reload entry data
      await this._loadEntries();
      this._renderSidebar();
    } catch (e) {
      console.error("LutronPanel: save failed", e);
      if (statusEl) statusEl.textContent = "⚠ Save failed";
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  // ── Utilities ─────────────────────────────────────────────────

  _esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}

customElements.define("lutron-keypad-panel", LutronKeypadsPanel);
