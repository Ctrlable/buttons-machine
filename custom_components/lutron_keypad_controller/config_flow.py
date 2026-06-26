from __future__ import annotations
_A5='led_bindings'
_A4='device_not_found'
_A3='already_configured'
_A2='lutron_not_loaded'
_A1='model_number'
_A0='controller'
_z='remote'
_y='hybrid'
_x='alisee'
_w='scene_group'
_v='keypad_name'
_u='is_lower'
_t='is_raise'
_s='value'
_r='lutron_type'
_q='caseta'
_p='Lower'
_o='Raise'
_n='direction'
_m='device_name'
_l='model'
_k='leap_button_map'
_j='-down'
_i=' down'
_h='-lower'
_g=' lower'
_f='-up'
_e=' up'
_d='-raise'
_c=' raise'
_b='leap_button_number'
_a='button_number'
_Z='pico'
_Y='tabletop'
_X='seetouch'
_W='sunnata'
_V='palladiom'
_U='lip'
_T='engraving'
_S='area'
_R='lutron_lip'
_Q='lower_button'
_P='raise_button'
_O='configurable_buttons'
_N='area_name'
_M='lutron_caseta'
_L='unique_id'
_K='button_numbers'
_J='button_names'
_I='keypad'
_H='device_id'
_G='type'
_F='number'
_E='buttons'
_D='serial'
_C='label'
_B='name'
_A=None
import logging,re
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant,callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import area_registry as ar,device_registry as dr,entity_registry as er,selector
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
import homeassistant.helpers.config_validation as cv
from.const import DOMAIN,ACTION_ENTITY_TOGGLE,CONF_DEVICE_SERIAL,CONF_DEVICE_NAME,CONF_AREA_NAME,CONF_KEYPAD_TYPE,CONF_ACTION_TYPE,CONF_ACTION_TARGET,CONF_LED_ENTITY,CONF_LED_INVERT,CONF_LED_MODE,CONF_TARGET_BRIGHTNESS,CONF_TARGET_COLOR_TEMP,LED_MODE_ROOM,LED_MODE_SCENE,ACTION_STATEFUL_SCENE,KEYPAD_SEETOUCH,KEYPAD_SEETOUCH_HYBRID,KEYPAD_SUNNATA,KEYPAD_SUNNATA_HYBRID,KEYPAD_ALISEE,KEYPAD_PALLADIOM,KEYPAD_TABLETOP,KEYPAD_PICO,KEYPAD_GENERIC,ACTION_NONE,ACTION_RAISE,ACTION_LOWER,ACTION_TYPE_LABELS,ACTION_TYPE_DOMAINS,ACTION_TYPES_NEEDING_ENTITY,MULTI_ENTITY_ACTIONS,get_button_list,get_button_layout
_LOGGER=logging.getLogger(__name__)
LUTRON_TYPE_MAP={'SeeTouchKeypad':KEYPAD_SEETOUCH,'SeeTouchHybridKeypad':KEYPAD_SEETOUCH_HYBRID,'HybridSeeTouch':KEYPAD_SEETOUCH_HYBRID,'HybridSeeTouchKeypad':KEYPAD_SEETOUCH_HYBRID,'SeeTouch':KEYPAD_SEETOUCH,'SunnataKeypad':KEYPAD_SUNNATA,'SunnataHybridKeypad':KEYPAD_SUNNATA_HYBRID,'SunnataSwitchingKeypad':KEYPAD_SUNNATA,'Sunnata':KEYPAD_SUNNATA,'AlisseKeypad':KEYPAD_ALISEE,'AlisseSeeTouchKeypad':KEYPAD_ALISEE,'Alisse':KEYPAD_ALISEE,'AliseeKeypad':KEYPAD_ALISEE,'AliseeSeeTouchKeypad':KEYPAD_ALISEE,'Alisee':KEYPAD_ALISEE,'GrafikEyeQS':KEYPAD_ALISEE,'GRAFIK Eye QS':KEYPAD_ALISEE,'PalladiomKeypad':KEYPAD_PALLADIOM,'PalladiomKeypad2Button':KEYPAD_PALLADIOM,'PalladiomKeypad3Button':KEYPAD_PALLADIOM,'PalladiomKeypad4Button':KEYPAD_PALLADIOM,'PalladiomKeypad5Button':KEYPAD_PALLADIOM,'PalladiomKeypad7Button':KEYPAD_PALLADIOM,'Palladiom':KEYPAD_PALLADIOM,'PalladiomWirelessKeypad':KEYPAD_PALLADIOM,'PalladiomSeeTouchKeypad':KEYPAD_PALLADIOM,'PalladiomHybridKeypad':KEYPAD_PALLADIOM,'TabletopSeeTouch':KEYPAD_TABLETOP,'SeeTouchTabletop':KEYPAD_TABLETOP,'TabletopKeypad':KEYPAD_TABLETOP,'Pico1Button':KEYPAD_PICO,'Pico2Button':KEYPAD_PICO,'Pico2ButtonRaiseLower':KEYPAD_PICO,'Pico3Button':KEYPAD_PICO,'Pico3ButtonRaiseLower':KEYPAD_PICO,'Pico4Button':KEYPAD_PICO,'Pico4ButtonScene':KEYPAD_PICO,'Pico4ButtonZone':KEYPAD_PICO,'Pico4Button2Group':KEYPAD_PICO,'FourGroupRemote':KEYPAD_PICO,'PaddleRemote':KEYPAD_PICO}
LUTRON_TYPE_FUZZY=[('aliss',KEYPAD_ALISEE),(_x,KEYPAD_ALISEE),(_V,KEYPAD_PALLADIOM),(_W,KEYPAD_SUNNATA),(_y,KEYPAD_SEETOUCH_HYBRID),(_X,KEYPAD_SEETOUCH),(_Y,KEYPAD_TABLETOP),(_Z,KEYPAD_PICO),(_z,KEYPAD_PICO),(_I,KEYPAD_SEETOUCH)]
BUTTON_TYPE_KEYWORDS={_I,_Z,_z,_X,_W,'aliss',_x,_V,_Y,_y}
def _infer_keypad_type(device_type):
	A=device_type
	if A in LUTRON_TYPE_MAP:return LUTRON_TYPE_MAP[A]
	C=A.lower()
	for(D,B)in LUTRON_TYPE_FUZZY:
		if D in C:_LOGGER.debug('Fuzzy-matched device type %r → %s',A,B);return B
	_LOGGER.warning('Unrecognized Lutron device type %r — falling back to generic keypad',A);return KEYPAD_GENERIC
