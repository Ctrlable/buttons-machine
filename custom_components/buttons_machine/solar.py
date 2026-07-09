from __future__ import annotations
_a='area_id'
_Z='transition'
_Y='transition_s'
_X='programs'
_W='color_name'
_V='hs_color'
_U='xy_color'
_T='rgbww_color'
_S='rgbw_color'
_R='take_over_control'
_Q='lights'
_P='color_temp'
_O='turn_on'
_N='light'
_M='bri'
_L='_solar_owner'
_K='_solar'
_J='enabled'
_I='ct'
_H='brightness_pct'
_G='brightness'
_F='entity_id'
_E='rgb_color'
_D=True
_C='color_temp_kelvin'
_B=False
_A=None
import asyncio,logging
from collections import deque
from datetime import time,timedelta
from typing import Any,Callable
from homeassistant.core import Context,HomeAssistant,ServiceCall,callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.sun import get_astral_location
from homeassistant.util.read_only_dict import ReadOnlyDict
import homeassistant.util.dt as dt_util
from.const import DOMAIN
from.solar_engine import SunLightSettings
_LOGGER=logging.getLogger(__name__)
_SOLAR_STORE_KEY='buttons_machine_solar'
_BRI_THRESH=25
_CT_THRESH=100
_MANUAL_ATTRS=_G,_H,_P,_C,_E,_S,_T,_U,_V,_W,'effect'
def setup_service_call_interceptor(hass,domain,service,intercept_func):
	D=hass;B=service;A=domain;E=D.services._services
	if A not in E or B not in E[A]:raise RuntimeError(f"Intercept failed: {A}.{B} not registered")
	C=E[A][B]
	async def F(call):
		A=call
		try:
			D=dict(A.data);E=intercept_func(A,D)
			if E is not _A:await E
			A.data=ReadOnlyDict(D)
		except Exception:_LOGGER.exception('Solar Sync interceptor error')
		B=C.job.target
		if asyncio.iscoroutinefunction(B):await B(A)
		else:B(A)
	D.services.async_register(A,B,F,C.schema)
	def G():D.services.async_register(A,B,C.job.target,C.schema)
	return G
async def _load_solar(hass):B=hass;from homeassistant.helpers.storage import Store;C=await Store(B,1,_SOLAR_STORE_KEY).async_load()or{};A=C.get(_X)if isinstance(C,dict)else{};A=A if isinstance(A,dict)else{};B.data.setdefault(DOMAIN,{})[_K]=A;_rebuild_owner_index(B);return A
async def _save_solar(hass,programs):B=programs;A=hass;from homeassistant.helpers.storage import Store;await Store(A,1,_SOLAR_STORE_KEY).async_save({_X:B});A.data.setdefault(DOMAIN,{})[_K]=B;_rebuild_owner_index(A)
def _rebuild_owner_index(hass):
	A={}
	for(B,C)in((hass.data.get(DOMAIN,{})or{}).get(_K)or{}).items():
		for D in C.get(_Q)or[]:A.setdefault(D,B)
	hass.data.setdefault(DOMAIN,{})[_L]=A
def _solar_owner(hass,eid):return((hass.data.get(DOMAIN,{})or{}).get(_L)or{}).get(eid)
def _toc(p):
	if _R in p:return bool(p[_R])
	return p.get('on_manual','release')!='respect'
def _parse_time(v):
	if not v:return
	try:A=str(v).split(':');return time(int(A[0]),int(A[1])if len(A)>1 else 0)
	except(ValueError,IndexError):return
def _rgb_tuple(v,default=(255,56,0)):
	try:A,B,C=(int(A)for A in v[:3]);return A,B,C
	except(TypeError,ValueError,IndexError):return default
