from __future__ import annotations
_A=None
def all_devices(dev_reg):
	A=dev_reg.devices;B=next(iter(A),_A)
	if B is _A:return[]
	if isinstance(B,str):return list(A.values())
	return list(A)
def devices_by_identifier(dev_reg,identifiers):
	B=identifiers;A=dev_reg;C=getattr(A,'async_get_devices',_A)
	if C is not _A:return C(identifiers=B)
	return[A for A in all_devices(A)if set(A.identifiers)&B]
def first_device_by_identifier(dev_reg,identifiers):A=devices_by_identifier(dev_reg,identifiers);return A[0]if A else _A
def reparent_device(dev_reg,device,entry_id):
	C=entry_id;B=dev_reg;A=device;import inspect as F;D=getattr(A,'config_entry_id',_A)
	if D is not _A:
		if D==C:return
		G=F.signature(B.async_update_device).parameters
		if'new_config_entry_id'in G:B.async_update_device(A.id,new_config_entry_id=C);return
	for E in list(A.config_entries):
		if E!=C:B.async_update_device(A.id,remove_config_entry_id=E)