def _is_keypad_device(device):
	A=device.get(_G,'')
	if A in LUTRON_TYPE_MAP:return True
	B=A.lower();return any(A in B for A in BUTTON_TYPE_KEYWORDS)
def _iter_lutron_bridges(hass):
	D='bridge'
	for C in hass.config_entries.async_entries(_M):
		if C.state is not ConfigEntryState.LOADED:continue
		E=getattr(C,'runtime_data',_A)
		if E is not _A:
			A=getattr(E,D,_A)
			if A is not _A:yield A;continue
		B=hass.data.get(_M,{}).get(C.entry_id)
		if B is not _A:
			A=getattr(B,D,_A)
			if A is _A and isinstance(B,dict):A=B.get(D)
			if A is not _A:yield A
def _get_lutron_bridge(hass):return next(_iter_lutron_bridges(hass),_A)
def _discover_keypads(hass):
	D=set();B=[]
	for E in _iter_lutron_bridges(hass):
		try:F=E.get_devices()
		except Exception as G:_LOGGER.warning('Could not query Lutron bridge devices: %s',G);continue
		for C in F.values():
			if not _is_keypad_device(C):continue
			A=str(C.get(_D,''))
			if A and A in D:continue
			B.append(C)
			if A:D.add(A)
	B.sort(key=lambda d:(d.get(_N,''),d.get(_B,'')));return B
def _build_device_options(keypads):
	B={}
	for A in keypads:
		C=str(A.get(_D,''))
		if not C:continue
		D=A.get(_N,'Unknown Area');E=A.get(_B,'Unknown');F=_infer_keypad_type(A.get(_G,''));B[C]=f"{D} — {E}  [{F}]"
	return B
def _resolve_btn_num(bd):
	for B in(_a,_b):
		A=bd.get(B)
		if A is not _A:
			try:return int(A)
			except(TypeError,ValueError):pass
def _strip_engraving(full_name,area,device):
	D=device;C=full_name;A=C.strip()
	for B in[f"{area} {D}",D,area]:
		B=B.strip()
		if B and A.lower().startswith(B.lower()):A=A[len(B):].strip();break
	return A.title()if A else C.strip()
