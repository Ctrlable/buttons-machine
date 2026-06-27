from __future__ import annotations
_C='license_keys'
_B='license_key'
_A=None
import logging,time
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
from homeassistant.loader import async_get_integration
from.const import DOMAIN
from.license import EXPECTED_PRODUCT,LicenseError,check_revocation_online,load_license_cache,periodic_revocation_check,recall_license_key,remember_license_key,save_license_cache,validate_license_offline
_LOGGER=logging.getLogger(__name__)
def _controller_entry(hass):
	for A in hass.config_entries.async_entries(DOMAIN):
		if A.data.get('_controller'):return A
async def _global_license_key(hass):
	B=hass;C=_controller_entry(B)
	if C is not _A:
		A=(C.options.get(_B)or'').strip()
		if A:return A
	for D in B.config_entries.async_entries(DOMAIN):
		A=(D.options.get(_B)or'').strip()
		if A:return A
	return await recall_license_key(B)
async def _license_key_for_product(hass,product):
	B=product;A=hass;C=_controller_entry(A)
	if C is not _A:
		F=C.options.get(_C)or{};D=(F.get(B)or'').strip()
		if D:return D
	if B==EXPECTED_PRODUCT:
		E=await _global_license_key(A)
		if E:return E
	return await recall_license_key(A,B)
async def enforce_license(hass,entry):
	J=entry;I=False;B=hass;from.backends import get_backend as T;O=T(J);F=O.license_product;U=getattr(O,'accepted_products',_A)or(F,);V=await async_get_integration(B,DOMAIN);W=str(V.version);A=_A;C='';D=F;K=_A
	for L in U:
		M=await _license_key_for_product(B,L)
		if not M:continue
		try:A=validate_license_offline(M,current_version=W,expected_product=L);C,D=M,L;break
		except LicenseError as X:K=X
	if A is _A:
		if K is not _A:_LOGGER.error("Buttons Machine: license validation failed for module '%s' — %s",F,K)
		else:_LOGGER.error("Buttons Machine: no license for module '%s'. Open the panel's License dialog and paste a license for this module (obtain one from portal.ctrlable.com).",F)
		return I
	if A.warn_only:_LOGGER.warning('Buttons Machine: license has expired but warn_only mode is active. Please renew your license.')
	G=await async_get_instance_id(B)
	if A.binding=='instance'and A.instance_id and A.instance_id!=G:_LOGGER.error('Buttons Machine: license is bound to instance %s; this system is %s.',A.instance_id,G);return I
	P=await check_revocation_online(A.jti,instance_id=G)
	if P is I:_LOGGER.error('Buttons Machine: license rejected by portal. Aborting setup.');return I
	Q=await load_license_cache(B);R=Q.get('last_ok')if Q.get('jti')==A.jti else _A
	if P is True:await save_license_cache(B,A.jti)
	elif R is not _A:
		S=(time.time()-R)/86400
		if S>30:_LOGGER.warning('Buttons Machine: portal unreachable for %.0f days. Ensure this device can reach portal.ctrlable.com periodically.',S)
	await remember_license_key(B,C,D);E=_controller_entry(B)
	if E is not _A:
		H={**E.options};N={**(E.options.get(_C)or{})}
		if N.get(D)!=C:N[D]=C;H[_C]=N
		if D==EXPECTED_PRODUCT:H[_B]=C
		if H!=dict(E.options):B.config_entries.async_update_entry(E,options=H)
	B.async_create_background_task(periodic_revocation_check(B,A.jti,J.entry_id,instance_id=G),name=f"buttons_machine_license_check_{J.entry_id}");return True