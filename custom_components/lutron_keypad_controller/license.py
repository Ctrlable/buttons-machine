from __future__ import annotations
_E='license_key'
_D='instance_id'
_C=False
_B=True
_A=None
import asyncio,logging,time
from typing import Any
import aiohttp
_LOGGER=logging.getLogger(__name__)
EXPECTED_PRODUCT='lutron_keypad_controller'
_PUBLIC_KEY='-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1GY0z59YDAAnbMI7cHut\nNgsGwrPMXwcAZ8SmTaHnlwEPK0x1YXElc3rEQEwZd3XoKSB1794cUuqot/PG6Ztu\nis0PZNs7CVw2FZaLl3XzChx8RCfgEARkUkT5bvUB1LXtyVo3jeY8mPbdAvi9xaCj\nzC2/4ViNpO1bT5Aim2JdaYFAV6V6yB4DSPEF/pMf+fikjAnyIqyrQezb1yUncyJx\noKXz8IYxxFKMZrty057jUxzsIZlVkiB7J2zGnOjDnK7rhoY+8Xe97r9/BobT6J8P\n5eQTUePNRFozcCCfXm9RWXrJ22MiTEnH5TFiyoO4ZeLS6FB/4mB9BXL+nVmHThwR\nKwIDAQAB\n-----END PUBLIC KEY-----'
_CHECK_URL='https://portal.ctrlable.com/api/v1/licenses/check/{jti}'
_CHECK_INTERVAL=86400
_OFFLINE_WARN_DAYS=30
_STORAGE_KEY='lutron_keypad_controller_license_cache'
_STORAGE_VERSION=1
class LicenseError(Exception):0
class LicenseResult:
	__slots__='valid','on_expire','grace_days','expires_at','warn_only','jti','binding','instance_id','max_version','product'
	def __init__(A,valid,on_expire,grace_days,expires_at,jti,binding='none',instance_id=_A,max_version=_A,product=_A):B=on_expire;A.valid=valid;A.on_expire=B;A.grace_days=grace_days;A.expires_at=expires_at;A.jti=jti;A.warn_only=B=='warn_only';A.binding=binding;A.instance_id=instance_id;A.max_version=max_version;A.product=product
def _version_tuple(v):
	try:return tuple(int(A)for A in v.strip().split('.'))
	except(ValueError,AttributeError):return()
def _version_allowed(current,max_ver):
	B=_version_tuple(current);A=_version_tuple(max_ver)
	if not A:return _B
	C=len(A);return B[:C]<=A
def _decode_jwt_rs256(token):
	from cryptography.hazmat.primitives.serialization import load_pem_public_key as F;from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15 as G;from cryptography.hazmat.primitives.hashes import SHA256 as H;from cryptography.exceptions import InvalidSignature as I;import base64 as J,json as B;C=token.split('.')
	if len(C)!=3:raise LicenseError('Malformed license key')
	D,E,K=C
	def A(s):s+='='*(-len(s)%4);return J.urlsafe_b64decode(s)
	L=B.loads(A(D))
	if L.get('alg')!='RS256':raise LicenseError('Unexpected signing algorithm')
	M=F(_PUBLIC_KEY.encode());N=f"{D}.{E}".encode();O=A(K)
	try:M.verify(O,N,G(),H())
	except I:raise LicenseError('License signature invalid')
	P=B.loads(A(E));return P
def validate_license_offline(token,current_version=_A):
	J='disable';D=current_version
	try:A=_decode_jwt_rs256(token)
	except LicenseError:raise
	except Exception as G:raise LicenseError(f"License decode error: {G}")from G
	E=A.get('product')
	if EXPECTED_PRODUCT and E!=EXPECTED_PRODUCT:raise LicenseError(f"License is for product {E!r}, not Lutron Keypad Controller ({EXPECTED_PRODUCT!r})")
	K=A.get('jti','');F=A.get('on_expire',J);H=int(A.get('grace_days',0));B=A.get('exp');L=A.get('binding','none');M=A.get(_D)or _A;C=A.get('max_version')or _A;I=time.time()
	if C and D and not _version_allowed(D,C):raise LicenseError(f"License covers up to version {C}.x; this installation is v{D}. Please obtain a new license to use this version.")
	if B is not _A and I>B:
		N=H*86400
		if F==J:raise LicenseError('License has expired')
		if F=='grace_period'and I>B+N:raise LicenseError('License grace period has also expired')
	return LicenseResult(valid=_B,on_expire=F,grace_days=H,expires_at=B,jti=K,binding=L,instance_id=M,max_version=C,product=E)
async def load_license_cache(hass):from homeassistant.helpers.storage import Store;A=Store(hass,_STORAGE_VERSION,_STORAGE_KEY);return await A.async_load()or{}
async def save_license_cache(hass,jti):from homeassistant.helpers.storage import Store;A=Store(hass,_STORAGE_VERSION,_STORAGE_KEY);await A.async_save({'jti':jti,'last_ok':time.time()})
_KEY_STORAGE_KEY='lutron_keypad_controller_license_key'
async def remember_license_key(hass,key):from homeassistant.helpers.storage import Store;A=Store(hass,_STORAGE_VERSION,_KEY_STORAGE_KEY);await A.async_save({_E:key})
async def recall_license_key(hass):from homeassistant.helpers.storage import Store;A=Store(hass,_STORAGE_VERSION,_KEY_STORAGE_KEY);B=await A.async_load()or{};return(B.get(_E)or'').strip()
async def check_revocation_online(jti,instance_id=_A):
	C=instance_id;E=_CHECK_URL.format(jti=jti);D={}
	if C:D[_D]=C
	try:
		async with aiohttp.ClientSession()as F:
			async with F.get(E,params=D,timeout=aiohttp.ClientTimeout(total=10))as A:
				if A.status==404:_LOGGER.warning('Ctrlable Lutron Keypad: license JTI %s not found on portal',jti);return _C
				if A.status==200:
					B=await A.json()
					if B.get('instance_mismatch'):_LOGGER.error('Ctrlable Lutron Keypad: license instance mismatch — this license belongs to a different HA installation.');return _C
					return bool(B.get('valid',not B.get('is_revoked',_C)))
				_LOGGER.warning('Ctrlable Lutron Keypad: license check returned HTTP %s',A.status)
	except Exception as G:_LOGGER.debug('Ctrlable Lutron Keypad: portal unreachable (%s) — operating offline',G)
async def periodic_revocation_check(hass,jti,entry_id,instance_id=_A):
	while _B:
		await asyncio.sleep(_CHECK_INTERVAL);A=await check_revocation_online(jti,instance_id=instance_id)
		if A is _C:_LOGGER.error('Ctrlable Lutron Keypad: license revoked or instance mismatch. Disabling integration.');await hass.config_entries.async_unload(entry_id);return
		if A is _B:await save_license_cache(hass,jti)