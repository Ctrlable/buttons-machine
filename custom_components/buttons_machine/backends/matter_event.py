from __future__ import annotations
_C='buttons_machine_bilresa'
_B='_bm_scroll_pending'
_A=None
import logging
from typing import Callable
from homeassistant.core import HomeAssistant,callback
from homeassistant.helpers.event import async_track_state_change_event
from.base import KeypadBackend
_LOGGER=logging.getLogger(__name__)
_HOLD='long_press'
_HOLD_RELEASE='long_release'
_SINGLE='multi_press_1'
_DOUBLE='multi_press_2'
class MatterEventBackend(KeypadBackend):
	source_domain='matter';license_product=_C;accepted_products=_C,'buttons_machine_ikea','buttons_machine';native_hold=True;native_double_tap=True
	def subscribe(E,hass,controller):
		A=controller;B=_button_entities(hass,A)
		if not B:_LOGGER.warning("'%s': no Matter button event entities found — nothing to listen to",A.name);return lambda:_A
		@callback
		def C(event):
			D=event;C=D.data.get('new_state')
			if C is _A or C.state in('unknown','unavailable'):return
			E=D.data.get('old_state')
			if E is not _A and E.state==C.state:return
			F=B.get(D.data['entity_id'])
			if F is _A:return
			G=str(C.attributes.get('event_type')or'');_dispatch(A,F,G)
		D=async_track_state_change_event(hass,list(B),C);_LOGGER.info("Buttons Machine '%s' registered (matter, %d button entities)",A.name,len(B));return D
	async def async_write_led(A,hass,led_entity,is_on):0
	async def async_find_leds(A,hass,config_entry):return{}
_SCROLL_SETTLE_S=.35
def _cancel_pending(controller,bank):
	A=getattr(controller,_B,_A)
	if not A:return
	B=A.pop(bank,_A)
	if B is not _A:B.cancel()
def _dispatch(controller,btn,ev_type):
	I='release';H='press';C=ev_type;B=btn;A=controller
	if C==_HOLD:A.handle_button(B,H);A.handle_button(B,'hold');return
	if C==_HOLD_RELEASE:A.handle_button(B,I);return
	if not C.startswith('multi_press_'):_LOGGER.debug("'%s': button %d -> unhandled event %r",A.name,B,C);return
	try:D=int(C.rsplit('_',1)[1])
	except(IndexError,ValueError):return
	J=B%3;E=(B-1)//3
	if J==0:
		_cancel_pending(A,E);A.handle_button(B,H)
		if D==2:A.handle_button(B,'double_tap')
		elif D>=3:A.handle_button(B,'triple_tap')
		A.handle_button(B,I);return
	K=1 if J==1 else-1;G=getattr(A,'handle_scroll',_A)
	if G is _A:A.handle_button(B,H);A.handle_button(B,I);return
	if D>=2:_cancel_pending(A,E);G(B,K,D);return
	F=getattr(A,_B,_A)
	if F is _A:F={};setattr(A,_B,F)
	_cancel_pending(A,E)
	def L():F.pop(E,_A);_LOGGER.debug("'%s': button %d single detent settled -> scrolling",A.name,B);G(B,K,D)
	F[E]=A.hass.loop.call_later(_SCROLL_SETTLE_S,L)
def _button_entities(hass,controller):
	from homeassistant.helpers import device_registry as G,entity_registry as C;import re;D=getattr(controller,'_config_entry',_A);A=str((D.data.get('device_id')if D else'')or'')
	if not A:return{}
	H=C.async_get(hass);I=G.async_get(hass)
	if I.async_get(A)is _A:return{}
	E={}
	for B in C.async_entries_for_device(H,A,include_disabled_entities=False):
		if B.domain!='event':continue
		F=re.search('(\\d+)$',B.entity_id)
		if F:E[B.entity_id]=int(F.group(1))
	return E