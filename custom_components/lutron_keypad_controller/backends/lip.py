from __future__ import annotations
_A='lutron_lip'
import logging,re
from typing import Callable
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID,SERVICE_TURN_OFF,SERVICE_TURN_ON
from homeassistant.core import HomeAssistant,callback
from homeassistant.helpers import device_registry as dr,entity_registry as er
from.base import KeypadBackend
_LOGGER=logging.getLogger(__name__)
LIP_EVENT='lutron_event'
def _lip_id(config_entry):return str(config_entry.data.get('lip_id','')).strip()
def _lip_device(hass,lip_id):
	C=dr.async_get(hass)
	for B in C.devices.values():
		for A in B.identifiers:
			if len(A)>=2 and A[0]==_A and str(A[1])==lip_id:return B
class LipBackend(KeypadBackend):
	source_domain=_A;native_hold=True;native_double_tap=True
	def subscribe(E,hass,controller):
		A=controller;B=_lip_id(A._config_entry);G=re.compile(rf"^keypad_{re.escape(B)}_\w*?(\d+)$")
		@callback
		def C(event):
			B=event.data;C=str(B.get('id',''));D=G.match(C)
			if not D:return
			E=int(D.group(1));F=B.get('action','press');_LOGGER.debug("'%s': lip event — id=%s btn=%d action=%s",A.name,C,E,F);A.handle_button(E,F)
		D=hass.bus.async_listen(LIP_EVENT,C);_LOGGER.info("Lutron Keypad Controller '%s' registered (lip, keypad %s)",A.name,B);return D
	async def async_write_led(C,hass,led_entity,is_on):A=led_entity;B=A.split('.',1)[0];await hass.services.async_call(B,SERVICE_TURN_ON if is_on else SERVICE_TURN_OFF,{ATTR_ENTITY_ID:A},blocking=True)
	async def async_find_leds(H,hass,config_entry):
		D=config_entry;B=_lip_id(D);E=_lip_device(hass,B)
		if E is None:_LOGGER.warning('lip LED discovery: no lutron_lip device for keypad %s',B);return{}
		G=er.async_get(hass);A={}
		for C in er.async_entries_for_device(G,E.id):
			if C.domain not in('switch','light'):continue
			F=re.search('_led_(\\d+)$',C.entity_id)
			if F:A[int(F.group(1))]=C.entity_id
		if A:_LOGGER.info("lip LED discovery for '%s' (keypad %s): %s",D.title,B,A)
		return A