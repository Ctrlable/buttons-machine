from __future__ import annotations
_A='caseta'
from homeassistant.config_entries import ConfigEntry
from.base import KeypadBackend
from.caseta import CasetaBackend
_BACKENDS={_A:CasetaBackend}
def get_backend(config_entry):
	A=config_entry;B=_A
	if A is not None:B=A.data.get('backend')or _A
	return _BACKENDS.get(B,CasetaBackend)()
__all__=['KeypadBackend','CasetaBackend','get_backend']