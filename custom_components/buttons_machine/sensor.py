from __future__ import annotations
_I='scene_id'
_H='buttons'
_G='button'
_F='Lutron'
_E=False
_D='(not configured)'
_C=True
_B='label'
_A=None
import logging
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from.const import DOMAIN,CONF_KEYPAD_TYPE,KEYPAD_GENERIC,ATTR_ACTIVE_SCENE,CONF_ACTION_TYPE,CONF_ACTION_TARGET,CONF_LED_ENTITY,ACTION_STATEFUL_SCENE,ACTION_TYPES_NEEDING_ENTITY,get_button_layout
_LOGGER=logging.getLogger(__name__)
async def async_setup_platform(hass,config,async_add_entities,discovery_info=_A):
	C=hass.data.get(DOMAIN,{}).get('controllers',[]);A=[]
	for B in C:A.append(LutronKeypadsStatusSensor(_A,B));A.append(LutronKeypadsLastButtonSensor(_A,B))
	async_add_entities(A,_C)
async def async_setup_entry(hass,entry,async_add_entities):
	D='number';A=entry;E=hass.data.get(DOMAIN,{}).get('entry_controllers',{}).get(A.entry_id);B=[]
	if E is not _A:B.append(LutronKeypadsStatusSensor(A,E));B.append(LutronKeypadsLastButtonSensor(A,E))
	F=A.options.get(_H,{})
	for C in get_button_layout(A.data):
		G=str(C[D]);H=F.get(G,{}).get(CONF_ACTION_TYPE,'')
		if not C['is_raise']and not C['is_lower']:B.append(ButtonEntitySensor(A,C[D]))
		if H==ACTION_STATEFUL_SCENE:B.append(ButtonLedSensor(A,C[D]));B.append(ButtonSceneGroupSensor(A,C[D]))
	async_add_entities(B,_C)
class LutronKeypadsStatusSensor(RestoreEntity,SensorEntity):
	_attr_has_entity_name=_C;_attr_should_poll=_E
	def __init__(A,entry,controller):
		C=controller;B=entry;A._entry=B;A._controller=C
		if B is not _A:A._attr_unique_id=f"{B.entry_id}_status"
		else:A._attr_unique_id=f"lutron_keypad_{C.name.lower().replace(" ","_")}_status"
	@property
	def name(self):return'Status'
	@property
	def device_info(self):
		A=self
		if A._entry is _A:return
		return DeviceInfo(identifiers={(DOMAIN,A._entry.entry_id)},name=A._entry.title,manufacturer=_F,model=A._entry.data.get(CONF_KEYPAD_TYPE,KEYPAD_GENERIC).replace('_',' ').title())
	async def async_added_to_hass(A):
		await super().async_added_to_hass()
		if A._controller is not _A:A._controller.register_state_sensor(A)
		if A._entry is not _A:A.async_on_remove(A._entry.add_update_listener(A._on_entry_updated))
	async def _on_entry_updated(A,hass,entry):A._entry=entry;A.async_write_ha_state()
	@property
	def native_value(self):
		A=self._controller._last_action
		if A is _A:return'idle'
		B=A.get(_I,'')
		if B:return B.replace('scene.','').replace('_',' ').title()
		return A.get('type','active')
	@property
	def extra_state_attributes(self):
		B='active_button';A=self._controller._last_action
		if A is _A:return{ATTR_ACTIVE_SCENE:_A,B:_A}
		return{ATTR_ACTIVE_SCENE:A.get(_I),B:A.get(_G),'last_action_type':A.get('type')}
	@property
	def icon(self):return'mdi:remote'
