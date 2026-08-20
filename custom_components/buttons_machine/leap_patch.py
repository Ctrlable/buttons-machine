from __future__ import annotations
import inspect,logging
_LOGGER=logging.getLogger(__name__)
_EXPECTED_FILTER='if device_type not in _LEAP_DEVICE_TYPES.get("sensor"):'
_EXPECTED_ARGS='self','control_station_area_name','control_station_name','device_json'
def apply():
	G=None;E=True;B=False
	try:from pylutron_caseta import _LEAP_DEVICE_TYPES as H;from pylutron_caseta.leap import id_from_href as O;from pylutron_caseta.smartbridge import Smartbridge as C
	except Exception as D:_LOGGER.debug('pylutron_caseta not importable, nothing to patch: %s',D);return B
	if getattr(C,'_bm_unknown_keypads_patched',B):return E
	A=getattr(C,'_load_ra3_station_device',G)
	if A is G or not inspect.iscoroutinefunction(A):_LOGGER.warning('Not patching pylutron_caseta: _load_ra3_station_device is missing or not a coroutine. Unrecognised keypads still work, via per-button binding.');return B
	try:I=tuple(inspect.signature(A).parameters);J=inspect.getsource(A)
	except(OSError,TypeError,ValueError)as D:_LOGGER.warning('Not patching pylutron_caseta: cannot inspect _load_ra3_station_device (%s). Falling back to per-button binding.',D);return B
	if I!=_EXPECTED_ARGS or _EXPECTED_FILTER not in J:_LOGGER.warning('Not patching pylutron_caseta: _load_ra3_station_device is not the version this patch was written for (args=%s, expected filter %s). The library has changed — unrecognised keypads still work through the per-button binding, but this patch needs revisiting.',I,'present'if _EXPECTED_FILTER in J else'absent');return B
	F=set(H.get('sensor')or())
	if not F:_LOGGER.warning('Not patching pylutron_caseta: it lists no keypad device types, so there is nothing to present an unknown device as.');return B
	K=set()
	for M in H.values():K.update(M)
	L=sorted(F)[0]
	async def N(self,control_station_area_name,control_station_name,device_json):
		N='type';M='DeviceType';J=control_station_name;I=control_station_area_name;H=self;E='Device';B=device_json;D=B[E][M]
		if D in F:return await A(H,I,J,B)
		if D in K:return
		P={**B,E:{**B[E],M:L}};await A(H,I,J,P);C=H.devices.get(O(B[E]['href']))
		if C is not G and C.get(N)==L:C[N]=D;_LOGGER.info("Loaded '%s' (type %s), which pylutron_caseta does not recognise — %d button group(s). It would otherwise have been dropped with all its buttons and LEDs.",C.get('device_name'),D,len(C.get('button_groups')or[]))
	C._load_ra3_station_device=N;C._bm_unknown_keypads_patched=E;_LOGGER.info('pylutron_caseta patched: control-station devices with an unrecognised DeviceType are now loaded when they have buttons.');return E