def _settings_for(hass,p):A,B=get_astral_location(hass);return SunLightSettings(name=p.get('name','solar'),astral_location=A,adapt_until_sleep=bool(p.get('adapt_until_sleep',_B)),max_brightness=int(p.get('max_brightness',100)),max_color_temp=int(p.get('max_color_temp',5500)),min_brightness=int(p.get('min_brightness',1)),min_color_temp=int(p.get('min_color_temp',2000)),sleep_brightness=int(p.get('sleep_brightness',1)),sleep_rgb_or_color_temp=p.get('sleep_rgb_or_color_temp',_P),sleep_color_temp=int(p.get('sleep_color_temp',1000)),sleep_rgb_color=_rgb_tuple(p.get('sleep_rgb_color')),sunrise_time=_parse_time(p.get('sunrise_time')),min_sunrise_time=_parse_time(p.get('min_sunrise_time')),max_sunrise_time=_parse_time(p.get('max_sunrise_time')),sunset_time=_parse_time(p.get('sunset_time')),min_sunset_time=_parse_time(p.get('min_sunset_time')),max_sunset_time=_parse_time(p.get('max_sunset_time')),brightness_mode_time_dark=timedelta(seconds=int(p.get('brightness_mode_time_dark',900))),brightness_mode_time_light=timedelta(seconds=int(p.get('brightness_mode_time_light',3600))),brightness_mode=p.get('brightness_mode','default'),sunrise_offset=timedelta(minutes=int(p.get('sunrise_offset_min',0))),sunset_offset=timedelta(minutes=int(p.get('sunset_offset_min',0))),timezone=dt_util.get_time_zone(hass.config.time_zone)or dt_util.UTC)
def solar_preview(hass,program,step_min=15):
	C=program;F=_settings_for(hass,C);G=bool(C.get('_preview_sleep'));H=dt_util.now();I=H.replace(hour=0,minute=0,second=0,microsecond=0);D=[]
	for E in range(0,1440,max(5,step_min)):
		J=I+timedelta(minutes=E)
		try:A=F.brightness_and_color(J,G)
		except Exception:continue
		B=A.get(_E)or(0,0,0);D.append({'m':E,_M:round(float(A[_H]),1),_I:int(A[_C]),'rgb':[int(B[0]),int(B[1]),int(B[2])],'sun':round(float(A.get('sun_position',0)),3)})
	return D