class LutronKeypadsLastButtonSensor(RestoreEntity,SensorEntity):
	_attr_has_entity_name=_C;_attr_should_poll=_E
	def __init__(A,entry,controller):
		C=controller;B=entry;A._entry=B;A._controller=C
		if B is not _A:A._attr_unique_id=f"{B.entry_id}_last_button"
		else:A._attr_unique_id=f"lutron_keypad_{C.name.lower().replace(" ","_")}_last_button"
	@property
	def name(self):return'Last Button'
	@property
	def device_info(self):
		A=self
		if A._entry is _A:return
		return DeviceInfo(identifiers={(DOMAIN,A._entry.entry_id)},name=A._entry.title,manufacturer=_F,model=A._entry.data.get(CONF_KEYPAD_TYPE,KEYPAD_GENERIC).replace('_',' ').title())
	async def async_added_to_hass(A):
		await super().async_added_to_hass()
		if A._controller is not _A:A._controller.register_state_sensor(A)
		if A._entry is not _A:A.async_on_remove(A._entry.add_update_listener(A._on_entry_updated))
	async def _on_entry_updated(A,hass,entry):A._entry=entry;A.async_write_ha_state()
	@property
	def native_value(self):
		B=self._controller._last_action
		if B is _A:return
		A=B.get(_G)
		if A is _A:return
		D=self._controller._buttons.get(A,{});C=D.get(_B,'');return f"{A}"+(f" — {C}"if C else'')
	@property
	def extra_state_attributes(self):
		D='action_type';B=self._controller._last_action
		if B is _A:return{}
		A=B.get(_G)
		if A is _A:return{}
		C=self._controller._buttons.get(A,{});return{'button_number':A,_B:C.get(_B,''),D:C.get(D,'')}
	@property
	def icon(self):return'mdi:gesture-tap-button'
class _LutronButtonSensorBase(SensorEntity):
	_attr_has_entity_name=_C;_attr_should_poll=_E
	def __init__(A,entry,btn_number):B=btn_number;A._entry=entry;A._btn_number=B;A._btn_key=str(B)
	@property
	def device_info(self):A=self;return DeviceInfo(identifiers={(DOMAIN,A._entry.entry_id)},name=A._entry.title,manufacturer=_F,model=A._entry.data.get(CONF_KEYPAD_TYPE,KEYPAD_GENERIC).replace('_',' ').title())
	def _get_btn_cfg(A):return A._entry.options.get(_H,{}).get(A._btn_key,{})
	async def async_added_to_hass(A):A.async_on_remove(A._entry.add_update_listener(A._on_entry_updated))
	async def _on_entry_updated(A,hass,entry):A._entry=entry;A.async_write_ha_state()
	@property
	def extra_state_attributes(self):return{'configure_via':'gear icon → Configure'}
class ButtonEntitySensor(_LutronButtonSensorBase):
	@property
	def unique_id(self):return f"{self._entry.entry_id}_button_{self._btn_number}_entity_1"
	@property
	def name(self):A=self._get_btn_cfg().get(_B)or f"Button {self._btn_number}";return f"{A} Entity"
	@property
	def icon(self):return'mdi:target'
	@property
	def available(self):return self._get_btn_cfg().get(CONF_ACTION_TYPE,'')in ACTION_TYPES_NEEDING_ENTITY
	@property
	def native_value(self):
		A=self._get_btn_cfg().get(CONF_ACTION_TARGET)
		if isinstance(A,list):return', '.join(A)if A else _D
		return A or _D
class ButtonLedSensor(_LutronButtonSensorBase):
	@property
	def unique_id(self):return f"{self._entry.entry_id}_button_{self._btn_number}_led"
	@property
	def name(self):A=self._get_btn_cfg().get(_B)or f"Button {self._btn_number}";return f"{A} LED Entity"
	@property
	def icon(self):return'mdi:led-on'
	@property
	def native_value(self):return self._get_btn_cfg().get(CONF_LED_ENTITY)or _D
class ButtonSceneGroupSensor(_LutronButtonSensorBase):
	@property
	def unique_id(self):return f"{self._entry.entry_id}_button_{self._btn_number}_scene_group"
	@property
	def name(self):A=self._get_btn_cfg().get(_B)or f"Button {self._btn_number}";return f"{A} Scene Group"
	@property
	def icon(self):return'mdi:group'
	@property
	def native_value(self):return self._get_btn_cfg().get('scene_group')or _D