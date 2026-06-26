from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo,EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.const import DOMAIN
async def async_setup_entry(hass,entry,async_add_entities):
	A=entry
	if not A.data.get('_controller'):return
	from.import _discover_cover_cycle_covers as B;C=[LutronCalibrateTravelButton(hass,A,B)for B in B(hass)];async_add_entities(C)
class LutronCalibrateTravelButton(ButtonEntity):
	_attr_has_entity_name=True;_attr_should_poll=False;_attr_entity_category=EntityCategory.CONFIG;_attr_icon='mdi:ruler-square'
	def __init__(A,hass,entry,cover_id):B=cover_id;A._hass=hass;A._cover_id=B;D=B.split('.',1)[-1];A._attr_unique_id=f"{entry.entry_id}_calibrate_{D}";C=hass.states.get(B);E=C.name if C and C.name else D.replace('_',' ').title();A._attr_name=f"Calibrate {E} travel"
	@property
	def device_info(self):return DeviceInfo(identifiers={(DOMAIN,'controller')},name='Lutron Keypad Controller')
	async def async_press(A):from.import _calibrate_shade_travel as B;A._hass.async_create_task(B(A._hass,A._cover_id))