class SolarManager:
	def __init__(A,hass):A.hass=hass;A._unsubs={};A._released=set();A._last={};A._state_unsub=_A;A._our_ctx=deque(maxlen=256);A._autoreset={};A._intercept_removers=[];A._installed=_B
	def _make_ctx(B):A=Context();B._our_ctx.append(A.id);return A
	def _is_ours(A,ctx):return bool(ctx)and ctx.id in A._our_ctx
	@property
	def _programs(self):return(self.hass.data.get(DOMAIN,{})or{}).get(_K)or{}
	def rearm_all(A):
		A._released.clear();A.install_interceptor()
		for E in A._unsubs.values():
			try:E()
			except Exception:pass
		A._unsubs={}
		for(C,B)in A._programs.items():
			if B.get(_J,_D)and(B.get(_Q)or[]):F=max(30,int(B.get('interval_s',90)));A._unsubs[C]=async_track_time_interval(A.hass,A._tick(C),timedelta(seconds=F))
		if A._state_unsub:A._state_unsub();A._state_unsub=_A
		D=list(((A.hass.data.get(DOMAIN,{})or{}).get(_L)or{}).keys())
		if D:from homeassistant.helpers.event import async_track_state_change_event as G;A._state_unsub=G(A.hass,D,A._on_light_state)
		A.hass.async_create_task(A._apply_all())
	@callback
	def _on_light_state(self,event):
		D=event;A=self;B=D.data.get(_F);E=D.data.get('new_state');G=D.data.get('old_state')
		if E is _A:return
		if E.state=='off':
			A._released.discard(B);H=A._autoreset.pop(B,_A)
			if H:H()
			return
		if A._is_ours(D.context):return
		I=_solar_owner(A.hass,B);C=A._programs.get(I)if I else _A
		if not C or not C.get(_J,_D):return
		if C.get(_R,_D)and C.get('detect_non_ha_changes',_B)and G is not _A and G.state=='on':
			F=A._last.get(B)
			if F is not _A:
				J,K=E.attributes.get(_G),E.attributes.get(_C)
				if J is not _A and abs(J-F[_M])>_BRI_THRESH or K is not _A and F[_I]and abs(K-F[_I])>_CT_THRESH:A._release(B,C)
	def _tick(A,pid):
		async def B(now=_A):await A._apply_program(pid)
		return B
	async def _apply_all(A):
		for B in list(A._programs):await A._apply_program(B)
	async def _apply_program(B,pid):
		A=B._programs.get(pid)
		if not A or not A.get(_J,_D)or A.get('only_once',_B):return
		G=_settings_for(B.hass,A);D=int(A.get(_Y,45));E=G.get_settings(is_sleep=_B,transition=D)
		for C in A.get(_Q)or[]:
			if C in B._released:continue
			F=B.hass.states.get(C)
			if F is _A or F.state!='on':continue
			await B._apply_one(C,E[_H],E[_C],D)
	async def _apply_one(A,eid,bri_pct,ct,trans):B=max(1,min(255,round(255*bri_pct/100)));A._last[eid]={_M:B,_I:int(ct)};await A.hass.services.async_call(_N,_O,{_F:eid,_G:B,_C:int(ct),_Z:trans},blocking=_B,context=A._make_ctx())
	def rearm_light(A,eid):
		B=eid;A._released.discard(B);C=A._autoreset.pop(B,_A)
		if C:C()
		A.hass.async_create_task(A._apply_owner(B))
	def _release(A,eid,p):
		B=eid;A._released.add(B);C=A._autoreset.pop(B,_A)
		if C:C()
		D=int(p.get('autoreset_control_seconds',0)or 0)
		if D>0:from homeassistant.helpers.event import async_call_later as E;A._autoreset[B]=E(A.hass,D,lambda _now:A.rearm_light(B))
	def install_interceptor(A):
		if A._installed:return
		if not(A.hass.data.get(DOMAIN,{})or{}).get(_L):return
		try:A._intercept_removers.append(setup_service_call_interceptor(A.hass,_N,_O,A._intercept_turn_on));A._installed=_D
		except Exception as B:_LOGGER.warning('Solar Sync: could not install turn_on interceptor: %s',B)
	def uninstall_interceptor(A):
		for B in A._intercept_removers:
			try:B()
			except Exception:pass
		A._intercept_removers=[];A._installed=_B
	def _extract_eids(C,data):
		A=data.get(_F)
		if not A:return[]
		B=[A]if isinstance(A,str)else list(A);return[A for A in B if isinstance(A,str)and A.startswith('light.')]
	def _intercept_turn_on(A,call,data):
		E=data
		if A._is_ours(call.context):return
		F=A._extract_eids(E)
		if not F:return
		J=not any(A in E for A in _MANUAL_ATTRS);B={}
		for G in F:
			C=_solar_owner(A.hass,G)
			if C and A._governs(G,C,J):B.setdefault(C,[]).append(G)
		if not B:return
		K={B for A in B.values()for B in A};I=[A for A in F if A not in K];H=list(B);A._inject(E,H[0],B[H[0]])
		for C in H[1:]:D={};A._inject(D,C,B[C]);A.hass.async_create_task(A.hass.services.async_call(_N,_O,D,blocking=_B,context=A._make_ctx()))
		if I:D={A:B for(A,B)in call.data.items()if A not in(_F,_a)};D[_F]=I;A.hass.async_create_task(A.hass.services.async_call(_N,_O,D,blocking=_B,context=A._make_ctx()))
	def _governs(B,eid,pid,is_bare):
		A=B._programs.get(pid)
		if not A or not A.get(_J,_D)or eid in B._released:return _B
		if not A.get('intercept',_D):return _B
		if not is_bare:
			if _toc(A):B._release(eid,A);return _B
			if A.get('adapt_only_on_bare_turn_on',_B):return _B
		return _D
	def _inject(C,data,pid,eids):
		A=data;D=C._programs.get(pid)or{};F=_settings_for(C.hass,D);E=int(D.get('initial_transition',1));B=F.get_settings(is_sleep=_B,transition=E)
		for G in(_a,_P,_C,_E,_S,_T,_U,_V,_W):A.pop(G,_A)
		A[_F]=eids;A[_G]=max(1,min(255,round(255*B[_H]/100)))
		if(D.get('prefer_rgb_color',_B)or B.get('force_rgb_color'))and B.get(_E):A[_E]=list(B[_E])
		else:A[_C]=int(B[_C])
		A[_Z]=E
		for H in eids:C._last[H]={_M:A[_G],_I:int(B[_C])}
	async def _apply_owner(A,eid):
		C=_solar_owner(A.hass,eid);B=A._programs.get(C)if C else _A
		if not B or not B.get(_J,_D):return
		F=_settings_for(A.hass,B);D=int(B.get(_Y,45));E=F.get_settings(is_sleep=_B,transition=D);await A._apply_one(eid,E[_H],E[_C],D)
def _get_solar_manager(hass):
	C='_solar_manager';B=hass;A=B.data.setdefault(DOMAIN,{}).get(C)
	if A is _A:A=SolarManager(B);B.data[DOMAIN][C]=A
	return A
def solar_rearm(hass,eid):
	if _solar_owner(hass,eid):_get_solar_manager(hass).rearm_light(eid)