import re as _re_cf
_RAISE_NAME_RE=_re_cf.compile('\\braise\\b',_re_cf.IGNORECASE)
_LOWER_NAME_RE=_re_cf.compile('\\blower\\b',_re_cf.IGNORECASE)
def _build_layout_from_button_devices(candidates,area_name,device_name):
	I=candidates;B=sorted({O for A in I if(O:=_resolve_btn_num(A))is not _A})
	if not B:return{}
	C=_A;D=_A;F={};G={}
	for H in I:
		E=H.get(_B,'');J=E.lower();A=_resolve_btn_num(H);K=H.get(_b)
		if A is not _A and K is not _A:
			try:
				L=int(K)
				if L!=A:G[str(L)]=A
			except(TypeError,ValueError):pass
		if A is _A:continue
		if J.endswith((_c,_d,_e,_f))or _RAISE_NAME_RE.search(E):C=A
		elif J.endswith((_g,_h,_i,_j))or _LOWER_NAME_RE.search(E):D=A
		M=_strip_engraving(E,area_name,device_name)
		if M:F[str(A)]=M
	N=[A for A in B if A not in(C,D)];_LOGGER.debug('button_devices layout: %d total, configurable=%s raise=%s lower=%s names=%s leap_map=%s',len(B),N,C,D,F,G);return{_K:B,_O:N,_P:C,_Q:D,_J:F,_k:G}
def _build_layout_from_inline_buttons(buttons_list,area_name,device_name,device_full_name=''):
	A=[];C=_A;D=_A;F={};G={};O=device_name or device_full_name
	for H in buttons_list:
		I=H.get(_a)
		if I is _A:continue
		try:B=int(I)
		except(TypeError,ValueError):continue
		E=H.get(_B,'');J=E.lower()
		if J.endswith((_c,_d,_e,_f))or _RAISE_NAME_RE.search(E):C=B
		elif J.endswith((_g,_h,_i,_j))or _LOWER_NAME_RE.search(E):D=B
		A.append(B);K=_strip_engraving(E,area_name,O)
		if K:F[str(B)]=K
		L=H.get(_b)
		if L is not _A:
			try:
				M=int(L)
				if M!=B:G[str(M)]=B
			except(TypeError,ValueError):pass
	A=sorted(set(A));N=[A for A in A if A not in(C,D)];_LOGGER.debug('inline-buttons layout: %d total, configurable=%s raise=%s lower=%s names=%s leap_map=%s',len(A),N,C,D,F,G);return{_K:A,_O:N,_P:C,_Q:D,_J:F,_k:G}
def _build_layout_from_bridge_buttons(candidates,area_name,device_name,has_raise_lower=True):
	J=has_raise_lower;D=[];A=_A;B=_A;H={};I=[]
	for F in candidates:
		K=F.get(_a)
		if K is _A:continue
		try:E=int(K)
		except(TypeError,ValueError):continue
		G=F.get('button_name')or F.get(_B,'');L=G.lower();O=F.get('button_led')is not _A
		if J:
			if L.endswith((_c,_d,_e,_f))or _RAISE_NAME_RE.search(G):A=E
			elif L.endswith((_g,_h,_i,_j))or _LOWER_NAME_RE.search(G):B=E
			elif not O:I.append(E)
		D.append(E);M=_strip_engraving(G,area_name,device_name)
		if M:H[str(E)]=M
	if J:
		for C in sorted(I):
			if C%2==1 and A is _A:A=C
			elif C%2==0 and B is _A:B=C
		for C in sorted(I):
			if A is _A and C!=B:A=C
			elif B is _A and C!=A:B=C
	D=sorted(set(D));N=[C for C in D if C not in(A,B)];_LOGGER.debug('bridge.buttons layout: %d total, configurable=%s raise=%s lower=%s names=%s',len(D),N,A,B,H);return{_K:D,_O:N,_P:A,_Q:B,_J:H,_k:{}}
