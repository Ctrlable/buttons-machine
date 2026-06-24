from __future__ import annotations
_A='buttons'
from homeassistant.components.text import TextEntity,TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.const import DOMAIN,CONF_KEYPAD_TYPE,KEYPAD_GENERIC,get_button_layout
async def async_setup_entry(hass,entry,async_add_entities):A=entry;B=[LutronButtonLabelText(A,B['number'])for B in get_button_layout(A.data)];async_add_entities(B,True)
class LutronButtonLabelText(TextEntity):
	_attr_has_entity_name=True;_attr_should_poll=False;_attr_mode=TextMode.TEXT;_attr_native_min=0;_attr_native_max=255
	def __init__(A,entry,btn_number):B=btn_number;A._entry=entry;A._btn_number=B;A._btn_key=str(B)
	@property
	def unique_id(self):return f"{self._entry.entry_id}_button_{self._btn_number}_label"
	@property
	def name(self):return f"Button {self._btn_number} Label"
	@property
	def icon(self):return'mdi:label-outline'
	@property
	def device_info(self):A=self;return DeviceInfo(identifiers={(DOMAIN,A._entry.entry_id)},name=A._entry.title,manufacturer='Lutron',model=A._entry.data.get(CONF_KEYPAD_TYPE,KEYPAD_GENERIC).replace('_',' ').title())
	def _get_btn_cfg(A):return A._entry.options.get(_A,{}).get(A._btn_key,{})
	async def async_added_to_hass(A):A.async_on_remove(A._entry.add_update_listener(A._on_entry_updated))
	async def _on_entry_updated(A,hass,entry):A._entry=entry;A.async_write_ha_state()
	@property
	def native_value(self):return self._get_btn_cfg().get('label')or f"Button {self._btn_number}"
	async def async_set_value(A,value):B=dict(A._entry.options.get(_A,{}));C=dict(B.get(A._btn_key,{}));C['label']=value.strip()or f"Button {A._btn_number}";B[A._btn_key]=C;A.hass.config_entries.async_update_entry(A._entry,options={_A:B});await A.hass.config_entries.async_reload(A._entry.entry_id)