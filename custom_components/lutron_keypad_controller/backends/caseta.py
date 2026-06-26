from __future__ import annotations
import logging
from typing import Callable
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID,SERVICE_TURN_OFF,SERVICE_TURN_ON
from homeassistant.core import HomeAssistant,callback
from.base import KeypadBackend
_LOGGER=logging.getLogger(__name__)
class CasetaBackend(KeypadBackend):
	source_domain='lutron_caseta';native_hold=False;native_double_tap=False
	def subscribe(E,hass,controller):
		B=controller;from..const import LUTRON_EVENT as A
		@callback
		def C(event):
			F='action';E='leap_button_number';D='button_number';A=event.data;_LOGGER.debug("'%s': event received — serial=%s device_id=%s btn=%s leap_btn=%s action=%s",B.name,A.get('serial'),A.get('device_id'),A.get(D),A.get(E),A.get(F))
			if not B._matches_event(A):return
			C=A.get(D)
			if C is None:
				C=A.get(E)
				if C is None:return
			B.handle_button(int(C),A.get(F,'press'))
		D=hass.bus.async_listen(A,C);_LOGGER.info("Lutron Keypad Controller '%s' registered (caseta, serial=%s)",B.name,B.serial);return D
	async def async_write_led(A,hass,led_entity,is_on):await hass.services.async_call('switch',SERVICE_TURN_ON if is_on else SERVICE_TURN_OFF,{ATTR_ENTITY_ID:led_entity},blocking=True)
	async def async_find_leds(F,hass,config_entry):
		B=config_entry;from..import _find_led_entities as C,_find_led_entities_by_button_entities as D,_normalize_led_map as E;A=await D(hass,B)
		if not A:A=await C(hass,B)
		return E(A,B)if A else{}