def _detect_button_layout(hass,serial,keypad_type,device_name='',area_name='',device_id='',device_data=_A):
	H=area_name;G=device_name;C=device_id;A=serial
	for E in _iter_lutron_bridges(hass):
		F=getattr(E,'button_devices',_A)or{}
		if F:
			I=[B for B in F.values()if A and str(B.get(_D,''))==A or C and str(B.get(_H,''))==C]
			if I:_LOGGER.debug('Strategy 1 (button_devices): %d entries for serial=%s device_id=%s',len(I),A,C);return _build_layout_from_button_devices(I,H,G)
		B=device_data
		if B is _A:
			try:O=E.get_devices()
			except Exception as P:_LOGGER.warning('bridge.get_devices() failed during layout detection: %s',P);continue
			for J in O.values():
				if A and str(J.get(_D,''))==A or C and str(J.get(_H,''))==C:B=J;break
		if B is _A:continue
		D=str(B.get(_H,''))or C;_LOGGER.debug('Device serial=%s on bridge %s — type=%r model=%r device_id=%s inline_buttons=%d button_devices_total=%d',A,type(E).__name__,B.get(_G),B.get(_l),D,len(B.get(_E,[])),len(F));K=B.get(_E,[])
		if K:_LOGGER.debug('Strategy 2 (inline buttons): %d buttons for serial=%s',len(K),A);return _build_layout_from_inline_buttons(K,H,G,B.get(_B,''))
		L=getattr(E,_E,_A)or{}
		if L:
			M=[B for B in L.values()if A and str(B.get(_D,''))==A or D and str(B.get('parent_device',''))==D]
			if M:_LOGGER.debug('Strategy 3 (bridge.buttons): %d buttons for serial=%s device_id=%s',len(M),A,D);from.const import KEYPAD_LAYOUTS as N,KEYPAD_GENERIC as Q;S,R=N.get(keypad_type,N[Q]);return _build_layout_from_bridge_buttons(M,H,G,has_raise_lower=R)
		_LOGGER.warning('Device serial=%s (type=%r model=%r device_id=%s) found on bridge but carries no button data (button_devices=%d, inline_buttons=0, bridge.buttons=%d). Full device info: %s',A,B.get(_G),B.get(_l),D,len(F),len(L),B);return{}
	_LOGGER.debug('Device serial=%s device_id=%s not found on any bridge; falling back to keypad-type static layout.',A,C);return{}
def _infer_lip_keypad_type(model):
	A=(model or'').lower()
	if _V in A:return KEYPAD_PALLADIOM
	if _W in A:return KEYPAD_SUNNATA
	if _X in A or'see touch'in A:return KEYPAD_SEETOUCH
	if'alisse'in A or'alise'in A:return KEYPAD_ALISEE
	if _Y in A or'table top'in A:return KEYPAD_TABLETOP
	if _Z in A:return KEYPAD_PICO
	return KEYPAD_GENERIC
_LIP_DEFAULT_NAME_RE=re.compile('^[A-Za-z]{2,5}\\s*\\d{1,4}$')
async def _lip_xml_naming(hass):
	P='Name';E=hass;import xml.etree.ElementTree as Q;F=E.data.setdefault(DOMAIN,{}).setdefault('_lip_xml_naming',{});J=E.config_entries.async_entries(_R)
	if not J:return{}
	A=J[0].data.get('host')
	if not A:return{}
	if A in F:return F[A]
	try:
		from homeassistant.helpers.aiohttp_client import async_get_clientsession as R;import aiohttp as S;T=R(E)
		async with T.get(f"http://{A}/DbXmlInfo.xml",timeout=S.ClientTimeout(total=15))as U:V=await U.text()
		K=Q.fromstring(V);L=lambda tag:tag.split('}')[-1];M={B:A for A in K.iter()for B in A};G={}
		for B in K.iter():
			if L(B.tag)!='Device':continue
			if'KEYPAD'not in(B.get('DeviceType')or'').upper():continue
			N=B.get('IntegrationID')
			if not N:continue
			H=I='';C=M.get(B)
			while C is not _A:
				O,D=L(C.tag),C.get(P)
				if O=='DeviceGroup'and D and not I:I=D
				elif O=='Area'and D and not H:H=D
				C=M.get(C)
			G[str(N)]={_S:H,'group':I,_m:B.get(P)or''}
		F[A]=G;return G
	except Exception:return{}
def _build_lip_name(nm,lip_id):
	E=lip_id;A=[]
	for B in(nm.get(_S,''),nm.get('group','')):
		B=(B or'').strip()
		if B and B.lower()not in(A.lower()for A in A):A.append(B)
	C=(nm.get(_m,'')or'').strip()
	if C and not _LIP_DEFAULT_NAME_RE.match(C)and C.lower()not in(A.lower()for A in A):A.append(C)
	D=' '.join(A)
	if not D:return''
	if D.lower().rstrip().endswith(_I):return f"{D} {E}"
	return f"{D} Keypad {E}"
def _lip_button_info(hass):
	B={}
	try:
		F=hass.data.get(_R)or{}
		for G in F.values():
			C=getattr(G,_A0,_A)
			if C is _A:continue
			for H in getattr(C,'areas',[])or[]:
				for D in getattr(H,'keypads',[])or[]:
					E=str(getattr(D,'integration_id','')or'')
					if not E:continue
					I=B.setdefault(E,{})
					for A in getattr(D,_E,[])or[]:
						try:J=int(getattr(A,'component_number'))
						except(TypeError,ValueError):continue
						I[J]={_T:(getattr(A,_T,'')or'').strip(),_G:getattr(A,'button_type','')or'',_n:getattr(A,_n,'')or''}
	except Exception:return{}
	return B
async def _discover_lip_keypads(hass):
	F=hass;U=dr.async_get(F);V=er.async_get(F);W=_lip_button_info(F);X=await _lip_xml_naming(F);P=[]
	for B in U.devices.values():
		C=next((str(A[1])for A in B.identifiers if A[0]==_R),_A)
		if C is _A:continue
		E={}
		for J in er.async_entries_for_device(V,B.id):
			if J.domain!='event':continue
			Q=re.search('(\\d+)$',J.entity_id)
			if Q:A=int(Q.group(1));E[A]=J.original_name or J.name or f"Button {A}"
		if not E:continue
		K=sorted(E);R=W.get(C,{});L={};G=H=_A
		for A in K:
			N=R.get(A,{});M=N.get(_n,'')
			if M==_o:G=A
			elif M==_p:H=A
			if M in(_o,_p):L[str(A)]=M
			elif N.get(_T):L[str(A)]=N[_T]
			else:L[str(A)]=E[A]
		if G is _A and H is _A and not R:H=18 if 18 in E else _A;G=19 if 19 in E else _A
		Y=[A for A in K if A not in(G,H)];O=B.model or'';S=X.get(C,{});I=(S.get(_S)or'').strip()
		if not I and B.area_id:
			T=ar.async_get(F).async_get_area(B.area_id)
			if T:I=T.name
		if B.name_by_user:D=B.name_by_user
		else:
			D=_build_lip_name(S,C)
			if not D:D=f"{I} keypad {C}"if I else B.name or f"keypad {C}"
		P.append({_L:f"lip_{C}",_B:D,_C:f"{D} ({O or _I}, {len(K)} buttons)",'data':{_B:D,'backend':_U,'lip_id':C,_H:B.id,CONF_DEVICE_SERIAL:f"lip_{C}",CONF_DEVICE_NAME:D,CONF_AREA_NAME:I,CONF_KEYPAD_TYPE:_infer_lip_keypad_type(O),_A1:O,_K:K,_J:L,_O:Y,_P:G,_Q:H}})
	return sorted(P,key=lambda k:k[_B])
class LutronKeypadsConfigFlow(config_entries.ConfigFlow,domain=DOMAIN):
	VERSION=1
	def __init__(A):A._discovered_keypads=[];A._selected_device=_A;A._detected_layout={}
	async def async_step_user(A,user_input=_A):
		C=bool(A.hass.config_entries.async_entries(_M));B=bool(A.hass.config_entries.async_entries(_R))
		if not C and not B:return A.async_abort(reason=_A2)
		if C and B:return await A.async_step_source()
		if B:return await A.async_step_lip()
		return await A.async_step_caseta()
	async def async_step_source(A,user_input=_A):
		C=user_input;B='source'
		if C is not _A:
			if C[B]==_U:return await A.async_step_lip()
			return await A.async_step_caseta()
		return A.async_show_form(step_id=B,data_schema=vol.Schema({vol.Required(B,default=_q):vol.In({_q:'Caséta / RA2 Select (lutron_caseta)',_U:'Homeworks QS / RadioRA (lutron_lip)'})}))
	async def async_step_lip(A,user_input=_A):
		D=user_input;F=await _discover_lip_keypads(A.hass);G={A.unique_id or''for A in A.hass.config_entries.async_entries(DOMAIN)};B=[A for A in F if A[_L]not in G]
		if not B:return A.async_abort(reason=_A3)
		E={}
		if D is not _A:
			H=D.get(_I);C=next((A for A in B if A[_L]==H),_A)
			if C is _A:E['base']=_A4
			else:await A.async_set_unique_id(C[_L]);A._abort_if_unique_id_configured();return A.async_create_entry(title=C[_B],data=C['data'])
		return A.async_show_form(step_id=_U,data_schema=vol.Schema({vol.Required(_I):vol.In({A[_L]:A[_C]for A in B})}),errors=E,description_placeholders={'count':str(len(B))})
	async def async_step_caseta(A,user_input=_A):
		F='device_serial';C=user_input;G=A.hass.config_entries.async_entries(_M)
		if not G:return A.async_abort(reason=_A2)
		if not A._discovered_keypads:A._discovered_keypads=await A.hass.async_add_executor_job(_discover_keypads,A.hass)
		if not A._discovered_keypads:return await A.async_step_manual()
		H={A.unique_id or''for A in A.hass.config_entries.async_entries(DOMAIN)};B=[A for A in A._discovered_keypads if str(A.get(_D,''))not in H]
		if not B:return A.async_abort(reason=_A3)
		I=_build_device_options(B);D={}
		if C is not _A:
			E=C.get(F,'');A._selected_device=next((A for A in B if str(A.get(_D,''))==E),_A)
			if A._selected_device is _A:D['base']=_A4
			else:await A.async_set_unique_id(E);A._abort_if_unique_id_configured();J=str(A._selected_device.get(_D,''));K=_infer_keypad_type(A._selected_device.get(_G,''));A._detected_layout=_detect_button_layout(A.hass,J,K,device_name=A._selected_device.get(_B,''),area_name=A._selected_device.get(_N,''),device_id=str(A._selected_device.get(_H,'')),device_data=A._selected_device);return await A.async_step_confirm()
		return A.async_show_form(step_id=_q,data_schema=vol.Schema({vol.Required(F):vol.In(I)}),errors=D,description_placeholders={'count':str(len(B))})
	async def async_step_confirm(B,user_input=_A):
		G=user_input;A=B._selected_device
		if A is _A:return await B.async_step_user()
		E=A.get(_G,'');F=_infer_keypad_type(E);C=A.get(_N,'');D=A.get(_B,'');H=str(A.get(_D,''));I=f"{C} — {D}"if C else D
		if G is not _A:J=G.get(_B,I).strip();return B.async_create_entry(title=J,data={_B:J,CONF_DEVICE_SERIAL:H,CONF_DEVICE_NAME:D,CONF_AREA_NAME:C,CONF_KEYPAD_TYPE:F,_r:E,_A1:A.get(_l,''),_H:A.get(_H,''),**B._detected_layout})
		K=B._detected_layout.get(_K,[])
		if K:L=f"{len(K)} buttons detected from bridge"
		else:M=get_button_list(F);L=f"{len(M)} buttons (estimated from keypad type)"
		return B.async_show_form(step_id='confirm',data_schema=vol.Schema({vol.Required(_B,default=I):str}),description_placeholders={_S:C or'—',_m:D,'keypad_type':F,_D:H,_r:E,'button_count':L})
	async def async_step_manual(B,user_input=_A):
		A=user_input;D={}
		if A is not _A:
			C=A.get(CONF_DEVICE_SERIAL,'').strip()
			if not C:D[CONF_DEVICE_SERIAL]='serial_required'
			else:await B.async_set_unique_id(C);B._abort_if_unique_id_configured();E=A.get(_B,C).strip();return B.async_create_entry(title=E,data={_B:E,CONF_DEVICE_SERIAL:C,CONF_DEVICE_NAME:A.get(CONF_DEVICE_NAME,''),CONF_AREA_NAME:A.get(CONF_AREA_NAME,''),CONF_KEYPAD_TYPE:KEYPAD_GENERIC,_r:''})
		return B.async_show_form(step_id='manual',data_schema=vol.Schema({vol.Required(_B):str,vol.Required(CONF_DEVICE_SERIAL):str,vol.Optional(CONF_DEVICE_NAME,default=''):str,vol.Optional(CONF_AREA_NAME,default=''):str}),errors=D,description_placeholders={'note':'Auto-discovery failed — the Lutron bridge may not be reachable yet. Enter the serial manually: press any button on the keypad and check Developer Tools → Events → lutron_caseta_button_event.'})
	async def async_step_panel(A,user_input=_A):
		B=user_input
		if not B:return A.async_abort(reason='no_data')
		C=str(B.get(CONF_DEVICE_SERIAL,'')).strip()
		if not C:return A.async_abort(reason='no_serial')
		await A.async_set_unique_id(C);A._abort_if_unique_id_configured();D=str(B.pop(_B,C)).strip()or C;return A.async_create_entry(title=D,data=B)
	async def async_step_controller(A,user_input=_A):await A.async_set_unique_id(_A0);A._abort_if_unique_id_configured();return A.async_create_entry(title='Lutron Keypad Controller',data={'_controller':True})
	@staticmethod
	@callback
	def async_get_options_flow(config_entry):return LutronKeypadsOptionsFlow()
_ACTION_OPTIONS=[{_s:A,_C:B}for(A,B)in ACTION_TYPE_LABELS.items()]
class LutronKeypadsOptionsFlow(config_entries.OptionsFlow):
	def __init__(A):A._buttons_config={}
	def _get_all_buttons(A):return get_button_layout(A.config_entry.data)
	def _get_configurable(A):return[A for A in A._get_all_buttons()if not A[_t]and not A[_u]]
	def _get_raise_lower_note(C):
		A=[]
		for B in C._get_all_buttons():
			if B[_t]:A.append(f"Button {B[_F]} (Raise)")
			elif B[_u]:A.append(f"Button {B[_F]} (Lower)")
		if not A:return''
		return f"{", ".join(A)} are fixed raise/lower buttons and cannot be reassigned."
	def _get_led_bindings_note(C):
		B=C.hass.data.get(DOMAIN,{}).get('entry_controllers',{}).get(C.config_entry.entry_id)
		if B is _A or not B._led_map:return''
		D=['\n\n**Auto-discovered LED bindings:**']
		for A in sorted(B._led_map):E=B._buttons.get(A,{});F=C.config_entry.data.get(_J,{});G=E.get(_C)or C._buttons_config.get(A,{}).get(_C)or F.get(str(A))or f"Button {A}";D.append(f"- {G} (button #{A}) → `{B._led_map[A]}`")
		return'\n'.join(D)
	def _normalize_target(B,target):
		A=target
		if isinstance(A,list):return[str(A).strip()for A in A if str(A).strip()]
		if isinstance(A,str)and A.strip():return[A.strip()for A in A.split(',')if A.strip()]
		return[]
	def _default_entity(B,cfg,multiple):
		A=cfg.get(CONF_ACTION_TARGET,'')
		if multiple:return A if isinstance(A,list)else B._normalize_target(A)
		if isinstance(A,list):return A[0]if A else''
		return A or''
	async def async_step_init(A,user_input=_A):B=A.config_entry.entry_id;return A.async_show_menu(step_id='init',menu_options=[_E,'license'],description_placeholders={'panel_url':f"/lutron-keypads?entry={B}",_v:A.config_entry.title})
	async def async_step_license(A,user_input=_A):
		C=user_input;B='license_key'
		if C is not _A:D=dict(A.config_entry.options);D[B]=C.get(B,'').strip();return A.async_create_entry(title='',data=D)
		E=await async_get_instance_id(A.hass);F=vol.Schema({vol.Optional(B,default=A.config_entry.options.get(B,'')):str});return A.async_show_form(step_id='license',data_schema=F,description_placeholders={'instance_id':E})
	async def async_step_buttons(A,user_input=_A):
		D=user_input
		if not A._buttons_config:
			I=A.config_entry.options.get(_E,{})
			for(J,K)in I.items():
				try:A._buttons_config[int(J)]=dict(K)
				except(ValueError,TypeError):pass
		E=A._get_configurable();L=A.config_entry.data.get(_B,'Keypad')
		if D is not _A:
			for C in E:
				B=C[_F];M=A._buttons_config.get(B,{});G=D.get(f"button_{B}_action_type",ACTION_NONE);A._buttons_config[B]={**M,_C:D.get(f"button_{B}_label",f"Button {B}"),CONF_ACTION_TYPE:G}
				if G not in ACTION_TYPES_NEEDING_ENTITY:A._buttons_config[B][CONF_ACTION_TARGET]=[];A._buttons_config[B][CONF_LED_ENTITY]='';A._buttons_config[B][_w]=''
			for C in A._get_all_buttons():
				if C[_t]:A._buttons_config[C[_F]]={_C:_o,CONF_ACTION_TYPE:ACTION_RAISE}
				elif C[_u]:A._buttons_config[C[_F]]={_C:_p,CONF_ACTION_TYPE:ACTION_LOWER}
			N=any(A._buttons_config.get(B[_F],{}).get(CONF_ACTION_TYPE)in ACTION_TYPES_NEEDING_ENTITY for B in E)
			if N:return await A.async_step_entities()
			return A.async_create_entry(title='',data={**A.config_entry.options,_E:{str(A):B for(A,B)in A._buttons_config.items()}})
		O=A.config_entry.data.get(_J,{});F={}
		for C in E:B=C[_F];H=A._buttons_config.get(B,{});P=O.get(str(B),f"Button {B}");F[vol.Optional(f"button_{B}_label",default=H.get(_C)or P)]=selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT));F[vol.Required(f"button_{B}_action_type",default=H.get(CONF_ACTION_TYPE,ACTION_NONE))]=selector.SelectSelector(selector.SelectSelectorConfig(options=_ACTION_OPTIONS,mode=selector.SelectSelectorMode.DROPDOWN))
		return A.async_show_form(step_id=_E,data_schema=vol.Schema(F),description_placeholders={_v:L,'raise_lower_note':A._get_raise_lower_note(),_A5:A._get_led_bindings_note()})
	async def async_step_entities(B,user_input=_A):
		K=False;C=user_input;M=B._get_configurable();I=[A for A in M if B._buttons_config.get(A[_F],{}).get(CONF_ACTION_TYPE)in ACTION_TYPES_NEEDING_ENTITY];N=B.config_entry.data.get(_B,'Keypad')
		if not I:return B.async_create_entry(title='',data={**B.config_entry.options,_E:{str(A):B for(A,B)in B._buttons_config.items()}})
		if C is not _A:
			for J in I:
				A=J[_F];D=B._buttons_config[A][CONF_ACTION_TYPE];G=D in MULTI_ENTITY_ACTIONS;H=C.get(f"button_{A}_entity",[]if G else'');B._buttons_config[A][CONF_ACTION_TARGET]=(H if isinstance(H,list)else B._normalize_target(H))if G else H;B._buttons_config[A][CONF_LED_INVERT]=bool(C.get(f"button_{A}_led_invert",K))
				if D==ACTION_ENTITY_TOGGLE:B._buttons_config[A][CONF_LED_MODE]=C.get(f"button_{A}_led_mode",LED_MODE_ROOM);B._buttons_config[A][CONF_TARGET_BRIGHTNESS]=int(C.get(f"button_{A}_target_brightness")or 0);B._buttons_config[A][CONF_TARGET_COLOR_TEMP]=int(C.get(f"button_{A}_target_color_temp")or 0)
				if D==ACTION_STATEFUL_SCENE:B._buttons_config[A][CONF_LED_ENTITY]=C.get(f"button_{A}_led",'');L=C.get(f"button_{A}_scene_group",'');B._buttons_config[A][_w]=L.strip()if isinstance(L,str)else''
			return B.async_create_entry(title='',data={**B.config_entry.options,_E:{str(A):B for(A,B)in B._buttons_config.items()}})
		E={}
		for J in I:
			A=J[_F];F=B._buttons_config.get(A,{});D=F.get(CONF_ACTION_TYPE,ACTION_NONE);O=ACTION_TYPE_DOMAINS.get(D,[]);G=D in MULTI_ENTITY_ACTIONS;E[vol.Optional(f"button_{A}_entity",default=B._default_entity(F,G))]=selector.EntitySelector(selector.EntitySelectorConfig(domain=O,multiple=G))
			if D==ACTION_ENTITY_TOGGLE:E[vol.Optional(f"button_{A}_target_brightness",default=F.get(CONF_TARGET_BRIGHTNESS,0)or 0)]=selector.NumberSelector(selector.NumberSelectorConfig(min=0,max=100,step=1,unit_of_measurement='%',mode='slider'));E[vol.Optional(f"button_{A}_target_color_temp",default=F.get(CONF_TARGET_COLOR_TEMP,0)or 0)]=selector.NumberSelector(selector.NumberSelectorConfig(min=0,max=10000,step=100,unit_of_measurement='K',mode='box'));E[vol.Optional(f"button_{A}_led_mode",default=F.get(CONF_LED_MODE,LED_MODE_ROOM))]=selector.SelectSelector(selector.SelectSelectorConfig(options=[{_s:LED_MODE_ROOM,_C:'Room Mode — LED on when any entity is on'},{_s:LED_MODE_SCENE,_C:'Scene Mode — LED on when all entities match target'}],mode=selector.SelectSelectorMode.DROPDOWN))
			if D==ACTION_STATEFUL_SCENE:E[vol.Optional(f"button_{A}_led",default=F.get(CONF_LED_ENTITY,''))]=selector.EntitySelector(selector.EntitySelectorConfig(domain=['switch'],multiple=K));E[vol.Optional(f"button_{A}_scene_group",default=F.get(_w,''))]=selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
			E[vol.Optional(f"button_{A}_led_invert",default=F.get(CONF_LED_INVERT,K))]=selector.BooleanSelector()
		return B.async_show_form(step_id='entities',data_schema=vol.Schema(E),description_placeholders={_v:N,_A5:B._get_led_bindings_note()})